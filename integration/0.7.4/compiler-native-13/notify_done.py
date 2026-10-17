"""One authorized DONE delivery using the existing app-server Client. No retry."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import uuid
HERE=Path(__file__).resolve().parent
worker='01a149f1-6e6c-7683-8d76-43acab856af5'
coordinator='01a14893-cb1e-7203-97dd-de3da44dcf31'
message='DONE compiler-native-13 ID01a149f1-6e6c-7683-8d76-43acab856af5 RESULT FAILED_BEFORE_COMPILER_MATERIALIZATION. ONE actual A:compiler-native13-01 charged1GiB/controller1/37.747844s; adapter.py:352 LOCK_SH|LOCK_NB capacity.lock EAGAIN. No native stages/MD/link/ELF/regression credit; no retry. Independent actual custody/service/controller/all descendants join verified; stagejoined,high3,activeRAM0,overlap0. A permanent19864543232,F19821273088,tiny12/48MiB unchanged. All898grant/727plan/229static posthashes and7loaded policies pass. Both own NONOPERATIONAL wrapper corrections documented; no source/guard changes. HANDOFF /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/compiler-native-13/HANDOFF.txt; result /home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/compiler-native-13/result.json. Root owns next action; execution chat stops.'
intent=dict(coordinator=coordinator,message=message,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),attempts=1)
with (HERE/'notification-intent.json').open('x') as stream:json.dump(intent,stream,indent=2)
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
    else:params['clientUserMessageId']=str(uuid.uuid5(uuid.NAMESPACE_URL,'compiler-native-13-DONE:'+worker))
    result=client.rpc(method,params)
    record=dict(method=method,acknowledged=True,response=result,retry=False)
except BaseException as error:
    record=dict(acknowledged=False,delivery='uncertain-or-not-sent',error=type(error).__name__+': '+str(error),retry=False)
finally:
    if client is not None:client.close()
(HERE/'notification-result.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='response'}))
