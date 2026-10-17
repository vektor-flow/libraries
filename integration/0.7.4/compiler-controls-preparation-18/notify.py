"""Deliver one current native17 message via established native13 app-server protocol."""
import datetime,importlib.util,json,sys,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
STORAGE=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
auth=json.loads((STORAGE/'compiler-controls-preparation-18-visible-chat-grant.json').read_text())
kind=sys.argv[1];message=(HERE/(kind+'-message.txt')).read_text()
assert 'compiler-controls-preparation-18' in message and auth['owner_thread'] in message
assert (kind=='done') == message.startswith('DONE ')
intent=dict(coordinator=auth['coordinator'],worker=auth['owner_thread'],message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/(kind+'-notification-intent.json')).open('x') as f:json.dump(intent,f,indent=2)
client=None
try:
 source=STORAGE.parents[1]/'controller.py'
 spec=importlib.util.spec_from_file_location('existing_app_protocol',source)
 protocol=importlib.util.module_from_spec(spec);spec.loader.exec_module(protocol)
 client=protocol.client();client.sock.settimeout(20)
 thread=client.rpc('thread/read',dict(threadId=auth['coordinator'],includeTurns=True))['thread']
 active=protocol.active(thread);method='turn/steer' if active else 'turn/start'
 params=dict(threadId=auth['coordinator'],input=[dict(type='text',text=message)])
 if active:params['expectedTurnId']=active['id']
 else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-controls-preparation-18-'+kind+':'+auth['owner_thread']))
 response=client.rpc(method,params)
 record=dict(method=method,acknowledged=True,response=response,retry=False)
except BaseException as error:
 record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
 if client is not None:client.close()
with (HERE/(kind+'-notification-result.json')).open('x') as f:json.dump(record,f,indent=2)
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
