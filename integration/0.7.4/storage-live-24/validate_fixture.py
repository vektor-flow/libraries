"""Strict source-derived fixture schema, including BOTH post-fork print records."""
import hashlib

def validate_fixture(records,mode,manifest,payload_bytes):
 assert mode in ('success','nonzero','timeout')
 assert len(records)==(12 if mode=='timeout' else 10), 'unexpected fixture/helper record count'
 expected=[('private_workload_system_trust','pre-before-validation'),('private_workload_security','policy-gate'),('private_workload_snapshot','pre'),('private_workload_precondition',True),('private_workload_system_trust','post-before-validation'),('private_workload_security','policy-gate'),('private_workload_snapshot','post'),('private_workload_postcondition',True),('stage','mount-snapshot'),('mode',mode)]
 for row,(key,value) in zip(records,expected):assert row[key]==value
 assert payload_bytes==b'fresh storage qualification\n'*128
 report=records[9];assert report['outside_readonly'] is True and type(report['pid']) is int and report['pid']>0
 assert type(report['elapsed_seconds']) in (float,int) and report['elapsed_seconds']>=0
 proof=report['effective_storage'];assert proof==records[7]['private_workload_storage']
 assert records[6]['mountinfo']==records[8]['mountinfo']
 assert proof['mountinfo_sha256']==hashlib.sha256(records[8]['mountinfo'].encode('utf-8','surrogateescape')).hexdigest()
 charged=[r for r in proof['rows'] if r['result']=='charged-attempt']
 assert len(charged)==1 and charged[0]['path']==manifest['attempt_root'] and charged[0]['id']==proof['attempt_mount_id']
 assert report['pid_ns']==records[6]['context']['namespaces']['pid'] and report['net_ns']==records[6]['context']['namespaces']['net']
 if mode=='timeout':
  tail=records[10:];assert all(set(r)=={'namespace_pid','namespace_child'} for r in tail)
  assert all(type(v) is int and v>=0 for r in tail for v in r.values())
  parents=[r for r in tail if r['namespace_pid']==report['pid'] and r['namespace_child']>0]
  assert len(parents)==1;parent=parents[0]
  children=[r for r in tail if r['namespace_pid']==parent['namespace_child'] and r['namespace_child']==0]
  assert len(children)==1 and children[0]['namespace_pid']!=parent['namespace_pid']
 return dict(exact_fixture_records=True,fork_records=2 if mode=='timeout' else 0,exact_payload=True)
