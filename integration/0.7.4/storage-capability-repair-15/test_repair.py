"""Mocked negatives and source preservation, no credential or namespace grants."""
import ast, contextlib, copy, ctypes, errno, hashlib, importlib.util, io, json, os, resource, sys, types, unittest
from pathlib import Path
from unittest.mock import Mock, patch
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(15,15))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
H=Path(__file__).resolve().parent
V=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v6')
sys.path[:0]=[str(H/'proposed'),str(V)]
import private_workload as pw
import storage_controller as sc
import storage_paths as sp
ORIGIN=dict(uid=1000,gid=1000,cgroup='/mock.service')
LABELS={'origin':'unconfined','pre':'vkf-storage-pre-v1 (enforce)','post':'bwrap//&unpriv_bwrap (enforce)'}
def status(stage):
 return dict(Uid=['1000']*4,Gid=['1000']*4,CapInh=['0000000000000000'],CapPrm=['0000000000000000'],CapEff=['0000000000000000'],CapAmb=['0000000000000000'],CapBnd=['0000000000000000' if stage=='post' else '000001ffffffffff'],NoNewPrivs=['1' if stage=='post' else '0'])
def raw(fields):return ''.join(k+':\t'+'\t'.join(v)+'\n' for k,v in fields.items())
def snapshot():
 s=status('origin');s.update(Groups=['1000'],Threads=['1'],CapInh=['0000000800000000']);return dict(status=s,label='unconfined',errors=[])
def clean():
 s=snapshot();s['status']['CapInh']=['0000000000000000'];return s
class CapabilityInitialization(unittest.TestCase):
 def invoke(self,before=None,after=None,drop_error=None,readlink=None):
  b=before if before is not None else snapshot();a=after if after is not None else clean()
  output=io.StringIO()
  with patch.object(pw,'_security_snapshot',side_effect=[b,a]),patch.object(pw,'_drop_capabilities',side_effect=drop_error) as call,patch.object(pw.os,'readlink',return_value=readlink or f'{os.getpid()}/task/{os.getpid()}'),contextlib.redirect_stdout(output):
   try:pw.initialize_origin_capabilities(ORIGIN)
   except BaseException as e:error=e
   else:error=None
  records=[json.loads(x) for x in output.getvalue().splitlines()]
  self.assertEqual([r['private_workload_security'] for r in records],['origin-capability-drop-before','origin-capability-drop-after'])
  self.assertEqual(records[-1]['passed'],error is None)
  if error:self.assertTrue(records[-1]['error'])
  return error,call,records
 def test_only_inheritable_drift_can_be_dropped(self):
  e,c,r=self.invoke();self.assertIsNone(e);c.assert_called_once_with()
  self.assertEqual(r[0]['status']['CapInh'],['0000000800000000']);self.assertEqual(r[1]['status']['CapInh'],['0000000000000000'])
 def test_each_active_set_rejected_before_syscall(self):
  for key in ('CapPrm','CapEff','CapAmb'):
   b=snapshot();b['status'][key]=['0000000000000001']
   with self.subTest(key=key):e,c,_=self.invoke(before=b);self.assertIsInstance(e,sp.Rejected);c.assert_not_called()
 def test_each_identity_slot_is_preserved(self):
  for key in ('Uid','Gid'):
   for slot in range(4):
    for value in ('0','2000'):
     b=snapshot();b['status'][key][slot]=value
     with self.subTest(key=key,slot=slot,value=value):e,c,_=self.invoke(before=b);self.assertIsInstance(e,sp.Rejected);c.assert_not_called()
 def test_nnp_and_label_fail_before_syscall(self):
  for b in [dict(snapshot(),label='unprivileged_userns (enforce)'),dict(snapshot(),status=dict(snapshot()['status'],NoNewPrivs=['1']))]:
   e,c,_=self.invoke(before=b);self.assertIsInstance(e,sp.Rejected);c.assert_not_called()
 def test_thread_restriction(self):
  b=snapshot();b['status']['Threads']=['2']
  e,c,_=self.invoke(before=b);self.assertIsInstance(e,sp.Rejected);c.assert_not_called()
  e,c,_=self.invoke(readlink=f'{os.getpid()}/task/999999');self.assertIsInstance(e,sp.Rejected);c.assert_not_called()
 def test_missing_malformed_caps_or_groups_reject(self):
  for key in ('CapInh','CapPrm','CapEff','CapAmb','CapBnd','Groups'):
   b=snapshot();del b['status'][key]
   with self.subTest(key=key):e,c,_=self.invoke(before=b);self.assertIsInstance(e,sp.Rejected);c.assert_not_called()
  for value in ('xyz','-000000000000001','0','0'*17):
   b=snapshot();b['status']['CapInh']=[value]
   e,c,_=self.invoke(before=b);self.assertIsInstance(e,sp.Rejected);c.assert_not_called()
 def test_drop_error_is_fatal_and_after_is_observed(self):
  for n in (errno.EPERM,errno.EINVAL,errno.ENOSYS):
   e,c,r=self.invoke(after=snapshot(),drop_error=OSError(n,os.strerror(n)))
   self.assertIsInstance(e,OSError);self.assertEqual(e.errno,n);c.assert_called_once();self.assertEqual(r[1]['status']['CapInh'],['0000000800000000'])
 def test_read_errors_before_and_after_are_fatal(self):
  e,c,r=self.invoke(before=dict(snapshot(),errors=['unreadable status']))
  self.assertIsInstance(e,sp.Rejected);c.assert_not_called();self.assertEqual(r[0]['observation_errors'],['unreadable status'])
  e,c,r=self.invoke(after=dict(clean(),errors=['unreadable label']))
  self.assertIsInstance(e,sp.Rejected);c.assert_called_once();self.assertEqual(r[1]['observation_errors'],['unreadable label'])
 def test_noop_or_partial_capset_cannot_pass(self):
  for key in ('CapInh','CapPrm','CapEff','CapAmb'):
   a=clean();a['status'][key]=['0000000800000000']
   e,c,_=self.invoke(after=a);self.assertIsInstance(e,sp.Rejected);c.assert_called_once()
 def test_preserved_fields_cannot_change(self):
  for key in ('Uid','Gid','Groups','Threads','CapBnd','NoNewPrivs'):
   a=clean();a['status'][key]=['999']
   e,c,_=self.invoke(after=a);self.assertIsInstance(e,sp.Rejected);c.assert_called_once()
  e,c,_=self.invoke(after=dict(clean(),label='other'));self.assertIsInstance(e,sp.Rejected);c.assert_called_once()
class SyscallBinding(unittest.TestCase):
 def test_v3_self_two_zero_words_exact_types(self):
  seen=[]
  def capset(header,data):
   seen.append((header._obj.version,header._obj.pid,ctypes.sizeof(data),ctypes.string_at(ctypes.addressof(data),ctypes.sizeof(data))))
   return 0
  with patch.object(ctypes,'CDLL',return_value=types.SimpleNamespace(capset=capset)) as lib:pw._drop_capabilities()
  lib.assert_called_once_with(None,use_errno=True)
  self.assertEqual(seen,[(0x20080522,0,24,b'\0'*24)])
  self.assertIs(capset.restype,ctypes.c_int);self.assertEqual(len(capset.argtypes),2)
 def test_errno_and_missing_symbol_fail_closed(self):
  def capset(*args):ctypes.set_errno(errno.EPERM);return -1
  with patch.object(ctypes,'CDLL',return_value=types.SimpleNamespace(capset=capset)),self.assertRaises(OSError) as cm:pw._drop_capabilities()
  self.assertEqual(cm.exception.errno,errno.EPERM)
  with patch.object(ctypes,'CDLL',return_value=types.SimpleNamespace()),self.assertRaises(AttributeError):pw._drop_capabilities()
 def test_unsupported_machine_os_endian_pointer_long_or_int_rejected(self):
  for key,value in [('machine','aarch64'),('machine','i686'),('platform','darwin'),('byteorder','big'),('pointer',4),('long',4),('int',8)]:
   with self.subTest(key=key),contextlib.ExitStack() as stack:
    library=stack.enter_context(patch.object(ctypes,'CDLL'))
    if key=='machine':stack.enter_context(patch.object(pw.os,'uname',return_value=types.SimpleNamespace(machine=value)))
    elif key in ('platform','byteorder'):stack.enter_context(patch.object(sys,key,value))
    else:
     actual=ctypes.sizeof;target={'pointer':ctypes.c_void_p,'long':ctypes.c_long,'int':ctypes.c_int}[key]
     stack.enter_context(patch.object(ctypes,'sizeof',side_effect=lambda x: value if x is target else actual(x)))
    with self.assertRaises(sp.Rejected):pw._drop_capabilities()
    library.assert_not_called()
class Integration(unittest.TestCase):
 def test_controller_drop_and_gate_fail_before_sandbox_or_popen(self):
  for fail in ('initialize_origin_capabilities','policy_gate'):
   c=sc.Controller.__new__(sc.Controller);c.current=Mock();c.ledger=Mock();c.key='mock';c.attach=Mock()
   c.g=dict(worker='F',attempt='mock',owned_processes=dict(path='/never-load'));c.config=dict(lane_cgroups={'F':'/lane'})
   cleanup=Mock();spec=Mock();spec.loader.exec_module=Mock();origin=dict(ORIGIN,cgroup='/lane/vkfworkers-f-mock.service')
   with patch.object(sc.importlib.util,'spec_from_file_location',return_value=spec),patch.object(sc.importlib.util,'module_from_spec',return_value=cleanup),patch.object(pw,'context',return_value=origin),patch.object(pw,'initialize_origin_capabilities') as drop,patch.object(pw,'policy_gate') as gate,patch.object(sc,'sandbox') as sandbox,patch.object(sc.subprocess,'Popen') as popen:
    (drop if fail=='initialize_origin_capabilities' else gate).side_effect=sp.Rejected('stop')
    with self.assertRaisesRegex(sp.Rejected,'stop'):c.inner()
    drop.assert_called_once_with(origin)
    if fail=='initialize_origin_capabilities':gate.assert_not_called()
    else:gate.assert_called_once_with('origin',origin)
    sandbox.assert_not_called();popen.assert_not_called();c.ledger.finish_service.assert_not_called()
 def test_installed_pins_still_match(self):
  for p in json.loads((H/'sourcepins.json').read_text()):self.assertEqual(hashlib.sha256(Path(p['path']).read_bytes()).hexdigest(),p['sha256'])
 def test_exact_controller_delta(self):
  old=(V/'storage_controller.py').read_text();new=(H/'proposed/storage_controller.py').read_text()
  self.assertEqual(new,old.replace("        private_workload.policy_gate('origin', context)","        private_workload.initialize_origin_capabilities(context)\n        private_workload.policy_gate('origin', context)"))
 def test_all_existing_helper_logic_preserved_except_observation(self):
  def functions(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
  old=functions(V/'private_workload.py');new=functions(H/'proposed/private_workload.py')
  self.assertEqual({k for k in old if old[k]!=new[k]},{'policy_gate'})
  # All strict validation statements and returned security fields are unchanged.
  def checks(path):
   f=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='policy_gate')
   begin=next(i for i,n in enumerate(f.body) if isinstance(n,ast.For) and isinstance(n.iter,ast.Tuple))
   return [ast.dump(n) for n in f.body[begin:] if not (isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='label')]
  self.assertEqual(checks(V/'private_workload.py'),checks(H/'proposed/private_workload.py'))
 def test_diagnostic_available_on_every_strict_gate_failure(self):
  for stage in LABELS:
   s=status(stage);s['CapInh']=['0000000800000000'];o=io.StringIO()
   with patch.object(pw,'_security_snapshot',return_value=dict(status=s,label=LABELS[stage],errors=[])),contextlib.redirect_stdout(o),self.assertRaises(sp.Rejected):pw.policy_gate(stage,ORIGIN)
   d=json.loads(o.getvalue());self.assertEqual(d['stage'],stage);self.assertEqual(d['status']['CapInh'],s['CapInh'])
 def test_observation_io_and_duplicate_failures_are_emitted_and_rejected(self):
  for mode in ('io','duplicate'):
   def read(p,*a,**kw):
    if str(p)=='/proc/self/attr/current':return 'unconfined'
    if mode=='io':raise PermissionError('test unreadable')
    return raw(status('origin'))+'Uid: 1000 1000 1000 1000\n'
   o=io.StringIO()
   with patch.object(Path,'read_text',read),contextlib.redirect_stdout(o),self.assertRaises(sp.Rejected):pw.policy_gate('origin',ORIGIN)
   self.assertTrue(json.loads(o.getvalue())['observation_errors'])
 def test_dependency_pins_and_absent_includes(self):pw.verify_dependencies()
# Reuse all nine prior strict policy test methods, without old installation assumptions.
prior=H.parent/'storage-policy-setup-11/test_policy.py'
tree=ast.parse(prior.read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PolicyGate')
source=ast.get_source_segment(prior.read_text(),node).replace("source=(H/'candidate/storage-direct-v6/private_workload.py').read_text()","source=(H/'proposed/private_workload.py').read_text()")
exec(compile(source,str(prior)+':PolicyGate','exec'),globals())
if __name__=='__main__':unittest.main(verbosity=2)
