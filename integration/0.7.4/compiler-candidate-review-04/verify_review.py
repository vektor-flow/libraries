"""Host-only artifact authentication and patch reconstruction; no C++ execution."""
import hashlib, json, re, time
from pathlib import Path
here = Path(__file__).resolve().parent
repair = here.parent / 'compiler-renderer-repair-02'
start = time.monotonic()
pins = []
def pin(path, expected=None):
    path=Path(path); data=path.read_bytes(); digest=hashlib.sha256(data).hexdigest()
    if expected is not None: assert digest == expected, str(path)
    pins.append(dict(path=str(path.resolve()),sha256=digest,bytes=len(data)))
source=json.loads((repair/'source-pins.json').read_text())
for index in (51,53,56):
    x=next(x for x in source if x.get('index')==index)
    pin(x['effective'],x['sha256'])
x=json.loads((here/'relevant-unit54-pin.json').read_text()); pin(x['effective'],x['sha256'])
d=json.loads((repair/'build-input-unit53.json').read_text())
x=next(x for x in d['dependencies'] if x['nominal'].endswith('/vkf_value_layout.hpp'))
pin(x['effective'],x['sha256'])
pin(repair/'baseline/layouts_1.cpp','6c9f9cf5d2b60c426f88402c0ae32c294191c26880614e71907354613e27c5bd')
pin(repair/'candidate/layouts_1.cpp','8ff80f95d154585cc0966cfb2b9b06ae441cb357017eb524c8b750616ae6161d')
for name in ('HANDOFF.txt','CAUSE.txt','compiler.patch','regression_layouts.cpp','test_reasoning.py','real-ir-evidence.json'):
    pin(repair/name)
old=(repair/'regression_layouts.cpp').read_text().splitlines(True)
patch=(here/'regression-supplement.patch').read_text().splitlines(True)
result=[]; cursor=0
for line in patch[2:]:
    if line.startswith('@@'):
        m=re.match(r'@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@',line); assert m
        target=int(m[1])-1; assert target>=cursor
        result.extend(old[cursor:target]); cursor=target
    elif line.startswith(' '):
        assert old[cursor]==line[1:]; result.append(old[cursor]); cursor+=1
    elif line.startswith('-'):
        assert old[cursor]==line[1:]; cursor+=1
    elif line.startswith('+'): result.append(line[1:])
    else: raise AssertionError(line)
result.extend(old[cursor:])
assert ''.join(result)==(here/'regression_layouts_supplemented.cpp').read_text()
for name in ('regression-supplement.patch','regression_layouts_supplemented.cpp','make_supplement.py','verify_review.py','FINDINGS.txt'):
    pin(here/name)
for name in ('compiler-candidate-review-04-visible-chat-grant.json','a333-scope-reopened-20261017.json'):
    pin(Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')/name)
(here/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
report=dict(result='PASS host artifact checks only',seconds=time.monotonic()-start,
    pins=len(pins),patch_reconstruction='exact in memory; source untouched',
    native_test='NOT RUN',reasoning_model='not rerun; no duplicate semantic model',
    native_record_cases_prepared=27,processes='synchronous host Python only; joined')
(here/'tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
