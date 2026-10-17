"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149c3-9d8a-7542-8303-df8791f01fe2'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='ONE DONE storage-combined-trust-review-23-01a149c3-accept-source | RESULT: ACCEPT exact combined20+22 source proposal; no confirmed blocker or patch, runtime remains UNQUALIFIED. Actual source review and original-fixture gaps documented. New bounded TEST_ONLY real-pipe/ordinary-exec/pinned-wait_owned tests5/5 pass3.88s; all six processes joined. No deployment/policy/namespace/native operations, agents, commits or peer writes.105pins unchanged;6attempts24MiB,activeRAM0,live19 owners preserved; A/Fempty,dispatcherheld,MemAvailable19483303936bytes. PATH: /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-combined-trust-review-23/HANDOFF.txt (detailed REVIEW.txt alongside). Stopping after this delivery.'
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-review23-DONE:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
