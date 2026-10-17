"""One authorized coordinator notification via the existing app-server. No retry."""
import datetime
import importlib.util
import json
from pathlib import Path
import uuid

HERE = Path(__file__).resolve().parent
WORKER = '01a14935-046e-71e3-935e-beca885ffe3c'
COORDINATOR = '01a14893-cb1e-7203-97dd-de3da44dcf31'
MESSAGE = ('DONE ' + WORKER + ' | Two-file UTF16BE/ActualText source patch; '
           '5 host oracle tests pass for 41 exact assertions; native unexecuted; '
           'production pins unchanged, no integration without provenance | '
           + str(HERE / 'HANDOFF.txt'))
intent = {'coordinator': COORDINATOR, 'message': MESSAGE, 'attempts': 1,
          'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
with (HERE / 'notification-intent.json').open('x') as stream:
    json.dump(intent, stream, indent=2)
    stream.write('\n')
client = None
try:
    source = Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/controller.py')
    spec = importlib.util.spec_from_file_location('existing_app_protocol', source)
    protocol = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protocol)
    client = protocol.client()
    client.sock.settimeout(20)
    thread = client.rpc('thread/read', {'threadId': COORDINATOR, 'includeTurns': True})['thread']
    active = protocol.active(thread)
    method = 'turn/steer' if active else 'turn/start'
    params = {'threadId': COORDINATOR, 'input': [{'type': 'text', 'text': MESSAGE}]}
    if active:
        params['expectedTurnId'] = active['id']
    else:
        params['clientUserMessageId'] = str(uuid.uuid5(uuid.NAMESPACE_URL, 'pdf-selection-encoding-03-done:' + WORKER))
    response = client.rpc(method, params)
    record = {'method': method, 'acknowledged': True, 'response': response, 'retry': False}
except BaseException as error:
    record = {'acknowledged': False, 'delivery': 'uncertain-or-not-sent',
              'error': type(error).__name__ + ': ' + str(error), 'retry': False}
finally:
    if client is not None:
        client.close()
(HERE / 'notification-result.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({key: value for key, value in record.items() if key != 'response'}))
