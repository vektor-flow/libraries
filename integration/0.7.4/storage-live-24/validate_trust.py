"""Reconcile exact v9 runtime records; no namespace operations or trust overrides."""
import hashlib,json,os
import private_workload as pw
from storage_paths import strict_json

def parse(text):
 return [strict_json(line) for line in text.splitlines() if line.strip()]
def validate_trust(service_stdout,records,row,g,m):
 service=parse(service_stdout);diags=[x for x in service if 'private_workload_system_trust' in x]
 assert diags and all(x['reason'] is None for x in diags)
 assert all(x['private_workload_system_trust'] in ['host-before-validation','host-observer-pre','host-observer-post'] for x in diags)
 hosts=[x for x in diags if x['private_workload_system_trust'].startswith('host-observer-')]
 assert [x['private_workload_system_trust'] for x in hosts]==['host-observer-pre','host-observer-post']
 locals=[x for x in records if 'private_workload_system_trust' in x]
 assert [x['private_workload_system_trust'] for x in locals]==['pre-before-validation','post-before-validation']
 assert all(x['reason'] is None for x in locals)
 result=row['inner_result'];proofs=result['system_trust_proofs']
 assert result['system_trust_error'] is None and [p['stage'] for p in proofs]==['pre','post']
 argv=result['sandbox_argv'];i=argv.index('pre');origin=strict_json(argv[i+1]);preargv=argv[i+4:];j=preargv.index('post')
 assert argv==pw.command(m,origin) and preargv[j+4:]==m['argv']==g['argv']
 channel=origin['trust_channel'];assert set(channel)=={'request_fd','reply_fd','nonce'}
 assert all(type(channel[k]) is int and channel[k]>2 for k in ['request_fd','reply_fd']) and channel['request_fd']!=channel['reply_fd']
 assert len(channel['nonce'])==64 and all(c in '0123456789abcdef' for c in channel['nonce'])
 assert origin['boot']==pw.HOST_NAMESPACE_ANCHOR['boot'] and origin['namespaces']==pw.HOST_NAMESPACE_ANCHOR['namespaces']
 assert origin['cgroup']==row['custody']['cgroup']==row['service']['identity']['cgroup']
 assert origin['uid']==os.getuid()!=0 and origin['gid']==os.getgid()!=0
 baselines=[d for d in diags if d['private_workload_system_trust']=='host-before-validation']
 assert baselines
 base=baselines[0]['observation']
 for d in baselines:
  assert d['context']['boot']==origin['boot'] and d['context']['namespaces']==origin['namespaces']
  pw.validate_observation(d['observation'],host=True);pw.compare_host(base,d['observation'])
 snapshots=[x for x in records if 'private_workload_snapshot' in x]
 assert [s['private_workload_snapshot'] for s in snapshots]==['pre','post']
 for n,stage in enumerate(['pre','post']):
  proof,host,local,snap=proofs[n],hosts[n],locals[n],snapshots[n]
  assert set(proof)=={'stage','process','lineage','self_maps','host_maps','intermediate_maps_observed','scaffold_root','observation_sha256'}
  assert proof['intermediate_maps_observed'] is False
  process=proof['process'];ctx=process['context'];selfctx=local['context'];obs=host['observation']
  assert ctx==host['context'] and selfctx==snap['context']
  pw.validate_stage_context(stage,selfctx,origin)
  assert ctx['namespaces']==selfctx['namespaces'] and ctx['boot']==origin['boot'] and ctx['overflow']==origin['overflow']
  assert ctx['cgroup']==origin['cgroup'] and ctx['uid']==origin['uid'] and ctx['gid']==origin['gid']
  assert type(process['pid']) is int and process['pid']>0 and type(process['starttime']) is int and process['starttime']>0
  assert type(process['ppid']) is int and process['ppid']>0 and process['executable']==pw.PYTHON
  expected=argv[i-4:i+4]+preargv if stage=='pre' else preargv[j-4:]
  assert process['argv']==expected
  assert any(t['pid']==process['pid'] and t['starttime']==process['starttime'] for t in result['tracked']), 'proof PID/starttime outside owned join'
  assert set(proof['lineage'])==set(pw.NS_NAMES)
  for name,ident in proof['lineage'].items():
   assert type(ident) is list and len(ident)==2 and all(type(x) is int and x>0 for x in ident)
   assert ctx['namespaces'][name]==name+':['+str(ident[1])+']'
  assert proof['self_maps']==selfctx['maps'] and proof['host_maps']==ctx['maps']
  for kind in ['uid','gid']:
   pw.single_map(proof['self_maps'][kind],origin[kind],origin[kind] if stage=='pre' else 0)
   pw.single_map(proof['host_maps'][kind],origin[kind],origin[kind])
  scaffold=origin if stage=='post' else None
  pw.compare_host(base,obs,scaffold);pw.compare_namespace(obs,local['observation'],selfctx,origin)
  assert proof['observation_sha256']==hashlib.sha256(pw._frame(obs)).hexdigest()
  assert proof['scaffold_root']==(obs['root_mount'] if stage=='post' else None)
  if stage=='post':
   mounts=pw.effective_storage.parse_mountinfo(snap['mountinfo']);root=next(x for x in mounts.values() if x.path=='/')
   assert root.id==obs['root_mount']['id'] and root.root=='/newroot' and root.fstype=='tmpfs' and not root.optional
 assert proofs[0]['lineage']['cgroup']==proofs[1]['lineage']['cgroup']
 return dict(ordered_stages=['pre','post'],proofs=proofs,source_authenticated_fd_lineage=True,intermediate_maps_observed=False,observations_digest_bound=True)
