"""Bounded host reads only. No namespace, compiler, subprocess, or authority writes."""
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(HERE/'proposed'))
import private_workload as proposal
import effective_storage as es


def pin(p):
    return dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def read(p):
    return json.loads(p.read_text())


def refs(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and value['path'].startswith('/'):
            yield value['path']
        for item in value.values():
            yield from refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from refs(item)


def retained(value):
    p = os.path.normpath(value)
    for link, target in proposal.RUNTIME_LINKS:
        if es.within(p, link):
            p = '/'+target+p[len(link):]
            break
    return any(es.within(p, source) for source in (*proposal.RUNTIME_READ_TREES, '/dev/shm'))


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    documents = {
        'live19': BASE/'storage-live-19/authenticated-input-pins.json',
        'compiler-plan': BASE/'compiler-native-binding-08/root-check01/compiler-preview/plan.json',
        'compiler-authentication': BASE/'compiler-build-preparation-03/authentication.json',
        'current-controls': BASE/'compiler-native-binding-08/root-check01/current-closures.json',
        'adapter-authority': BASE/'compiler-controller-preparation-09/source-contract.json',
    }
    data = {k: read(v) for k, v in documents.items()}
    categories = {k: set(refs(v)) for k, v in data.items()}
    future_outputs = {p for s in data['compiler-plan']['stages'] for p in s['outputs']}
    assert not future_outputs.intersection(p['path'] for p in data['compiler-plan']['inputs'])
    categories['compiler-plan'] -= future_outputs
    # Include every transitive ELF edge, nominal loader alias, font/language
    # assets, generated VFS assets, and adapter's mutable protected read paths.
    categories['elf-edges'] = {e[k] for e in data['compiler-authentication']['elf_edges']
                               for k in ('source', 'target')}
    categories['font-language-assets'] = {p['path'] for p in data['compiler-authentication']['inputs']
                                          if 'A347 font/language asset' in p.get('roles', [])}
    categories['protected-live-reads'] = {data['adapter-authority'][k] for k in ('lock_path', 'state_path')}
    config = read(HERE/'frozen-v8/runtime-config.json')
    categories['protected-live-reads'].add(config['owner_state'])
    categories['python-mapped-runtime'] = {l.split(None, 5)[5].strip() for l in Path('/proc/self/maps').read_text().splitlines()
                                           if len(l.split(None, 5)) == 6 and l.split(None, 5)[5].startswith('/')}
    categories['python-mapped-runtime'].add(ctypes.__file__)
    # Git worktree's common directory is outside this checkout but retained by /home.
    gitfile = BASE.parent.parent/'.git'
    gitdir = (gitfile.parent/gitfile.read_text().strip().split(': ', 1)[1]).resolve()
    commondir = (gitdir/(gitdir/'commondir').read_text().strip()).resolve()
    categories['git-metadata'] = {str(gitfile), str(gitdir/'HEAD'), str(commondir/'config')}
    report = {}
    all_paths = sorted(set.union(*categories.values()))
    for value in all_paths:
        try:
            p = Path(value)
            resolved = p.resolve(strict=True)
            assert retained(value) and retained(str(resolved)), 'outside runtime view'
            with p.open('rb') as stream:
                stream.read(1)  # Access proof only; no new digest authorizes changed bytes.
                s = os.fstat(stream.fileno())
            report[value] = dict(resolved=str(resolved), dev=s.st_dev, ino=s.st_ino,
                                 mode=s.st_mode, uid=s.st_uid, gid=s.st_gid, accessible=True)
        except Exception as error:
            report[value] = dict(accessible=False, error=type(error).__name__+': '+str(error))
    # Complete host topology captured, as distinct from audit21's selected rows.
    raw = Path('/proc/self/mountinfo').read_text()
    (HERE/'host-mountinfo.txt').write_text(raw)
    mounts = es.parse_mountinfo(raw)
    sources = (*proposal.RUNTIME_READ_TREES, '/dev/shm')
    visible = sorted(set(sources) | {m.path for m in mounts.values()
                                   if any(es.within(m.path, s) for s in sources)})
    observed = {}
    for p in visible:
        try:
            observed[p] = dict(es.asdict(es.observe(p)), accessible=True)
        except Exception as error:
            observed[p] = dict(accessible=False, error=type(error).__name__+': '+str(error))
    topology = dict(host_only=True, runtime_qualification=False, mountinfo=pin(HERE/'host-mountinfo.txt'),
                    read_sources=sources, mountpoints=observed,
                    topology_stable=Path('/proc/self/mountinfo').read_text() == raw)
    (HERE/'retained-mount-access.json').write_text(json.dumps(topology, indent=2)+'\n')
    output = dict(host_only=True, runtime_qualification=False, source_documents={k:pin(v) for k,v in documents.items()},
                  categories={k:sorted(v) for k,v in categories.items()}, paths=report,
                  compiler_plan_input_rows=len(data['compiler-plan']['inputs']),
                  compiler_stages=[s['name'] for s in data['compiler-plan']['stages']],
                  future_outputs=sorted(future_outputs),
                  future_output_contract='Unbuilt outputs, not read inputs. Adapter relocates whole plan.out into exact charged attempt/compiler; no execution here.',
                  elf_edges=len(data['compiler-authentication']['elf_edges']),
                  compatibility_links={p:os.readlink(p) for p,_ in proposal.RUNTIME_LINKS},
                  missing=[p for p,r in report.items() if not r['accessible']],
                  uninspectable=[p for p,r in observed.items() if not r['accessible']],
                  note='Reachability and host descriptor observations; historical plan hashes were not reauthorized or rehashed.')
    (HERE/'read-closure.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(dict(paths=len(report), categories={k:len(v) for k,v in categories.items()},
                          retained_mountpoints=len(observed), missing=output['missing'],
                          uninspectable=output['uninspectable'], topology_stable=topology['topology_stable'])))
    assert not output['missing'] and not output['uninspectable'] and topology['topology_stable']


if __name__ == '__main__':
    main()
