import ast
from dataclasses import replace
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'proposed'))
import private_workload as candidate
import effective_storage as es
from topology_model import View, bwrap_argv

BASE = Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
MANIFEST = json.loads((BASE/'storage-direct-v8/storage-live-19/live19-f-success-01-manifest.json').read_text())
ORIGIN = dict(uid=1000, gid=1000, cgroup='/TEST_ONLY.service', namespaces={n:'TEST_ONLY_'+n for n in ('mnt','user','pid','net')})
HOST = (HERE/'host-mountinfo.txt').read_text()


def old_command():
    spec = importlib.util.spec_from_file_location('frozen_private', HERE/'frozen-v8/private_workload.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = candidate.HERE
    return module.command(MANIFEST, ORIGIN)


class RuntimeView(unittest.TestCase):
    def setUp(self):
        self.command = candidate.command(MANIFEST, ORIGIN)
        self.argv = bwrap_argv(self.command)
        self.view = View(HOST).construct(self.argv)

    def test_captured_audit21_rows_are_in_fixture(self):
        selected = json.loads((HERE.parent/'storage-remaining-gates-audit-21/host-topology-readonly.json').read_text())
        self.assertTrue(all(row in HOST.splitlines() for row in selected['selected_mount_rows']))
        self.assertIn('/run/user/60578/doc', HOST)
        self.assertIn('/run/docker/netns/', HOST)
        self.assertIn('/var/lib/docker/rootfs/', HOST)

    def test_final_model_strict_checker_and_all_mounts_inspected(self):
        seen = set()
        def observe(path):
            seen.add(path)
            return self.view.observe(path)
        result = es.check(self.view.raw(), MANIFEST['attempt_root'], observe)
        self.assertEqual(seen, {m.path for m in self.view.mounts.values()})
        self.assertEqual([r['path'] for r in result['rows'] if r['result']=='charged-attempt'],
                         [MANIFEST['attempt_root']])
        self.assertFalse(any(r['result']=='hidden' for r in result['rows']))
        self.assertTrue(all(not m.optional for m in self.view.mounts.values()))

    def test_inaccessible_host_trees_absent_not_merely_covered(self):
        for m in self.view.mounts.values():
            self.assertFalse(any(es.within(m.path, p) for p in ('/run','/var','/sys')))
        # Merely bind-masking the old root retains hidden mountinfo rows.
        old = View(HOST).construct(bwrap_argv(old_command()))
        self.assertTrue(any(m.path=='/run/user/60578/doc' for m in old.mounts.values()))

    def test_old_root_model_still_rejects_inaccessible_mount(self):
        old = View(HOST).construct(bwrap_argv(old_command()))
        def observe(path):
            if path == '/run/user/60578/doc' or path.startswith('/run/docker/netns/'):
                raise PermissionError(errno.EACCES, 'captured ancestor search denied')
            return old.observe(path)
        with self.assertRaisesRegex(es.Rejected, 'unresolved mount path'):
            es.check(old.raw(), MANIFEST['attempt_root'], observe)

    def test_minimal_audit21_portal_counterexample(self):
        v = View('1 99 8:1 / / ro - ext4 ROOT rw\n')
        v.mounts[100000] = replace(v.mounts[100000], options=('ro',))
        v.add('/attempt', (8,1), 'ext4', False)
        parent = v.add('/run/user/60578', (0,61), 'tmpfs', True)
        v.add('/run/user/60578/doc', (0,66), 'fuse.portal', False, parent=parent)
        def observe(path):
            if path.endswith('/doc'):
                raise PermissionError(errno.EACCES, 'audit21 fixture')
            return v.observe(path)
        with self.assertRaisesRegex(es.Rejected, 'unresolved mount path'):
            es.check(v.raw(), '/attempt', observe)

    def test_new_inaccessible_import_is_not_whitelisted(self):
        path = '/home/TEST_ONLY-inaccessible/mount'
        self.view.add(path, (0,1234), 'tmpfs', True)
        def observe(p):
            if p == path:
                raise PermissionError(errno.EACCES, 'new inaccessible import')
            return self.view.observe(p)
        with self.assertRaisesRegex(es.Rejected, 'unresolved mount path'):
            es.check(self.view.raw(), MANIFEST['attempt_root'], observe)

    def test_omitted_root_remount_rejects_writable_scaffold(self):
        argv = list(self.argv)
        i = next(i for i in range(len(argv)-1) if argv[i:i+2]==['--remount-ro','/'])
        del argv[i:i+2]
        v = View(HOST).construct(argv)
        with self.assertRaisesRegex(es.Rejected, 'writable filesystem outside'):
            es.check(v.raw(), MANIFEST['attempt_root'], v.observe)

    def test_runtime_dirs_are_readonly_same_scaffold_not_extra_tmpfs(self):
        for path in ('/run','/var','/tmp'):
            self.assertIn(path, self.view.directories)
            self.assertEqual(self.view.observe(path).mount_id, self.view.observe('/').mount_id)
            self.assertTrue(self.view.observe(path).readonly)

    def test_no_new_writable_mount_is_accepted(self):
        for path in ('/run','/var','/tmp','/home/new','/mnt/new',MANIFEST['attempt_root']+'/nested'):
            with self.subTest(path=path):
                v = View(HOST).construct(self.argv)
                v.add(path, (0,1999), 'tmpfs', False)
                with self.assertRaisesRegex(es.Rejected, 'writable filesystem outside'):
                    es.check(v.raw(), MANIFEST['attempt_root'], v.observe)

    def test_root_remount_order_and_exact_single_rw_bind(self):
        end = self.argv.index('--')
        args = self.argv[:end]
        self.assertEqual(args.count('--bind'), 1)
        i = args.index('--bind')
        self.assertEqual(args[i+1:i+3], [MANIFEST['attempt_root']]*2)
        self.assertEqual(args[i+3:i+5], ['--remount-ro','/'])
        self.assertFalse(any(x in args[i+5:] for x in ('--ro-bind','--bind','--dir','--dev','--proc','--tmpfs')))
        self.assertNotIn('--tmpfs', args)
        self.assertNotIn('/sys', args)
        self.assertNotIn(['--ro-bind','/','/'], [args[j:j+3] for j in range(len(args))])

    def test_recursive_bind_sources_cannot_be_recovered_by_late_mask(self):
        # Appending a fresh /run dir does not alter mounts already cloned from /.
        old = bwrap_argv(old_command())
        i = old.index('--')
        v = View(HOST).construct(old[:i]+['--dir','/run']+old[i:])
        self.assertTrue(any(m.path=='/run/user/60578/doc' for m in v.mounts.values()))

    def test_custody_namespace_and_payload_transport_unchanged(self):
        old = old_command()
        self.assertEqual(old[:old.index('/usr/bin/bwrap')], self.command[:self.command.index('/usr/bin/bwrap')])
        old_bwrap = bwrap_argv(old)
        self.assertEqual(old_bwrap[old_bwrap.index('--'):], self.argv[self.argv.index('--'):])
        for flag in ('--unshare-user','--unshare-pid','--unshare-net','--die-with-parent'):
            self.assertEqual(self.argv.count(flag), 1)
        self.assertNotIn('--unshare-cgroup', self.command)
        self.assertIn('--propagation', self.command)
        self.assertEqual(self.command[self.command.index('--propagation')+1], 'private')

    def test_all_existing_guard_functions_byte_semantics_unchanged(self):
        def functions(path):
            return {n.name:ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text()).body
                    if isinstance(n, ast.FunctionDef) and n.name!='command'}
        old = functions(HERE/'frozen-v8/private_workload.py')
        new = functions(HERE/'proposed/private_workload.py')
        self.assertEqual(old, {k:v for k,v in new.items() if k!='runtime_view'})
        for name in ('effective_storage.py','storage_paths.py'):
            self.assertEqual((HERE/'frozen-v8'/name).read_bytes(), (HERE/'proposed'/name).read_bytes())

    def test_required_inputs_outside_view_fail_closed(self):
        for path in ('/run','/var','/sys','/tmp','/usr-does-not-exist'):
            m = dict(MANIFEST, inputs=[dict(path=path, sha256='TEST_ONLY')])
            with self.subTest(path=path), self.assertRaises((RuntimeError, FileNotFoundError)):
                candidate.command(m, ORIGIN)

    def test_symlink_escape_and_changed_compatibility_link_rejected(self):
        original = Path.resolve
        with patch.object(Path, 'resolve', lambda p, **kw: Path('/run/escape') if str(p)=='/usr/bin/python3.14' else original(p, **kw)):
            with self.assertRaisesRegex(RuntimeError, 'outside runtime read view'):
                candidate.command(MANIFEST, ORIGIN)
        with patch.object(os, 'readlink', return_value='run/escape'):
            with self.assertRaisesRegex(RuntimeError, 'compatibility symlink changed'):
                candidate.command(MANIFEST, ORIGIN)

    def test_exact_actual_compiler_inputs_and_pinned_closure_fit_view(self):
        closure = json.loads((HERE/'read-closure.json').read_text())
        self.assertEqual(closure['compiler_plan_input_rows'], 727)
        self.assertEqual(len(closure['compiler_stages']), 8)
        self.assertTrue(closure['categories']['font-language-assets'])
        self.assertTrue(any('libffi' in p for p in closure['categories']['python-mapped-runtime']))
        self.assertTrue(any('ld-linux' in p for p in closure['categories']['elf-edges']))
        self.assertEqual(closure['missing'], [])
        self.assertEqual(closure['uninspectable'], [])
        # Use canonical controller pins just as adopted adapter10 does, retaining
        # every digest; the nominal compiler aliases remain in the sealed plan.
        plan = json.loads(Path(closure['source_documents']['compiler-plan']['path']).read_text())
        m = dict(MANIFEST, inputs=[dict(p, path=str(Path(p['path']).resolve(strict=True))) for p in plan['inputs']])
        self.assertEqual(candidate.command(m, ORIGIN), self.command)

    def test_host_observations_cover_every_imported_boundary(self):
        record = json.loads((HERE/'retained-mount-access.json').read_text())
        self.assertTrue(record['host_only'])
        self.assertTrue(record['topology_stable'])
        imported = {m.path for m in self.view.mounts.values() if any(es.within(m.path,s) for s in (*candidate.RUNTIME_READ_TREES,'/dev/shm'))}
        imported.remove(MANIFEST['attempt_root'])
        self.assertEqual(imported, set(record['mountpoints']))
        self.assertTrue(all(r['accessible'] for r in record['mountpoints'].values()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
