"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149e6-08dd-7253-b459-468c282e0130'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='BLOCKER compiler-admission-audit-12 01a149e6-08dd-7253-b459-468c282e0130: preparation09 seal_source.py lines6-12,30 still bind installed v6 plus hardcoded b1aaaec; source-contract.json is v6/historical HEAD, whereas actual qualified bundle is v9. adapter.py static_contract182-186 checks those bytes; evidence197-201 also needs a root export schema (live24/root-qualification-review.json is NOT that schema). Minimum fix belongs to peer11: reseal exact installed-v9 controller/config/five helpers/BINARIES/POLICY_INPUTS and current package/HEAD; root supplies genuine qualified-A evidence export. v6_bundle key alone is only legacy naming and can hold exact v9 pins; do not relaunch tiny qualification or re-review core53. Checking runtime closure/provenance/budget next; no operational changes.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'blocker-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-admission-audit-12-blocker:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'blocker-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
