"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149ae-8341-7d13-ae1b-d1a37c1ce5d9'
coordinator='01a149ab-4957-7a71-817b-494ae3302d01'
message='COMMAND HUNK COORDINATION repair22 under root instruction: root accepted explicit workload read view /usr,/etc,/home,/mnt; compatibility /bin,/sbin,/lib,/lib32,/lib64; empty scaffold /run,/var,/tmp; fresh /dev,/proc; readonly original /dev/shm; exact charged attempt; final --remount-ro /. No /sys absent concrete need. Own proposed/private_workload.py and runtime-view.patch versus frozenv8 add RUNTIME_READ_TREES/RUNTIME_LINKS/runtime_view(m) immediately before command(), replace bwrap root --ro-bind / / with *runtime_view(m), add root remount after attempt bind. command encoding/helper/pre/post transport remains byte-identical. Please preserve these semantic changes when root combines your command transport; no edits to your files. No immutable empty input/new helper/binary or policy delta. Model/input closure tests underway, no runtime operations. Root coordinator has dependency notice; final review is root-owned.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'repair20-coordination-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-runtime-view-repair-22-repair20:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'repair20-coordination-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
