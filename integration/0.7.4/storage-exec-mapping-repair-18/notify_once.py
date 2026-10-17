"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a14996-21e5-7d01-8d80-eced8f40d032'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE repair18-01a14996-ready | worker01a14996-21e5-7d01-8d80-eced8f40d032 | READY_ROOT_PATCH_SOURCE_ONLY: v2 custom profiles with exactly3 m additions (private Python; pre Python+bwrap), existing Px/denials/gates preserved. New dedicated byte-identical unshare, exact5-value helper patch, frozen original v7 bundle contract. No-load/no-cache compile PASS;43mock/source tests PASS; patch byte-exact;7test/parser children joined. Concrete unexecuted install/rollback uses existing tools and fail-closed collision/tool checks; no /usr/bin/rg. Current5loaded policies unchanged.5attempts20MiB activeRAM0 both owners live17 preserved; no recovery/setup/load/workload/agents/commits. MemAvailable19504857088 overlap0. No runtime proof; exact Ubuntu source unavailable and implicit later attachments remain limits. | /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-exec-mapping-repair-18/HANDOFF.txt'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
client=None
try:
    source=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/controller.py')
    spec=importlib.util.spec_from_file_location('existing_app_protocol',source)
    protocol=importlib.util.module_from_spec(spec);spec.loader.exec_module(protocol)
    client=protocol.client();client.sock.settimeout(20)
    thread=client.rpc('thread/read',dict(threadId=coordinator,includeTurns=True))['thread']
    active=protocol.active(thread)
    method='turn/steer' if active else 'turn/start'
    params=dict(threadId=coordinator,input=[dict(type='text',text=message)])
    if active:params['expectedTurnId']=active['id']
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-exec-mapping-repair-18-done:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
