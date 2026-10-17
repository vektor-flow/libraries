"""Exactly one authorized DONE to the existing coordinator; no ambiguous retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid

HERE = Path(__file__).resolve().parent
WORKER = '01a14945-5b8e-74b0-b054-403b2fd996aa'
COORDINATOR = '01a14893-cb1e-7203-97dd-de3da44dcf31'
MESSAGE = ('DONE ' + WORKER + ' | Unapplied 3-file host source-binding bridge: real revision/provenance APIs, '
           'eight PDF columns and exact native argument adapters; 17 behavior tests plus existing suites pass; '
           'typed-document authentication only, native/renderer UNEXECUTED; all children joined | ' + str(HERE / 'HANDOFF.txt'))
for path, expected in json.loads((HERE / 'artifact-pins.json').read_text())['sha256'].items():
    assert hashlib.sha256((HERE / path).read_bytes()).hexdigest() == expected, path
intent = {'coordinator': COORDINATOR, 'message': MESSAGE, 'attempts': 1,
          'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
with (HERE / 'notification-intent.json').open('x') as stream:
    json.dump(intent, stream, indent=2); stream.write('\n')
client = None
try:
    source = Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/controller.py')
    spec = importlib.util.spec_from_file_location('existing_app_protocol', source)
    protocol = importlib.util.module_from_spec(spec); spec.loader.exec_module(protocol)
    client = protocol.client(); client.sock.settimeout(20)
    thread = client.rpc('thread/read', {'threadId': COORDINATOR, 'includeTurns': True})['thread']
    active = protocol.active(thread)
    method = 'turn/steer' if active else 'turn/start'
    params = {'threadId': COORDINATOR, 'input': [{'type': 'text', 'text': MESSAGE}]}
    if active:
        params['expectedTurnId'] = active['id']
    else:
        params['clientUserMessageId'] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'host-source-binding-05-done:' + WORKER))
    response = client.rpc(method, params)
    record = {'method': method, 'acknowledged': True, 'retry': False,
              'turn_id': response.get('turnId') or response.get('turn', {}).get('id')}
except BaseException as error:
    record = {'acknowledged': False, 'delivery': 'uncertain-or-not-sent',
              'error': type(error).__name__ + ': ' + str(error), 'retry': False}
finally:
    if client is not None:
        client.close()
(HERE / 'notification-result.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
