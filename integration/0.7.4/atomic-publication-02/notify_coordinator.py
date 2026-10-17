"""One authorized notification to the existing coordinator; never retry."""
from pathlib import Path
import datetime
import importlib.util
import json
import uuid

OUT = Path(__file__).resolve().parent
SUPERVISOR = Path('/home/viktor/Projects/Vektor Flow/.worktrees/integration-0133/bootstrap/scripts/worker_supervisor_0136.py')
SOCKET = '/home/viktor/snap/codex/34/app-server-control/app-server-control.sock'
COORDINATOR = '01a14893-cb1e-7203-97dd-de3da44dcf31'
RECEIPT = OUT / 'coordinator-notification.json'
if RECEIPT.exists():
    raise SystemExit('Prior notification evidence exists: no retry allowed')
spec = importlib.util.spec_from_file_location('existing_supervisor', SUPERVISOR)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
client = module.Client(SOCKET)
record = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'coordinator': COORDINATOR, 'owner': '01a148fb-6f95-7aa3-a7f2-d4106680f3fb',
          'attempted': False, 'acknowledged': False}
try:
    thread = client.rpc('thread/read', {'threadId': COORDINATOR, 'includeTurns': True})['thread']
    active = [turn for turn in thread.get('turns', []) if turn.get('status') == 'inProgress']
    record['status'] = thread.get('status')
    message = (OUT / 'coordinator-message.txt').read_text()
    params = {'threadId': COORDINATOR, 'input': [{'type': 'text', 'text': message}]}
    if len(active) == 1:
        method = 'turn/steer'
        params['expectedTurnId'] = active[0]['id']
        record['expectedTurnId'] = active[0]['id']
    elif not active and thread.get('status', {}).get('type') == 'idle':
        method = 'turn/start'
        params['clientUserMessageId'] = str(uuid.uuid4())
    else:
        raise RuntimeError('Coordinator status has no unambiguous active/idle action; no notification sent')
    record.update(method=method, attempted=True)
    RECEIPT.write_text(json.dumps(record, indent=2) + '\n')
    response = client.rpc(method, params)
    record.update(acknowledged=True, response=response)
except Exception as error:
    record['error'] = str(error)
    raise
finally:
    client.close()
    RECEIPT.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({key: value for key, value in record.items() if key != 'response'}))
