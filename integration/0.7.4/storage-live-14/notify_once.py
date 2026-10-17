"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a14978-0c64-7903-aea1-f81eb80b1cf4'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE '+worker+' | STOP_ORIGIN_POLICY_GATE_NONZERO_CAPINH: first F service exit1, outer125 before namespace/payload; 2 authenticated rotations and locked owner publication succeeded. Real PIDs absent/cgroups empty; ledger running retains3GiB RAM and4MiB charge, no normal join/recovery. Total4attempts16MiB; remaining12/48MiB. No retry/policy/source change. MemAvailable19385446400; overlap0. | '+str(HERE/'HANDOFF.txt')
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-live-14-done:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
