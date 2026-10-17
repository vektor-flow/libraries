"""One authorized DONE delivery using the existing app-server Client. No retry."""
import sys
sys.dont_write_bytecode=True
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149fc-2f96-7a31-bb18-5c4b989339cc'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='LOCK REVIEW15 01a149fc-2f96-7a31-bb18-5c4b989339cc: Source-confirmed legitimate contention: installed v9 storage_admission.py503 guard_service holds transaction LOCK_EX through authenticate->current (all grant inputs hashed), host (legacy+active service checks), ledger.check. inner guard runs immediately after launch (last=0), then >=1s after each completion. Actual native13 holder UNKNOWN. No source lock cycle found: these callbacks do not wait for adapter validation. Critical liveness constraint: owned-processes.py guard executes synchronously BEFORE remaining-deadline check; an adapter SH holder can block EX guard and delay timeout. Keep SH validation finite and release before materialization/payload; do not wait for a controller event while SH held. Bounded SH polling should retry only contention errors, use monotonic remaining budget, preserve checks under SH, pass reduced remaining budget to payload rather than restart1200. Inspecting isolated process counterexample next; no live locks or installed changes.'
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-lock-review-15-blocker:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'blocker-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
