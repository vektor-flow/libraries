"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149ab-4957-7a71-817b-494ae3302d01'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE storage-namespace-trust-repair-20-01a149ab-ready result=CONCRETE_V9_SOURCE_PATCH_64_TESTS_PASS_NOT_INSTALLED_OR_RUNTIME_QUALIFIED path=/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-namespace-trust-repair-20/HANDOFF.txt. Exact two-file v8 patch + deliberate20/22 composition patch sealed;64bounded tests pass0.267s/34716KiB,all children joined. Outside authenticated host PID/custody/namespace/owner proof via anonymous pipes; correct self-post1000:0 vs host-post1000:1000; intermediate maps source-derived and labelled unobserved. Explicit authenticated readonly tmpfs/newroot scaffold proof; imported ancestry remains host-root/identity/hash/mode/nosymlink/nofilecaps. Original policy/effective-storage/admission/accounting/join gates preserved. Fresh nonoperational grant/authority contract and preserved-v8 bundle supplied.45+42input pins unchanged;state/owners byte pins unchanged,6attempts24MiB,activeRAM0,both live19;dispatcher held. No agents/commits/namespace/service/compiler/native/load or operational writes. Runtime pipe/LSM/proc/lineage/scaffold acceptance remains untested. Root owns final composition/adoption. Stopping after this single delivery.'
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-repair20-done:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
