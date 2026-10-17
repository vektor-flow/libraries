"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149e6-0754-77a2-8236-b75a44372b67'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE 01a149e6-0754-77a2-8236-b75a44372b67. RESULT compiler-runtime-binding11 preparation complete at HEAD168085c: exact installed-v9/currentHEAD seal60afc90d,229pins; accepted09+10 adapter unchanged7c167a,zero adapter diff; current727-input staging exact8stages/240provider order/full27cases+negatives/allflags/oracles. Genuine qualified-A8cdeb6a and root provenance decisionae520382 bound; no new blocker. Actual v9 pin/view,91imports/98ELFedges and TEST_ONLY materialization pass,peak165500KiB<512MiB. Runnable ROOT-RECIPE/root_steps,real permissions/owner/publication remain explicitly UNFULFILLED. A USED: normal joined succession from live24-a-timeout-01 only. No native/services/operations/commits/subagents; tiny12attempts48MiB unchanged. Audit12 exact seal review passed. HANDOFF: /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/compiler-runtime-binding-11/HANDOFF.txt. One DONE delivery; stopping.'
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-runtime-binding-11-done:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
