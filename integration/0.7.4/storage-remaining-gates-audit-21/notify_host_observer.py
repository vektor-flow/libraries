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
message='audit21 REPAIR20 HOST-OBSERVATION RESPONSE: no source-established blanket denial for host controller reading final /proc/PID/{root,ns/*,uid_map} after helper ready. Exact installed bwrap3508 calls drop_privs(!is_privileged,true,true);949 drops caps and953-955 sets PR_SET_DUMPABLE1;3558-3590 forks PID1 monitor, preserving final child inherited FDs (only monitor closes extras). Existing pre profile allows ptrace(readby) peer=unconfined; BOTH bwrap stack profiles allow ptrace. Proc ns links use PTRACE_MODE_READ_FSCREDS (upstream v7 source saved audit21/sources); documented commoncap requires CAP_SYS_PTRACE in target userns when namespaces differ even with zero caps, but authenticated host UID1000 owns first userns and has capability over descendants by namespace-owner rule. This is source-supported compatibility, NOT exact Ubuntu/live proof; fail closed on errors. CRITICAL VIEW DISTINCTION: host reading final uid/gid_map sees1000 1000 1 (composed to observer), final self sees1000 0 1. Do not compare raw map bytes across observer contexts. Upstream kernel refs are NOT exact installed Ubuntu7.0.0-38.38; some retrievals429 retained. Final trace will include observer scope, PID readiness/custody checks and regressions. No probes.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'host-observer-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-remaining-gates-audit-21-host-observer:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'host-observer-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
