import json,os,pathlib,subprocess,sys,time
OUT=pathlib.Path(__file__).resolve().parent;PACKET=OUT.parent/'compiler-controls-binding-23'
STORAGE=pathlib.Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
def main():
 step=sys.argv[1];assert not (OUT/'STOP.json').exists()
 auth=json.loads((STORAGE/'d288-native-24-visible-chat-grant.json').read_text())['root_decision']
 if step in ('rotate','export','publish'):
  cmd=['/usr/bin/python3','-I','-B',str(PACKET/'root_steps.py'),step,'--decision',auth['path'],'--decision-sha256',auth['sha256']]
 elif step=='assemble':
  cmd=['/usr/bin/timeout','--signal=TERM','--kill-after=2s','60s','/usr/bin/python3','-I','-B',str(PACKET/'adapter.py'),'assemble','--plan',str(PACKET/'staging/d288/plan.json'),'--root-inputs',str(PACKET/'root-inputs.json'),'--out',str(PACKET/'root-packet')]
 else:raise ValueError(step)
 with (OUT/(step+'-intent.json')).open('x') as f:json.dump(dict(argv=cmd),f)
 start=time.monotonic()
 with (OUT/(step+'.stdout')).open('xb') as out,(OUT/(step+'.stderr')).open('xb') as err:r=subprocess.run(cmd,stdout=out,stderr=err)
 result=dict(step=step,exit=r.returncode,seconds=time.monotonic()-start,children_joined=True)
 with (OUT/(step+'-result.json')).open('x') as f:json.dump(result,f,indent=2)
 if r.returncode:
  with (OUT/'STOP.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result));raise SystemExit(r.returncode)
if __name__=='__main__':main()
