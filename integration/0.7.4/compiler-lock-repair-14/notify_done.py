"""One actual authorized completion using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149fc-2e0d-77d2-8ea3-5b44dd93f93d'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE compiler-lock-repair-14 ID01a149fc-2e0d-77d2-8ea3-5b44dd93f93d RESULT SOURCE_PROPOSAL_READY_FOR_ROOT_INTEGRATION. Actual own completion; earlier wrong native13-template notice corrected/preserved. Exact adapter SHA4629f4ca3da296e60208e24baf203ee8700432a8a6c3d0b747a9d33b83d33484 matches review15. 16 focused tests +15 inherited validation cases pass1.494267s/55344KiB;4ordinary children joined; TEMP locks only. Exact patch and next native13 sequence12 USED-owner recipe delta ready. 10s conservative cap, local versus controller deadline and unbounded I/O/SH/guard-delay limits explicit. No native/operational/HEAD/seal changes. RESULT /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/compiler-lock-repair-14/result.json; HANDOFF /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/compiler-lock-repair-14/HANDOFF.txt. Root integrates/reseals once. Worker stops.'
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-lock-repair-14-actual-DONE:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
