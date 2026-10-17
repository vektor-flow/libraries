from pathlib import Path
import json,os,resource,signal,subprocess,sys,time
H=Path(__file__).resolve().parent;R=H.parents[2];I=H.parent
node=['/usr/bin/node','--jitless','--max-old-space-size=160','--max-semi-space-size=4']
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(536870912,)*2)
 resource.setrlimit(resource.RLIMIT_CPU,(55,)*2)
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
directory=str((H/'combined').relative_to(R));patch=str(H/'combined.patch')
steps=[('combined-check',['git','apply','--check','--whitespace=error-all','--directory='+directory,patch]),('combined-apply',['git','apply','--whitespace=error-all','--directory='+directory,patch]),('api21',[sys.executable,'-B',str(I/'latex-api-resource-integration-21/test_proposal.py')]),('selection-source',[sys.executable,'-B',str(I/'pdf-selection-implementation-22/verify_source.py')]),('combined-selection',node+['--import',str(H/'current-source-hooks.mjs'),str(H/'combined/examples/gpu-math/native-vkf/host/tests/pdf-selection-plan.mjs')]),('supplemental',node+['--import',str(H/'current-source-hooks.mjs'),str(H/'review-tests.mjs')]),('bridge',node+[str(R/'examples/gpu-math/native-vkf/host/tests/source-binding-bridge.mjs')]),('provenance',node+[str(R/'examples/gpu-math/native-vkf/host/tests/provenance-entry.mjs')])]
records=[]
for name,args in steps:
 start=time.monotonic();timeout=False
 with (H/(name+'.stdout')).open('xb') as out,(H/(name+'.stderr')).open('xb') as err:
  p=subprocess.Popen(args,cwd=R,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','SOURCE_BINDING_NATIVE_ROOT':str(R/'examples/gpu-math/native-vkf'),'PATH':'/home/viktor/.local/bin:'+os.environ['PATH']})
  try:p.wait(timeout=60)
  except subprocess.TimeoutExpired:timeout=True;os.killpg(p.pid,signal.SIGKILL);p.wait()
 records.append(dict(stage=name,argv=args,pid=p.pid,exit=p.returncode,seconds=time.monotonic()-start,joined=True,timeout=timeout))
 if p.returncode:break
result=dict(stages=records,passed=len(records)==len(steps) and all(r['exit']==0 for r in records),all_children_joined=True,maxrss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,as_limit_bytes=536870912,wall_limit_seconds=60,native_execution=False)
(H/'host-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));sys.exit(0 if result['passed'] else 1)
