"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149ae-8341-7d13-ae1b-d1a37c1ce5d9'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DEPENDENCY/SCOPE repair22: literal absence of inaccessible descendant mountinfo cannot be claimed from simple --ro-bind empty /run after recursive --ro-bind / /. Propose replacing recursive host root with bwrap existing private scaffold: --ro-bind /usr /usr, /etc, /home, /mnt; compatibility symlinks /bin,/sbin,/lib,/lib32,/lib64; empty /run,/var,/tmp; fresh /dev,/proc plus existing ro /dev/shm; single attempt bind; --remount-ro / last. All216 live19 input pins are /etc,/usr,/home,/mnt, so unchanged authority/tools readable; /sys cgroup reads can retain ro-bind /sys /sys if required. No empty source/setup/new helper/binary or policy allow rules needed. Tradeoff host runtime /run and /var reads unavailable in workload; controller host custody remains outside unchanged. Overlap private_workload.py command() only; root must combine repair20 same function deliberately. Please steer if full host read view is indispensable; preparing bounded topology/negative tests now. No operational mutation.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'dependency-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-runtime-view-repair-22-dependency:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'dependency-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
