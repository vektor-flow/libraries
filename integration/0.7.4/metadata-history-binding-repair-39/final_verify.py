"""Final read-only input audit and exact own-output source patch reconstruction."""
import json,os,subprocess,sys,tempfile,time
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H))
import adapter as a
start=time.monotonic();s=a.static_contract();p=a.load_pin(s['control_plan'])
assert a.current_head()==a.read(H/'grant.snapshot.json')['source_commit']==s['source_commit']
refs=a.unique(s['pins']+a.controller_inputs(p['inputs'])+p['generated'])
for ref in refs:a.verify(ref)
sys.path.insert(0,str(Path(s['v6_bundle']['controller']['path']).parent))
from storage_paths import pinned,pinned_json
history=a.read(H/'history-audit.json');m=pinned_json(history['manifest']);bad=[]
for ref in m['inputs']:
 try:pinned(ref)
 except Exception as e:bad.append(dict(pin=ref,error=str(e)))
assert len(bad)==1 and bad[0]['pin']==history['mismatches'][0]['pin']
assert a.pin(bad[0]['pin']['path'])['sha256']=='400a56b07d9cb67c7d4d9331a787d13af43fd60dfba56a09481e88b9f66de169'
for ref in a.read(H/'binding32-initial-observation.snapshot.json')['protected_pins']:a.verify(ref)
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_source_patch_',dir=H) as tmp:
 child=subprocess.run(['/usr/bin/patch','--batch','-p1','-i',str(H/'candidate-source-additions.patch')],cwd=tmp,capture_output=True,timeout=5)
 assert child.returncode==0,child.stderr
 names=['adapter.py','root_steps.py','build_packet.py','seal_source.py','generator/prepare.py','generator/payload.py','generator/authenticate.py','generator/authentication.json','generator/SPEC.txt']
 for name in names:assert (Path(tmp)/H.relative_to(a.REPO)/name).read_bytes()==(H/name).read_bytes()
assert not (H.parent/'ROOT-NOT-A-FILE').exists()
assert not subprocess.check_output(['/usr/bin/git','-C',str(a.REPO),'diff','HEAD','--'])
assert not (H/'root-inputs.json').exists() and not (H/'root-packet').exists()
assert not any(H.glob('TEST_ONLY_*'))
for name in ('test-results.json','packet-verification.json','independent-verification.json','relocation-verification.json'):assert a.read(H/name)['passed']
result=dict(passed=True,seconds=time.monotonic()-start,successor_inputs_verified=len(refs),historical_manifest_inputs_verified=914,historical_manifest_inputs=915,expected_unrestored_history_mismatch=bad,actual_join_success_claimed=False,exact_candidate_patch_files=9,shared_tracked_diff_empty=True,own_scratch_removed=True,root_integration_and_final_HEAD_reseal_required=True,operational_packet_exists=False,native_execution=False)
a.save(H/'final-verification.json',result)
print(json.dumps(result))
