"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149ab-4957-7a71-817b-494ae3302d01'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='Repair20 concrete two-file v8->v9 candidate now in own proposed/. Outside admitted controller polls inherited anonymous request/reply pipes within unchanged wait_owned; authenticates live PID/starttime/argv/exe/cgroup/descendant and actual namespace fd lineage; host composed maps vs child self maps are separate. No sockets/policy delta or child ancestor introspection. Scaffold integration explicit: runtime_view source composition enables ONLY constructed / proof (tmpfs /newroot,0755 mapped owner,ro/nosuid/nodev,actual descriptor readonly+dev); /usr,/etc/all imported dependency ancestry remains host-root/identity/mode/hash/no-links/no-filecaps. command() unchanged in20, so22 hunk composes directly. First48bounded tests47pass/1model fake graph fixture KeyError corrected; final expanded tests/immutable pins/handoff forthcoming. No operational or attempt changes; no namespace probes. Host anchor is boot-bound observed source authority, fresh grant required; no arbitrary trust flags/receipts.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'implementation-progress-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-repair20-progress:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'implementation-progress-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
