"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149d1-1ba6-77f0-904a-23fc7490075b'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE storage-live-24-01a149d1-qualified | Worker 01a149d1-1ba6-77f0-904a-23fc7490075b. RESULT six tiny v9 combined20+22 real cases QUALIFIED: sequential F3GiB and A8GiB success/nonzero/timeout exits0/23/124; twelve actual ordered HostTrust stage proofs, actual readonly tmpfs/newroot, strict304-row storage tables, exact payloads, independent normal joins all pass. Both owners live24;7 atomic publications. Original6attempts24MiB plus6new =12/16attempts48/64MiB consumed;4attempts16MiB remaining arithmetic. ActiveRAM0,overlap0,Ahigh3GiB restored; unchanged hardA8/F3,parent21,swap0,Tasks128 and held dispatcher. All7 loaded profile bytes exact in8checks;243 input pins. Local Ftimeout wrapper count expected11 instead of source-correct12 (both fork prints); original failure archived,4positive29negative controls and full captured F revalidation passed with state/owner bytes unchanged, NO actual replay. No unexpected actual operation, recovery,native,source/policy/config edits,agents or commits. HEAD585704c held. HANDOFF: /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-24/HANDOFF.txt . One DONE delivery, stopping.'
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-live-24-done:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
