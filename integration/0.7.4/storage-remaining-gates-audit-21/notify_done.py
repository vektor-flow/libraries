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
message='DONE audit21-01a149ab-source-complete | RESULT READ_ONLY_AUDIT_COMPLETE: exact installed v8/package-source63pins verified; predicted inaccessible inherited /run mount post blocker handed to separate22; repair20 has exact self/host map distinctions, U2 nonuser ownership and child ancestor ioctl EPERM constraints. Host observer follow-up finds no source-established blanket same-owner denial after final readiness/dumpable1; conditional source compatibility only, actual Ubuntu access unqualified. SOURCE-TRACE.txt provides exact lines and minimal unexecuted regressions; no implementation/topology edits/probes/services/native/compiler/load/agents/commits or attempt use. State/owners unchanged live19,6attempts24MiB activeRAM0; finalMemAvailable19488342016 overlap0 dispatcher held. | /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-remaining-gates-audit-21/HANDOFF.txt | Stop after this one DONE.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'done-notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'storage-remaining-gates-audit-21-done:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'done-notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
