"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a1498d-0c53-74c0-96a2-899999a3fc97'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE storage-live-17-01a1498d-stop | worker 01a1498d-0c53-74c0-96a2-899999a3fc97 | RESULT STOP/UNQUALIFIED: exact installed v7 F recovery-kind succession, unused A revocation and both authorized owner publications succeeded. First real F3GiB success case sandbox child4165055 SIGSEGV(-11), outer245, service199; kernel AppArmor file_mmap DENIED /usr/bin/python3.14 under vkf-storage-private-v1. Origin CapInh bit35 drop to0 and origin gate succeeded; no pre/post or fixture output. Actual normal service join independently reauthenticated; all recorded processes absent, cgroups empty, activeRAM0, no overlap, final MemAvailable19408031744.5/16attempts20/64MiB consumed;11attempts44MiB remain arithmetic only. F nonzero/timeout and all A UNRUN; no retry/policy/source/config changes/native/agents/commits. Both owners now live17; A high3GiB unchanged. HANDOFF/evidence: /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-17/HANDOFF.txt . One DONE delivery; stopping afterward.'
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-live-17-done:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
