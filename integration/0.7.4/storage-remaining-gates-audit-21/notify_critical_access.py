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
message='CRITICAL REMAINING GATE audit21: independent predicted post effective-storage stop after trust repair. Installed effective_storage.py159-161 rejects EACCES;169-188 resolves every visible mountpoint. Current host mountinfo still has /run/user/60578/doc and /run/docker/netns/*; bounded host lstat (not namespace/probe execution) shows /run/user/60578 uid60578/gid975 mode0700, /run/docker uid0/gid0 mode0700. Current argv recursively ro-binds / and covers only /dev,/proc and charged attempt; it does not hide these /run trees. bwrap bind-mount.c475-477 explicitly skips EACCES remounts. Therefore user1000 post retains these enumerated, unresolved mounts and strict checker predicts rejection, despite fixed private propagation. Historical live09 rows49-65 corroborate exact inherited paths but failed earlier propagation gate; NOT a live19 observation. Preserve fail-closed inaccessible-path guard; no UID/name/fstype exceptions or permission changes. repair08 HANDOFF already lists this unresolved limit. Also repair20 must not require ancestor NS_GET_PARENT/NS_GET_USERNS from final child: documented EPERM outside own userns scope; use authenticated outside evidence if adding lineage. Evidence own audit21/host-topology-readonly.json; detailed source trace forthcoming. No attempt use.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'critical-access-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-remaining-gates-audit-21-critical-access:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'critical-access-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
