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
message='COMBINATION REQUIREMENT repair22: root-accepted scaffold changes final / device/inode/owner from host root; /usr,/etc,/home,/mnt root objects and children still same source identities via ro-bind, but a host ancestry inventory must NOT assume / itself remains host root. Coordinate repair20 trust transport explicitly: authenticate original source ancestry at origin/pre, prove constructed final / via exact command/custody/namespace plus strict readonly scaffold observation, preserve imported source object identity/mode/no-symlink/digest checks and all existing guards. Do not invent UID exception or broadly skip parent validation. My proposal does NOT edit trust functions. Tests currently pass17new+prior checker regression, all1155 read paths accessible incl727 compiler inputs/29ELF-edge endpoints/fonts/Python-libffi/authority;293retained mount boundaries inspectable host-side. Full live map/LSM/scaffold trust remains unqualified. Hunk private_workload.py runtime_view helper + command two mount-list changes; root combines with20.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'repair20-scaffold-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-runtime-view-repair-22-repair20-scaffold:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'repair20-scaffold-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
