"""ROOT POST-RESTORATION, read-only. Never run as a temporary source swap."""
import argparse,json,resource,signal,sys
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*2**20,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(50,50))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
signal.signal(signal.SIGALRM,lambda *args:(_ for _ in ()).throw(TimeoutError('55s wall bound')))
signal.alarm(55)
S=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')
sys.dont_write_bytecode=True
sys.path.insert(0,str(S/'storage-direct-v9'))
from storage_paths import pinned,pinned_json
from storage_controller import Controller
statepath=S/'storage-direct-v4/direct-state-v4.json';raw=statepath.read_bytes();data=json.loads(raw)
key,row=max(((k,r) for k,r in data['phases'].items() if r['worker']=='A'),key=lambda item:item[1]['sequence'])
assert key=='A:metadata-native29-01' and row['sequence']==15 and row['stage']=='joined'
assert row['owner']=='01a14a3a-d0d8-7a10-a188-717e31a22e31'
assert row['join']['sha256']=='4a1ed5938463632747f40aba82b60beca7af7de4d676ed7e96ab9b01ea55f002'
manifest=pinned_json(row['manifest'])
for ref in manifest['inputs']:pinned(ref)
grant=pinned_json(row['grant'])
controller=Controller(argparse.Namespace(config_sha256=grant['runtime_config']['sha256'],grant=Path(row['grant']['path']),grant_sha256=row['grant']['sha256'],manifest=Path(row['manifest']['path']),manifest_sha256=row['manifest']['sha256']))
assert controller.verify_join(row,pinned_json(row['join'])) is True
assert statepath.read_bytes()==raw
print(json.dumps(dict(passed=True,manifest_inputs=len(manifest['inputs']),installed_join=True,sequence=15,owner=row['owner'],join=row['join'],state_unchanged=True)))
