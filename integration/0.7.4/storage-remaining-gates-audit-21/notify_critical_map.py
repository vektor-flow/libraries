"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149ab-4aec-72c3-9f1c-406b345266a4'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='CRITICAL SOURCE COMPATIBILITY audit21 -> root/repair20: exact installed Ubuntu bwrap0.11.1-1ubuntu0.3 --dev /dev sets opt_needs_devpts=true (ubuntu-bubblewrap.c2147); unprivileged child maps ns UID/GID0 -> parent1000 (3291-3305), then after mounts unshare(CLONE_NEWUSER) and write_uid_gid_map(final1000, ns0, final1000, ns0,-1,false,false) (3456-3501). Expected self post map is1000 0 1, NOT pre1000 1000 1. mnt/pid/net namespaces are owned by intermediate bwrap userns, not final post userns. No extra cgroup namespace requested. Current v8 checks maps only pre; this is a concrete counterexample for repair20 stage-aware proof assumptions, not an observed live19 post failure (live19 never reached pre policy gate). Preserve exact composed mapping/lineage guards; do not reuse pre map or require final userns to own mnt/pid/net. Source trace and regression suggestions will be in own audit21 output; no implementation or attempt consumed.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'critical-map-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-remaining-gates-audit-21-critical-map:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'critical-map-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
