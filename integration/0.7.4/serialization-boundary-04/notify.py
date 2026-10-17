"""One authorized completion notification; never retries an ambiguous send."""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
OUT=Path(__file__).resolve().parent
COORDINATOR='01a14893-cb1e-7203-97dd-de3da44dcf31'
HELPER=Path('/home/viktor/Projects/Vektor Flow/.worktrees/integration-0133/bootstrap/scripts/worker_supervisor_0136.py')
MESSAGE='DONE 01a148fe-2d9a-70c1-9659-7850815be709 | three-file independent ordered-tree patch; 211 source/model checks and 6 preparation tests pass; native unqualified | '+str(OUT/'HANDOFF.txt')
receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),coordinator=COORDINATOR,text=MESSAGE,helper_sha256=hashlib.sha256(HELPER.read_bytes()).hexdigest(),notification_attempts=0,owned_jobs_before_notification='all joined; zero background/native/service jobs')
def save(): (OUT/'notification.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert not (OUT/'notification.json').exists(), 'Never repeat notification after prior attempt'
spec=importlib.util.spec_from_file_location('existing_worker_client',HELPER)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
client=module.Client('/home/viktor/snap/codex/34/app-server-control/app-server-control.sock')
try:
    thread=client.rpc('thread/read',dict(threadId=COORDINATOR,includeTurns=True))['thread']
    receipt['observed_status']=thread.get('status')
    active=[t for t in thread.get('turns',[]) if t.get('status')=='inProgress']
    params=dict(threadId=COORDINATOR,input=[dict(type='text',text=MESSAGE)])
    if active:
        assert len(active)==1, 'Ambiguous active turn; no send'
        method='turn/steer';params['expectedTurnId']=active[0]['id']
    else:
        assert thread.get('status',{}).get('type')=='idle', 'No unambiguous active/idle state; no send'
        method='turn/start'
    receipt.update(method=method,expectedTurnId=params.get('expectedTurnId'),status='sending; no ambiguous retry',notification_attempts=1)
    save()
    response=client.rpc(method,params)
    receipt.update(status='acknowledged',response=response);save()
    print(json.dumps(dict(status=receipt['status'],method=method)))
except BaseException as error:
    receipt.update(status='error; do not retry',error=str(error));save();raise
finally:client.close()
