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
message='REVIEW15 concrete TEMP result: original one-shot EAGAIN reproduced; transient EX release->SH acquired in0.307s; persistent EX bounded failure0.100s. Actual installed owned.wait_owned(timeout=.06, guard=TEMP LOCK_EX) returned124 after0.425s while TEMP SH holder lived. All3children joined/absent, suite1.231s,maxRSS~16MiB each. No live capacity lock or service/native work. This is delayed synchronous timeout, not proof of deadlock/native13 holder. Existing wait_owned deadline already includes adapter contention; avoid claiming a new1200s-from-adapter-entry is the controller whole-run deadline. Minimal fix should consume wait+validation+materialization in local payload remaining budget, release SH before executing, retain external installed timeout. Existing controller limitation need not trigger v9 redesign. Awaiting repair14 proposal for concrete review; models/results in integration/0.7.4/compiler-lock-review-15/process-model-results.json.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'model-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-lock-review-15-model:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'model-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
