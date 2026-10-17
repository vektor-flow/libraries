"""Synthetic controls of runtime evidence parser; no live trust/namespace proof."""
import copy,json,os,stat,hashlib,resource
from preflight import save,REPAIR
import private_workload as pw
from validate_trust import validate_trust
from storage_paths import Rejected
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(20,20))
def fixture():
 origin=pw.context();origin['cgroup']='/test/live24.service';origin['trust_channel']=dict(request_fd=7,reply_fd=8,nonce='0'*64)
 m=dict(attempt_root='/mnt/development/TEST_ONLY_live24',cwd='/mnt/development/TEST_ONLY_live24/cwd',inputs=[dict(path=str(REPAIR/'fixture.py'),sha256='0'*64)],argv=[pw.PYTHON,'-B',str(REPAIR/'fixture.py'),'success','/mnt/development/TEST_ONLY_live24',str(REPAIR/'fixture.py'),origin['namespaces']['pid'],origin['namespaces']['net']]);g=copy.deepcopy(m)
 argv=pw.command(m,origin);i=argv.index('pre');preargv=argv[i+4:];j=preargv.index('post')
 base=pw.trust_observation();pw.validate_observation(base,host=True)
 service=[dict(private_workload_system_trust='host-before-validation',context=copy.deepcopy(origin),observation=copy.deepcopy(base),reason=None)]
 records=[];proofs=[];tracked=[]
 for n,stage in enumerate(['pre','post']):
  hostctx=copy.deepcopy(origin);hostctx.pop('trust_channel')
  for name in pw.NS_NAMES:
   if name in ['mnt','user'] or (stage=='post' and name in ['pid','net']):hostctx['namespaces'][name]=name+':['+str(50000+n*10+list(pw.NS_NAMES).index(name))+']'
  hostctx['maps']={k:f'{origin[k]} {origin[k]} 1\n' for k in ['uid','gid']}
  ctx=copy.deepcopy(hostctx);ctx['maps']={k:f'{origin[k]} {origin[k] if stage=="pre" else 0} 1\n' for k in ['uid','gid']}
  obs=copy.deepcopy(base);raw='123 122 0:999 /newroot / ro,nosuid,nodev - tmpfs tmpfs ro\n'
  if stage=='post':
   obs['paths']['/'].update(st_dev=os.makedev(0,999),st_ino=50000,st_mode=stat.S_IFDIR|0o755,st_uid=origin['uid'],st_gid=origin['gid'])
   obs['root_mount']=dict(id=123,path='/',root='/newroot',dev=[0,999],fstype='tmpfs',options=['ro','nosuid','nodev'],optional=[],readonly=True)
  local=copy.deepcopy(obs)
  for row in local['paths'].values():
   for kind in ['uid','gid']:row['st_'+kind]=origin[kind] if row['st_'+kind]==origin[kind] else ctx['overflow'][kind]
  process=dict(pid=70000+n,starttime=80000+n,ppid=69999,executable=pw.PYTHON,argv=argv[i-4:i+4]+preargv if stage=='pre' else preargv[j-4:],context=hostctx)
  proof=dict(stage=stage,process=process,lineage={name:[4,int(value.split('[')[1][:-1])] for name,value in ctx['namespaces'].items()},self_maps=ctx['maps'],host_maps=hostctx['maps'],intermediate_maps_observed=False,scaffold_root=obs['root_mount'] if stage=='post' else None,observation_sha256=hashlib.sha256(pw._frame(obs)).hexdigest())
  service.append(dict(private_workload_system_trust='host-observer-'+stage,context=hostctx,observation=obs,reason=None))
  records.extend([dict(private_workload_system_trust=stage+'-before-validation',context=ctx,observation=local,reason=None),dict(private_workload_snapshot=stage,context=copy.deepcopy(ctx),mountinfo=raw)])
  proofs.append(proof);tracked.append(dict(pid=process['pid'],starttime=process['starttime']))
 row=dict(custody=dict(cgroup=origin['cgroup']),service=dict(identity=dict(cgroup=origin['cgroup'])),inner_result=dict(system_trust_proofs=proofs,system_trust_error=None,sandbox_argv=argv,tracked=tracked))
 return dict(service=service,records=records,row=row,g=g,m=m)
def check(f):return validate_trust('\n'.join(json.dumps(x) for x in f['service']),f['records'],f['row'],f['g'],f['m'])
f=fixture();assert check(f)['ordered_stages']==['pre','post']
neg=[]
def case(name,mutate):
 b=copy.deepcopy(f);mutate(b)
 try:check(b)
 except (AssertionError,KeyError,ValueError,TypeError,Rejected):neg.append(name)
 else:raise AssertionError('invalid evidence accepted: '+name)
case('empty stdout',lambda b:b['service'].clear())
case('missing payload records',lambda b:b['records'].clear())
case('missing proofs',lambda b:b['row']['inner_result']['system_trust_proofs'].clear())
case('reverse proofs',lambda b:b['row']['inner_result']['system_trust_proofs'].reverse())
case('trust error',lambda b:b['row']['inner_result'].update(system_trust_error='error'))
case('observer rejection',lambda b:b['service'][1].update(reason='denied'))
case('local rejection',lambda b:b['records'][0].update(reason='denied'))
case('host unknown errors',lambda b:b['service'][1]['observation']['errors'].append(dict(path='/',reason='EPERM')))
case('local unknown errors',lambda b:b['records'][0]['observation']['errors'].append(dict(path='/',reason='EPERM')))
case('digest mismatch',lambda b:b['row']['inner_result']['system_trust_proofs'][0].update(observation_sha256='0'*64))
case('fake intermediate maps',lambda b:b['row']['inner_result']['system_trust_proofs'][1].update(intermediate_maps_observed=True))
case('no tracked process',lambda b:b['row']['inner_result']['tracked'].clear())
for field,val in [('pid',1),('starttime',1),('executable','/bad'),('argv',[]),('ppid',0)]:
 case('process '+field,lambda b,k=field,v=val:b['row']['inner_result']['system_trust_proofs'][0]['process'].update({k:v}))
case('bad namespace FD identity',lambda b:b['row']['inner_result']['system_trust_proofs'][1]['lineage']['user'].__setitem__(1,99))
case('missing namespace FD identity',lambda b:b['row']['inner_result']['system_trust_proofs'][1]['lineage'].pop('mnt'))
case('self map host confusion',lambda b:b['records'][2]['context']['maps'].update(uid='1000 1000 1\n'))
case('host map self confusion',lambda b:b['service'][2]['context']['maps'].update(uid='1000 0 1\n'))
case('scaffold writable',lambda b:b['service'][2]['observation']['root_mount'].update(readonly=False))
case('scaffold host root',lambda b:b['service'][2]['observation']['paths'].__setitem__('/',copy.deepcopy(b['service'][0]['observation']['paths']['/'])))
case('scaffold wrong type',lambda b:b['service'][2]['observation']['root_mount'].update(fstype='ext4'))
case('scaffold wrong source',lambda b:b['service'][2]['observation']['root_mount'].update(root='/'))
case('scaffold propagation',lambda b:b['service'][2]['observation']['root_mount'].update(optional=['master:1']))
case('scaffold wrong owner',lambda b:b['service'][2]['observation']['paths']['/'].update(st_uid=0))
case('imported owner changed',lambda b:b['service'][2]['observation']['paths']['/usr'].update(st_uid=1000))
case('system digest changed',lambda b:b['service'][1]['observation']['files'][pw.PYTHON].update(sha256='0'*64))
case('system capabilities',lambda b:b['service'][1]['observation']['files'][pw.PYTHON].update(filecaps=True))
case('missing host stage',lambda b:b['service'].pop())
case('extra host stage',lambda b:b['service'].append(copy.deepcopy(b['service'][2])))
save('trust-parser-tests.json',dict(passed=True,positive=1,negative=len(neg),cases=neg,synthetic_only=True,runtime_qualification=False))
print('PASS trust evidence parser: 1 synthetic positive,',len(neg),'negative controls')
