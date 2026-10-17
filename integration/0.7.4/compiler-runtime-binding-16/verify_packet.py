"""TEST_ONLY host checks. No positive admission fixture, native or operational call."""
import copy
import difflib
import json
from pathlib import Path
import resource
import sys
import tempfile
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import adapter as a

def main():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(30,30))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    start=time.monotonic(); checks=[]
    seal=a.static_contract(); plan=a.read(HERE/'staging/plan.json')
    assert a.current_head()==seal['source_commit']==plan['application_head_at_preparation']
    checks.append('exact current HEAD, 229 static pins and accepted adapter bytes')
    old=a.read(HERE.parent/'compiler-native-binding-08/root-check01/compiler-preview/plan.json')
    rebased,assets=a.relocate(old,plan['out'])
    rebased['application_head_at_preparation']=seal['source_commit']
    assert rebased==plan,'fresh staging differs beyond output relocation and current HEAD'
    for path,data in assets: assert Path(path).read_bytes()==data
    checks.append('complete fresh plan equals accepted08 plan after exact relocation and HEAD refresh')
    review=a.load_pin(seal['review']);a.check_plan(plan,seal['source_commit'],review)
    assert review['candidate']['sha256']=='226bb513fec0c2e1d9443fd9ac61d6ab863e9a3a136ab2238cf7d9346130307f'
    assert a.pin(HERE/'staging/sources/regression_layouts.cpp')['sha256']==review['regression']['sha256']=='688a991c0821951d86c1b87330d2def7af6cd0423488c5350eb2005e48a81c86'
    checks.append('corrected core53 and full unchanged regression including27 cases/negatives')
    for i in (2,4,6): assert len([p for p in plan['stages'][i]['argv'] if p.endswith(('.o','.a'))])==240
    checks.append('240 ordered providers in all3 links; full-plan equality preserves flags/order')
    with tempfile.TemporaryDirectory(prefix='TEST_ONLY_materialization_',dir=HERE) as tmp:
        target=Path(tmp)/'compiler';moved,assets=a.relocate(plan,target)
        target.mkdir()
        for name in ('tmp','cache','home','logs','objects','sources'):(target/name).mkdir()
        for path,data in assets:
            assert Path(path).parent.is_dir()
            Path(path).write_bytes(data)
        for p in moved['generated']:a.verify(p)
        for stage in moved['stages']:
            paths=stage.get('outputs',[])+([stage['md']] if 'md' in stage else [])
            for path in paths:assert Path(path).parent.is_dir() and Path(path).is_relative_to(target)
        back,_=a.relocate(moved,plan['out']);assert back==plan
    checks.append('TEST_ONLY materialization and full reverse relocation; no authority fixtures')
    target=HERE/'TEST_ONLY_must_not_assemble'
    assert not target.exists()
    try:a.assemble(HERE/'staging/plan.json',HERE/'root-inputs.REQUIRED.json',target)
    except ValueError as e:assert str(e)=='actual root execution decision required'
    else:raise AssertionError('null root decision accepted')
    assert not target.exists()
    checks.append('null genuine-root-input template refused before any assembly output')
    # Verify exact independently reviewed repaired adapter, without changing historical packet.
    original=HERE.parent/'compiler-lock-repair-14/adapter.py'
    diff=''.join(difflib.unified_diff(original.read_text().splitlines(True),
        (HERE/'adapter.py').read_text().splitlines(True),fromfile=str(original),tofile=str(HERE/'adapter.py')))
    assert not diff;(HERE/'adapter.patch').write_text(diff)
    assert a.current_head()==seal['source_commit']
    result=dict(passed=True,checks=checks,seconds=time.monotonic()-start,native_execution=False,
                admission=False,operational_mutations=0,TEST_ONLY=True,
                memory=[x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith(('VmHWM:','VmPeak:'))])
    (HERE/'verification.json').write_bytes(a.encoded(result));print(json.dumps(result))

if __name__=='__main__':main()
