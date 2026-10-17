"""Read-only evidence and mocked negative gates, never setup/native execution."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H/'candidate/storage-direct-v6'))
import private_workload as pw
import storage_paths as sp
import storage_controller as sc
ORIGIN={'uid':1000,'gid':1000,'cgroup':'/mock.service'}
def status(stage):
 return dict(Uid=['1000']*4,Gid=['1000']*4,CapInh=['0'],CapPrm=['0'],CapEff=['0'],CapAmb=['0'],CapBnd=['0' if stage=='post' else '1ffffffffff'],NoNewPrivs=['1' if stage=='post' else '0'])
def raw(fields):return ''.join(k+':\t'+'\t'.join(v)+'\n' for k,v in fields.items())
LABELS={'origin':'unconfined','pre':'vkf-storage-pre-v1 (enforce)','post':'bwrap//&unpriv_bwrap (enforce)'}
class PolicyGate(unittest.TestCase):
 def call(self,stage,fields=None,label=None,origin=None):
  def read(path,*args,**kwargs):
   if str(path)=='/proc/self/status':return raw(status(stage) if fields is None else fields)
   if str(path)=='/proc/self/attr/current':return LABELS[stage] if label is None else label
   raise AssertionError(str(path))
  with patch.object(Path,'read_text',read):return pw.policy_gate(stage,origin or ORIGIN)
 def test_three_exact_labels_nnp_and_identity(self):
  for stage in LABELS:
   with self.subTest(stage=stage):self.assertEqual(self.call(stage)['label'],LABELS[stage])
 def test_each_credential_slot_rejects_root_or_other_user(self):
  for stage in LABELS:
   for field in ('Uid','Gid'):
    for slot in range(4):
     for value in ('0','2000'):
      s=status(stage);s[field][slot]=value
      with self.subTest(stage=stage,field=field,slot=slot,value=value),self.assertRaises(sp.Rejected):self.call(stage,s)
 def test_each_capability_set_rejects_nonzero(self):
  for stage in LABELS:
   for key in ('CapInh','CapPrm','CapEff','CapAmb')+(('CapBnd',) if stage=='post' else ()):
    s=status(stage);s[key]=['1']
    with self.subTest(stage=stage,key=key),self.assertRaises(sp.Rejected):self.call(stage,s)
 def test_pre_bounding_set_may_remain_but_post_must_be_empty(self):
  self.call('pre')
  s=status('post');s['CapBnd']=['1']
  with self.assertRaises(sp.Rejected):self.call('post',s)
 def test_nnp_is_never_cleared_or_accepted_at_wrong_stage(self):
  for stage in LABELS:
   s=status(stage);s['NoNewPrivs']=['0' if stage=='post' else '1']
   with self.subTest(stage=stage),self.assertRaises(sp.Rejected):self.call(stage,s)
 def test_missing_and_malformed_status_fail(self):
  for stage in LABELS:
   for key in status(stage):
    s=status(stage);del s[key]
    with self.subTest(stage=stage,key=key),self.assertRaises((sp.Rejected,KeyError)):self.call(stage,s)
  s=status('post');s['CapEff']=['not-hex']
  with self.assertRaises(ValueError):self.call('post',s)
 def test_old_unconfined_denial_complain_extra_and_missing_stack_rejected(self):
  for stage in ('pre','post'):
   for label in ('unconfined','unprivileged_userns (enforce)','bwrap (enforce)',
                 'unpriv_bwrap (enforce)','bwrap//&unpriv_bwrap (complain)',
                 'bwrap//&unpriv_bwrap//&other (enforce)','vkf-storage-pre-v1 (complain)',
                 ':other:bwrap//&unpriv_bwrap (enforce)'):
    with self.subTest(stage=stage,label=label),self.assertRaises(sp.Rejected):self.call(stage,label=label)
 def test_policy_failure_prevents_mount_read_and_exec(self):
  with patch.object(pw,'verify_dependencies'),patch.object(pw,'policy_gate',side_effect=sp.Rejected('policy')),\
       patch.object(pw.os,'execv') as execute,patch.object(pw,'context') as context:
   for stage in ('pre','post'):
    with self.assertRaises(sp.Rejected):pw.gate(stage,ORIGIN,'/charged',['/usr/bin/bwrap'])
   execute.assert_not_called();context.assert_not_called()
 def test_source_checks_both_gates_before_exec(self):
  source=(H/'candidate/storage-direct-v6/private_workload.py').read_text()
  gate=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='gate')
  text=ast.get_source_segment(source,gate)
  self.assertLess(text.index('policy_gate('),text.index('context()'))
  self.assertLess(text.index('effective_storage.check('),text.index('os.execv('))
  self.assertLess(text.index('private_snapshot('),text.index('os.execv('))
class Dependencies(unittest.TestCase):
 def mocks(self):
  return patch.multiple(pw,pinned=Mock(),trusted_system_file=Mock())
 def test_verified_metadata_policy_absences_and_restriction(self):
  with self.mocks(),patch.object(pw.os.path,'lexists',return_value=False),patch.object(Path,'read_text',return_value='1\n'):
   pw.verify_dependencies()
   self.assertEqual(pw.pinned.call_count,len(pw.BINARIES)+len(pw.POLICY_INPUTS))
   self.assertEqual(pw.trusted_system_file.call_count,pw.pinned.call_count)
 def test_each_new_local_override_fails_closed(self):
  for missing in pw.ABSENT_INCLUDES:
   with self.subTest(path=missing),self.mocks(),patch.object(pw.os.path,'lexists',side_effect=lambda p:p==missing):
    with self.assertRaisesRegex(sp.Rejected,'include appeared'):pw.verify_dependencies()
 def test_changed_policy_and_sysctl_fail_closed(self):
  with patch.object(pw,'pinned',side_effect=sp.Rejected('hash')),patch.object(pw,'trusted_system_file'):
   with self.assertRaises(sp.Rejected):pw.verify_dependencies()
  with self.mocks(),patch.object(pw.os.path,'lexists',return_value=False),patch.object(Path,'read_text',return_value='0\n'):
   with self.assertRaisesRegex(sp.Rejected,'restriction changed'):pw.verify_dependencies()
 def test_no_deployed_binary_or_profile_created(self):
  self.assertFalse(Path(pw.UNSHARE).exists())
  self.assertFalse(Path('/etc/apparmor.d/vkf-storage-private-v1').exists())
 def test_metadata_rejects_symlink_user_owner_writable_or_special_files(self):
  good=Mock(st_mode=stat.S_IFREG|0o755,st_uid=0)
  for mode,uid in [(stat.S_IFLNK|0o777,0),(stat.S_IFREG|0o755,1000),(stat.S_IFREG|0o777,0),(stat.S_IFREG|0o4755,0),(stat.S_IFDIR|0o755,0)]:
   bad=Mock(st_mode=mode,st_uid=uid)
   with patch.object(Path,'lstat',return_value=bad),patch.object(Path,'stat',return_value=bad),\
        patch.object(pw.os,'listxattr',return_value=[]),self.assertRaises(sp.Rejected):pw.trusted_system_file('/mock')
  with patch.object(Path,'lstat',return_value=good),patch.object(Path,'stat',return_value=good),\
       patch.object(pw.os,'listxattr',return_value=['security.capability']),self.assertRaises(sp.Rejected):pw.trusted_system_file('/mock')
 def test_policy_pins_in_grant_and_manifest_and_outside_roots(self):
  s=(H/'candidate/storage-direct-v6/storage_controller.py').read_text()
  self.assertIn("all(p in g['inputs'] and p in m['inputs'] for p in private_workload.POLICY_INPUTS)",s)
  self.assertIn('*private_workload.BINARIES, *private_workload.POLICY_INPUTS]',s)
  self.assertIn("private_workload.policy_gate('origin', context)",s)
class Preservation(unittest.TestCase):
 def test_only_two_v6_files_changed(self):
  old=H.parent/'storage-propagation-repair-10/candidate/storage-direct-v6';new=H/'candidate/storage-direct-v6'
  changed={p.name for p in old.iterdir() if p.is_file() and p.read_bytes()!=(new/p.name).read_bytes()}
  self.assertEqual(changed,{'private_workload.py','storage_controller.py'})
 def test_every_controller_method_except_current_inner_identical(self):
  def methods(p):
   t=ast.parse(p.read_text());return {n.name+'.'+m.name:ast.dump(m) for n in t.body if isinstance(n,ast.ClassDef) for m in n.body if isinstance(m,ast.FunctionDef)}
  a=methods(H.parent/'storage-propagation-repair-10/candidate/storage-direct-v6/storage_controller.py')
  b=methods(H/'candidate/storage-direct-v6/storage_controller.py')
  self.assertEqual(a.keys(),b.keys());self.assertEqual({k for k in a if a[k]!=b[k]},{'Controller.current','Controller.inner'})
 def test_installed_policy_observation_and_absence_unchanged(self):
  evidence=json.loads((H/'evidence/local-policy.json').read_text())
  self.assertEqual(evidence['restrict_unprivileged_userns'],'1');self.assertEqual(evidence['current_profile'],'unconfined')
  for p in evidence['files']:self.assertEqual(hashlib.sha256(Path(p['path']).read_bytes()).hexdigest(),p['sha256'])
  for p in evidence['missing_includes']:self.assertFalse(os.path.lexists(p))
 def test_minimal_profile_structure_no_policy_escape(self):
  p=(H/'system-setup/vkf-storage-private-v1').read_text()
  active='\n'.join(line for line in p.splitlines() if not line.lstrip().startswith('#'))
  self.assertEqual(active.count('profile '),2)
  self.assertEqual(active.count('allow capability'),1)
  self.assertIn('allow capability sys_admin,',active)
  self.assertEqual(active.count('allow mount '),1)
  self.assertIn('allow mount options=(rw,rprivate) -> /,',active)
  self.assertIn('/usr/bin/python3.14 Px -> vkf-storage-pre-v1,',active)
  self.assertIn('/usr/bin/bwrap Px -> bwrap,',active)
  for text in ('audit deny capability,','audit deny userns,','audit deny mount,','audit deny change_profile,'):self.assertIn(text,active)
  for text in (' ux',' Ux',' ix',' pix','flags=(unconfined','allow all','include ','<local/','capability,\n  allow'):self.assertNotIn(text,active)
 def test_existing_payload_stack_denial_present_in_actual_policy(self):
  s=Path('/etc/apparmor.d/bwrap-userns-restrict').read_text()
  self.assertIn('allow pix /** -> &bwrap//&unpriv_bwrap,',s)
  self.assertIn('allow pix /** -> &unpriv_bwrap,',s)
  self.assertIn('audit deny capability,',s)
if __name__=='__main__':unittest.main()
