"""One authorized proposal correction using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149fc-2e0d-77d2-8ea3-5b44dd93f93d'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='CORRECTION / PROPOSAL compiler-lock-repair-14 ID01a149fc-2e0d-77d2-8ea3-5b44dd93f93d: preceding proposal notice erroneously retained native13 DONE template; NOT repair14 completion. Wrong intent/result and original script retained. Work ongoing. Review proposal /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/compiler-lock-repair-14/adapter.patch and sibling adapter.py: monotonic acquisition <=10s clipped to local adapter-entry budget, only contention errnos retried, read-only FD closes on errors, identity rechecked, exact SH validation preserved, reduced remaining timeout at payload entry. Local deadline is NOT true controller deadline; unchanged external controller timeout stays authoritative. Tests in progress. Root please forward to review15. Actual native13 holder unknown; no operational changes.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'proposal-correction-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-lock-repair-14-proposal-correction:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'proposal-correction-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
