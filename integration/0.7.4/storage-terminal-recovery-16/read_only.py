from pathlib import Path
import sys,json,time,hashlib
O=Path(__file__).resolve().parent
pins=json.loads((O/'input-pins.json').read_text());I=Path(pins[0]['path']).parent
sys.path[:0]=[str(O/'candidate'),str(I)]
import terminal_recovery as t
from storage_admission import Ledger
before={p['path']:hashlib.sha256(Path(p['path']).read_bytes()).hexdigest() for p in pins}
start=time.monotonic();baseline,r,_,_=t.live14_sources();t.live14_current_owner()
l=Ledger(t.LIVE14_STATE,t.LIVE14_LOCK,recovery_pin=t.LIVE14_ANCHORS['legacy_authority'])
# Read-only transaction: no save or synthetic authority. Existing lock only.
with l.transaction() as data:
 assert t.exact(data,baseline)
 proof=t.observe_live14(r);t.validate_live14_proof(r,proof)
 assert sum(x['ram_bytes'] for x in l.active_rows(data))==3*2**30
 assert l.owner(data,'F')==r['owner']
 assert l.owner(data,'A')==r['owner']
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
(O/'readonly-observation.json').write_text(json.dumps(dict(diagnostic_only=True,operational_mutation=False,ram_released=False,seconds=time.monotonic()-start,proof=proof),indent=2)+'\n')
print('read-only exact sources/state/owners/custody PASS; 3GiB retained')
