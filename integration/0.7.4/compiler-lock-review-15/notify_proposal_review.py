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
message='REVIEW15 inspected repair14 adapter SHA2564629f4ca3da296e60208e24baf203ee8700432a8a6c3d0b747a9d33b83d33484, saved own exact snapshot/pin. No blocking correctness defect found in this draft: only EAGAIN/EWOULDBLOCK retry, same rb FD/context cleanup, post-acquire inode/dev canonical identity, original validate_runtime+validate_admission still inside SH, release before materialization/execute, late materialization/execute rejected and reduced timeout passed. 10s cap is a conservative failure policy, NOT source-proven sufficient guard maximum: EX includes full input hashing+multiple individually10s host calls. Could fail closed under legitimate slow guard; actual native13 holder/duration unknown. No cycle found in retained SH validation (finite local reads/hashes, no controller acknowledgment or Ledger transaction). I/O has no hard per-read deadline, so cannot claim strict bounded SH hold; existing v9 synchronous-guard timeout caveat remains unchanged. This does not warrant controller redesign for this correction. Checking focused counterexamples against pinned helper next.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'proposal-review-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-lock-review-15-proposal-review:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'proposal-review-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
