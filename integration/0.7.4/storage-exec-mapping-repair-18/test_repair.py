"""Bounded source and mock checks only. No real drop, exec, namespace or load."""
import ast,contextlib,copy,ctypes,errno,hashlib,importlib.util,io,json,os,resource,sys,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(20,20));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
H=Path(__file__).resolve().parent
sys.path[:0]=[str(H/'proposed'),str(H/'baseline')]
import private_workload as pw
import storage_controller as sc
import storage_paths as sp
spec=importlib.util.spec_from_file_location('proposal_setup',H/'system-setup/system_setup.py');setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
ORIGIN=dict(uid=1000,gid=1000,cgroup='/mock.service')
LABELS={'origin':'unconfined','pre':'vkf-storage-pre-v2 (enforce)','post':'bwrap//&unpriv_bwrap (enforce)'}
def status(stage):return dict(Uid=['1000']*4,Gid=['1000']*4,CapInh=['0000000000000000'],CapPrm=['0000000000000000'],CapEff=['0000000000000000'],CapAmb=['0000000000000000'],CapBnd=['0000000000000000' if stage=='post' else '000001ffffffffff'],NoNewPrivs=['1' if stage=='post' else '0'])
def raw(fields):return ''.join(k+':\t'+'\t'.join(v)+'\n' for k,v in fields.items())
def snapshot():
 s=status('origin');s.update(Groups=['1000'],Threads=['1'],CapInh=['0000000800000000']);return dict(status=s,label='unconfined',errors=[])
def clean():
 s=snapshot();s['status']['CapInh']=['0000000000000000'];return s
# Reuse accepted tests by AST extraction. Their syscalls/exec interfaces are mocked.
prior=H.parent/'storage-capability-repair-15/test_repair.py'
tree=ast.parse(prior.read_text())
for n in tree.body:
 if isinstance(n,ast.ClassDef) and n.name in ('CapabilityInitialization','SyscallBinding'):
  exec(compile(ast.Module(body=[n],type_ignores=[]),str(prior),'exec'),globals())
prior=H.parent/'storage-policy-setup-11/test_policy.py'
n=next(n for n in ast.parse(prior.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='PolicyGate')
s=ast.get_source_segment(prior.read_text(),n).replace("source=(H/'candidate/storage-direct-v6/private_workload.py').read_text()","source=(H/'proposed/private_workload.py').read_text()")
exec(compile(s,str(prior),'exec'),globals())
class Preservation(unittest.TestCase):
 def test_only_exact_private_constants_changed(self):
  old=(H/'baseline/private_workload.py').read_text()
  new=(H/'proposed/private_workload.py').read_text()
  expected=old.replace('vkf-storage-private-v1','vkf-storage-private-v2').replace('vkf-storage-pre-v1','vkf-storage-pre-v2').replace('a6a82dd0c9f50c296e88933645e8a8487b947dd4de6ff6e66acee2541e1a17a4',setup.POLICY_SHA)
  self.assertEqual(new,expected)
  old_ast=ast.parse(old);new_ast=ast.parse(new)
  for n in old_ast.body:
   if isinstance(n,ast.FunctionDef):
    nn=next(x for x in new_ast.body if isinstance(x,ast.FunctionDef) and x.name==n.name)
    if n.name=='policy_gate':
     for x in ast.walk(n):
      if isinstance(x,ast.Constant) and x.value=='vkf-storage-pre-v1 (enforce)':x.value='vkf-storage-pre-v2 (enforce)'
    self.assertEqual(ast.dump(n),ast.dump(nn),n.name)
 def test_exact_policy_delta(self):
  old=(H/'baseline/vkf-storage-private-v1').read_text().replace('vkf-storage-private-v1','vkf-storage-private-v2').replace('vkf-storage-pre-v1','vkf-storage-pre-v2')
  new=(H/'system-setup/vkf-storage-private-v2').read_text()
  self.assertEqual(new.replace('  /usr/bin/python3.14 m,\n','').replace('  /usr/bin/bwrap m,\n',''),old)
  self.assertEqual(new.count('  /usr/bin/python3.14 m,'),2);self.assertEqual(new.count('  /usr/bin/bwrap m,'),1)
  self.assertNotIn('/usr/bin/**',new)
 def test_existing_post_mapping_and_denial(self):
  text=Path('/etc/apparmor.d/bwrap-userns-restrict').read_text()
  self.assertEqual(text.count('allow file rwlkm /{**,},'),2)
  self.assertIn('audit deny capability,',text)
  self.assertIn('allow pix /** -> &bwrap//&unpriv_bwrap,',text)
  self.assertIn('allow pix /** -> &unpriv_bwrap,',text)
 def test_old_pre_label_rejected(self):
  with patch.object(pw,'_security_snapshot',return_value=dict(status=status('pre'),label='vkf-storage-pre-v1 (enforce)',errors=[])),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(sp.Rejected):pw.policy_gate('pre',ORIGIN)
 def test_entire_command_shape_preserved(self):
  old=(H/'baseline/private_workload.py').read_text()
  node=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='command')
  env=dict(json=json,HERE=pw.HERE,PYTHON=pw.PYTHON,BWRAP=pw.BWRAP,UNSHARE='/usr/local/libexec/vkf-storage-private-v1/unshare')
  exec(compile(ast.Module(body=[node],type_ignores=[]),'old-command','exec'),env)
  m=dict(attempt_root='/charged',cwd='/charged/work',argv=['/usr/bin/python3.14','/payload.py'])
  expected=env['command'](m,ORIGIN);expected[0]=pw.UNSHARE
  self.assertEqual(pw.command(m,ORIGIN),expected)
 def test_inputs_immutable(self):
  for p in json.loads((H/'input-pins.json').read_text()):self.assertEqual(hashlib.sha256(Path(p['path']).read_bytes()).hexdigest(),p['sha256'],p['path'])
 def test_original_v7_bundle_exact_order(self):
  c=json.loads((H/'successor-contract.json').read_text());b=json.loads((H/'preserved-v7-bundle.json').read_text())
  self.assertEqual(c['preserved_v7_bundle'],b)
  self.assertEqual([Path(p['path']).name for p in b['helpers']],list(sc.HELPERS))
  self.assertTrue(all('/storage-direct-v7/' in p['path'] for p in [b['controller'],b['config'],*b['helpers']]))
 def test_missing_dependency_stops_gate(self):
  with patch.object(pw,'verify_dependencies',side_effect=sp.Rejected('missing')),patch.object(pw.os,'execv') as ex,self.assertRaises(sp.Rejected):pw.gate('pre',ORIGIN,'/attempt',[pw.BWRAP])
  ex.assert_not_called()
class SetupFailClosed(unittest.TestCase):
 def test_no_rg_dependency_and_shell_checks_unconditional(self):
  for name in ('install','rollback'):
   src=(H/'system-setup'/(name+'-reviewed.sh')).read_text()
   self.assertNotIn('/usr/bin/rg',src);self.assertIn('[[ -x /usr/bin/python3.14 ]] ||',src);self.assertIn('[[ -x /usr/sbin/apparmor_parser ]] ||',src)
   self.assertIn(hashlib.sha256((H/'system-setup/system_setup.py').read_bytes()).hexdigest(),src)
 def test_missing_each_tool_never_reaches_action(self):
  for missing in (setup.PYTHON,setup.PARSER):
   def trust(p,executable=False):
    if p==missing:raise FileNotFoundError(str(p))
   with patch.object(setup,'trusted',side_effect=trust),patch.object(setup,'install') as act,patch.object(setup,'immutable_inputs') as inputs,patch.object(sys,'argv',['setup','install']),self.assertRaises(FileNotFoundError):setup.main()
   act.assert_not_called();inputs.assert_not_called()
 def test_unreadable_loaded_names_never_installs(self):
  with patch.object(setup.os.path,'lexists',return_value=False),patch.object(Path,'read_text',side_effect=PermissionError()),patch.object(setup.os,'mkdir') as mkdir,self.assertRaises(PermissionError):setup.install()
  mkdir.assert_not_called()
 def test_each_destination_collision_stops_before_parser_and_write(self):
  for collision in (setup.DESTDIR,setup.POLICY):
   with patch.object(setup.os.path,'lexists',side_effect=lambda p:p==collision),patch.object(setup,'run_parser') as parse,patch.object(setup.os,'mkdir') as mkdir,self.assertRaisesRegex(RuntimeError,'collision'):setup.install()
   parse.assert_not_called();mkdir.assert_not_called()
 def test_profile_and_stack_collisions(self):
  for name in setup.NAMES:
   for mode in ('enforce','complain'):
    for label in (name,'bwrap//&'+name):
     with self.subTest(label=label,mode=mode),self.assertRaises(RuntimeError):setup.names_absent(label+' ('+mode+')\n')
  setup.names_absent('vkf-storage-private-v1 (enforce)\nbwrap (enforce)\n')
 def test_parser_nonzero_propagates_no_fallback(self):
  child=Mock(returncode=1);child.communicate.return_value=(b'',b'invalid policy')
  with patch.object(setup.subprocess,'Popen',return_value=child) as pop,self.assertRaises(RuntimeError):setup.run_parser('--add',setup.POLICY)
  pop.assert_called_once();child.communicate.assert_called_once()
 def test_compilation_always_no_load_no_cache(self):
  child=Mock(returncode=0);child.communicate.return_value=(b'policy',b'')
  with patch.object(setup.subprocess,'Popen',return_value=child) as pop:setup.run_parser('--stdout',setup.SOURCE,True)
  argv=pop.call_args.args[0]
  for flag in ('--skip-kernel-load','--skip-cache','--stdout','--config-file=/dev/null','--jobs=1','--max-jobs=1'):self.assertIn(flag,argv)
  self.assertNotIn('--replace',argv)
 def test_hash_mismatch_fatal(self):
  with self.assertRaises(RuntimeError):setup.checked_bytes(H/'system-setup/vkf-storage-private-v2','0'*64)
 def test_raw_contract_splits_exact_compiled_bytes(self):
  data=(H/'evidence/v2.compiled').read_bytes();c=json.loads((H/'compiled-profile-contract.json').read_text())
  self.assertEqual(hashlib.sha256(data).hexdigest(),setup.COMPILED_SHA)
  pieces=[]
  for p in c['profiles']:
   b=data[p['offset']:p['offset']+p['bytes']];pieces.append(b)
   self.assertEqual(hashlib.sha256(b).hexdigest(),setup.V2_RAW[p['name']])
  self.assertEqual(b''.join(pieces),data)
 def test_install_compile_load_verify_then_expose_order(self):
  events=[];compiled=(H/'evidence/v2.compiled').read_bytes()
  def parse(action,path,compile_only=False):events.append(('parser',action,compile_only));return compiled
  def checked(path,digest):events.append(('hash',str(path)));return b'pinned bytes'
  with patch.object(setup.os.path,'lexists',return_value=False),patch.object(Path,'read_text',return_value='bwrap (enforce)\n'),patch.object(Path,'lstat',return_value=types.SimpleNamespace(st_mode=0o40755,st_uid=0)),patch.object(setup,'trusted'),patch.object(setup,'checked_bytes',side_effect=checked),patch.object(setup,'run_parser',side_effect=parse),patch.object(setup.os,'mkdir',side_effect=lambda *a:events.append(('mkdir',))),patch.object(setup.os,'chmod',side_effect=lambda p,m:events.append(('chmod',str(p),m))),patch.object(setup,'exclusive_file',side_effect=lambda p,d,m:events.append(('write',str(p),m))),patch.object(setup,'fsyncdir'),patch.object(setup,'exact_loaded',side_effect=lambda *a:events.append(('loaded-equal',))),contextlib.redirect_stdout(io.StringIO()):setup.install()
  self.assertLess(events.index(('parser','--stdout',True)),events.index(('mkdir',)))
  self.assertLess(events.index(('write',str(setup.BINARY),0o600)),events.index(('parser','--add',False)))
  self.assertLess(events.index(('parser','--add',False)),events.index(('loaded-equal',)))
  self.assertEqual(events[-1],('chmod',str(setup.BINARY),0o755))
 def test_failed_loaded_equality_never_exposes_binary(self):
  compiled=(H/'evidence/v2.compiled').read_bytes()
  with patch.object(setup.os.path,'lexists',return_value=False),patch.object(Path,'read_text',return_value=''),patch.object(Path,'lstat',return_value=types.SimpleNamespace(st_mode=0o40755,st_uid=0)),patch.object(setup,'trusted'),patch.object(setup,'checked_bytes',return_value=b'pinned'),patch.object(setup,'run_parser',return_value=compiled),patch.object(setup.os,'mkdir'),patch.object(setup.os,'chmod') as chmod,patch.object(setup,'exclusive_file'),patch.object(setup,'fsyncdir'),patch.object(setup,'exact_loaded',side_effect=RuntimeError('mismatch')),self.assertRaisesRegex(RuntimeError,'mismatch'):setup.install()
  self.assertNotIn(unittest.mock.call(setup.BINARY,0o755),chmod.call_args_list)
 def test_rollback_hides_binary_then_removes_policy_then_files(self):
  events=[]
  with patch.object(setup,'trusted'),patch.object(setup,'checked_bytes'),patch.object(Path,'iterdir',return_value=iter([setup.BINARY])),patch.object(setup,'exact_loaded',side_effect=lambda *a:events.append('checked')),patch.object(setup.os,'chmod',side_effect=lambda *a:events.append('hidden')),patch.object(setup,'run_parser',side_effect=lambda action,*a:events.append(action)),patch.object(Path,'read_text',return_value=''),patch.object(Path,'unlink',side_effect=lambda:events.append('unlink')),patch.object(Path,'rmdir',side_effect=lambda:events.append('rmdir')),patch.object(setup,'fsyncdir'),contextlib.redirect_stdout(io.StringIO()):setup.rollback()
  self.assertEqual(events,['checked','hidden','--remove','unlink','unlink','rmdir'])
 def test_no_setup_execution_from_import(self):
  self.assertEqual(setup.NAMES,{'vkf-storage-private-v2','vkf-storage-pre-v2'})
if __name__=='__main__':unittest.main(verbosity=2)
