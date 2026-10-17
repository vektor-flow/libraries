"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149a4-a1db-77a3-8094-f450e46d1ee8'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE storage-live-19-01a149a4-stop | RESULT STOP/UNQUALIFIED. Exact installed v8/v2 authenticated; normal F joined succession from live17, full post-F snapshot UNUSED-A revocation and separate atomic owner publication succeeded. First real F3GiB success case exit1: pre-stage trusted_system_file rejected /usr/local/libexec/vkf-storage-private-v2/unshare (private_workload.py:33-34 via gate:226). No pre/post diagnostics, mounts or fixture output. Host binary uid0/mode0755; namespace lstat fields were not emitted, mechanism not claimed. Kernel query no entries. Normal join independently verified; outer454/service725/child842 absent, lanes empty, activeRAM0; MemAvailable19480301568, overlap0. Both owners now live19.6/16attempts24/64MiB consumed;10attempts40MiB remaining arithmetic. F nonzero/timeout and all A UNRUN; no retry, recovery, guard/policy/source/config edits/native/agents/commits. HANDOFF: /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-live-19/HANDOFF.txt . One DONE delivery, stopping.'
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-live-19-done:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
