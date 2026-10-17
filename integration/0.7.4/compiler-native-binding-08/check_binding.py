#!/usr/bin/env python3
"""Bounded source/materialization checks. No compiler, payload, fake receipt or native run.

All writes stay below this directory. Invoke with a fresh --out child directory.
The copied package bytes remain unchanged; only imported repository-location
constants are set to the real read-only source repository before loading prepare.
"""
import argparse
import copy
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True
resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_FSIZE, (32*1024*1024, 32*1024*1024))
START = time.monotonic()
OWN = Path(__file__).resolve().parent
REPO = OWN.parents[2]
PEER = OWN.parent/'compiler-build-preparation-03'
REPAIR = OWN.parent/'compiler-record-projection-repair-05'
REVIEW = OWN.parent/'compiler-package-review-06'
EXPECTED_HEAD = 'd8373abc43c3c64147cd99f58c84669056c3ccb7'
CANDIDATE = '226bb513fec0c2e1d9443fd9ac61d6ab863e9a3a136ab2238cf7d9346130307f'
REGRESSION = '688a991c0821951d86c1b87330d2def7af6cd0423488c5350eb2005e48a81c86'
MARKER = 'cross-ABI child was preserved'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(262144), b''): h.update(b)
    return h.hexdigest()

def pin(path): return dict(path=str(path), sha256=sha(path), bytes=Path(path).stat().st_size)
def read(path): return json.loads(Path(path).read_text())
def save(path, value):
    assert path.resolve().is_relative_to(OWN)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module
    spec.loader.exec_module(module); return module

parser=argparse.ArgumentParser();parser.add_argument('--out',required=True,type=Path)
args=parser.parse_args();out=args.out.resolve()
assert out.is_relative_to(OWN) and out!=OWN and not out.exists()
out.mkdir(parents=True)
inputs={}
def record(path):
    p=pin(path);inputs[p['path']]=p;return p

grant=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/compiler-native-binding-08-visible-chat-grant.json')
for p in [grant, REPAIR/'root-candidate-review.json', REPAIR/'regression_layouts.cpp',
          REPAIR/'baseline/layouts_1.cpp', REPAIR/'candidate/layouts_1.cpp',
          OWN.parent/'compiler-record-review-07/HANDOFF.txt', PEER/'root-integration.json',
          PEER/'estimates.json', REVIEW/'orchestration.patch', OWN/'corrected-review.json']:
    record(p)
assert read(grant)['owner_thread']=='01a14968-7498-7d73-a430-62c8f9d81131'
assert sha(REPAIR/'candidate/layouts_1.cpp')==CANDIDATE
assert sha(REPAIR/'regression_layouts.cpp')==REGRESSION
assert sha(REPAIR/'baseline/layouts_1.cpp')=='6c9f9cf5d2b60c426f88402c0ae32c294191c26880614e71907354613e27c5bd'
original=read(REPAIR/'root-candidate-review.json');corrected=read(OWN/'corrected-review.json')
expected=copy.deepcopy(original);expected['baseline_failure_marker']=MARKER
assert corrected==expected, 'binding must change only the baseline marker'
source=(REPAIR/'regression_layouts.cpp').read_text()
main=source[source.index('int main()'):]
order=['repair05_record_controls();','repair05_canonical_and_alias_controls();',
       'review04_negative_controls();','ordinary call narrowed a counted metadata field',
       'review04_record_projection_cases();','ordinary counted metadata layout regressions passed']
assert [main.index(x) for x in order]==sorted(main.index(x) for x in order)
assert source.index(MARKER)<source.index('int main()')

package=out/'package-copy';package.mkdir()
integrated={p['path']:p['sha256'] for p in read(PEER/'root-integration.json')['files']}
for name in ['authenticate.py','authentication.json','prepare.py','payload.py','SPEC.txt','test_preparation.py']:
    record(PEER/name);dest=package/name;dest.write_bytes((PEER/name).read_bytes())
    assert sha(dest)==sha(PEER/name)
    if name in integrated:
        assert sha(dest)==integrated[name]==sha(REVIEW/'candidate'/name)
        record(REVIEW/'candidate'/name)
auth=load('authenticate',package/'authenticate.py')
auth.REPO=REPO;auth.REPAIR=OWN.parent/'compiler-renderer-repair-02'
prep=load('prepare',package/'prepare.py');payload=load('payload',package/'payload.py')
# Any child from the imported package is restricted to bounded, synchronous Git HEAD reads.
real_check_output=subprocess.check_output;git_children=[]
def head_child(argv,**kw):
    assert argv==['/usr/bin/git','-C',str(REPO),'rev-parse','HEAD'], argv
    result=real_check_output(argv,timeout=5,**kw)
    git_children.append(dict(argv=argv,exit=0,joined=True));return result
prep.subprocess.check_output=head_child
head=prep.current_head();assert head==EXPECTED_HEAD,'shared HEAD advanced; review and refresh this check'
authentication=auth.read(package/'authentication.json');prep.freeze_check(authentication)
for p in authentication['inputs']: inputs[p['path']]=p
r=prep.review(OWN/'corrected-review.json');assert r['executable'] is True
plan=prep.build_plan(out/'compiler-preview',r,authentication)
assert plan['application_head_at_preparation']==head
assert (out/'compiler-preview/sources/regression_layouts.cpp').read_bytes()==(REPAIR/'regression_layouts.cpp').read_bytes()
assert (out/'compiler-preview/sources/layouts_1.cpp').read_bytes()==(REPAIR/'candidate/layouts_1.cpp').read_bytes()
assert plan['identity']==hashlib.sha256((plan['parent_identity']+CANDIDATE+prep.TAG).encode()).hexdigest()
assert plan['identity']!=plan['parent_identity']
stages={s['name']:s for s in plan['stages']}
assert list(stages)==['compile-53','compile-90','link-compiler','compile-regression',
                     'link-regression-baseline','run-regression-baseline','link-regression-candidate','run-regression-candidate']
assert [len(stages['compile-'+str(i)]['expected']) for i in [53,90]]==[302,70]
header=out/'compiler-preview/sources/vkf_compiler_build_identity.generated.hpp'
assert plan['identity'] in header.read_text()
identity_aliases={n:v for n,v in stages['compile-90']['mapping'].items() if Path(n).name==header.name}
assert identity_aliases and set(identity_aliases.values())=={str(header)}
old=auth.read(auth.REPAIR/'build-prerequisites.json')['ordered_link_argv']
providers=lambda argv:[x for x in argv if x.endswith(('.o','.a'))]
original_providers=providers(old)
changed={}
for name,positions in [('link-compiler',[54,91]),('link-regression-baseline',[0]),('link-regression-candidate',[0,54,91])]:
    new=providers(stages[name]['argv']);assert len(new)==len(original_providers)==240
    changed[name]=[i for i,(a,b) in enumerate(zip(original_providers,new)) if a!=b]
    assert changed[name]==positions
for s in plan['stages']:
    for p in s.get('outputs',[])+([s['md']] if 'md' in s else []):
        assert Path(p).resolve().is_relative_to(out) and not Path(p).exists()
baseline=stages['run-regression-baseline'];assert baseline['stderr_contains']==MARKER
# Test oracle comparison only, with explicitly synthetic strings; no executable.
payload.check_result(baseline,1,'',MARKER)
for code,stderr in [(0,MARKER),(1,original['baseline_failure_marker']),(1,'unrelated failure')]:
    try:payload.check_result(baseline,code,'',stderr)
    except ValueError:pass
    else:raise AssertionError('incorrect negative oracle accepted')
candidate=stages['run-regression-candidate']
payload.check_result(candidate,0,corrected['candidate_success_stdout'],'')

# Resolve actual header aliases, not literal-path differences. No preprocessor.
expected_dependencies={str(Path(d['effective']).resolve()):d for d in stages['compile-regression']['expected']}
unit53={str(Path(d['effective']).resolve()):d for d in plan['units']['53']['dependencies']}
headers=[]
names=['algorithm','stdexcept','iostream','bits/requires_hosted.h','ostream','istream','bits/istream.tcc']
paths=[Path('/usr/include/c++/15')/x for x in names]
paths += [Path(d['effective']) for d in plan['units']['53']['dependencies'] if d['nominal'].endswith(('bits/c++config.h','compiler/native/vkf_value_layout.hpp'))]
for path in paths:
    key=str(path.resolve());d=expected_dependencies[key]
    assert sha(path)==d['sha256'];record(path)
    headers.append(dict(path=str(path),canonical=key,sha256=sha(path),in_original53=key in unit53))
assert re.findall(r'^#include (.+)$',source,re.M)==['"compiler/native/vkf_value_layout.hpp"','<algorithm>','<iostream>','<stdexcept>']
save(out/'dependency-check.json',dict(headers=headers,regression_allowlist=len(stages['compile-regression']['expected']),
     includes=re.findall(r'^#include (.+)$',source,re.M),actual_md_observed=False,
     note='Direct headers and iostream direct include paths are authenticated. Existing unit53 supplies stream transitive paths. Actual conditional/preprocessor MD still required; no expanded allowlist.'))

# Current source closures using the corrected package's pure closure/entry functions.
# No compiler receipt is invented and tests_plan/payload.execute are not called.
closures={}
def closure_case(selection,name,roots,extra_pins=()):
    texts,pins=prep.closure(roots)
    for p in extra_pins:pins[p['path']]=p
    for p in pins.values():record(p['path'])
    closures.setdefault(selection,[]).append(dict(name=name,head=head,root_text_sha256={n:hashlib.sha256(t.encode()).hexdigest() for n,t in roots.items()},
        modules=sorted(texts),assertions={n:t.count('?!') for n,t in texts.items()},inputs=list(pins.values())))
for folder in [auth.D,auth.CACHE/'Proof/tests/independent-worker-D/iteration288-ownership02']:
    record(folder/'plan.json')
    for c in read(folder/'plan.json')['cases']:
        record(c['source']);closure_case('d288',c['name'],{c['name']:Path(c['source']).read_text()})
for selection,glob,name in [('metadata','metadata_actual_lengths.vkf','metadata'),('a345','*small*','A345'),('a347','*real*','A347')]:
    p=next((auth.REPAIR/'regressions').glob(glob));record(p);closure_case(selection,name,{name:p.read_text()})
f=auth.CACHE/'Integrator/independent-worker-F/iteration364-scene-ten01'
record(f/'execution-plan.json');record(f/'prepare_group.py')
historical=read(f/'execution-plan.json')['suites'][0];dispatcher=Path(historical['derivative']['path']);record(dispatcher)
roots={'02_scene_provider':dispatcher.read_text()};fpins=[];relocate=load('closure_relocate',f/'prepare_group.py')
for run in historical['runs'][:-1]:
    name=run['id'];p=REPO/'examples/gpu-math/native-vkf'/(name+'.vkf');fpins.append(record(p))
    wrapped=prep.entry(p.read_text());relocated,calls=relocate.prepare(wrapped)
    assert relocated.count('?!')==wrapped.count('?!');roots[name]=relocated
assert len(historical['runs'])==11
closure_case('f364','F364',roots,fpins)
p=REPO/'examples/gpu-math/native-vkf/native_document_cli.vkf'
closure_case('full-app','full-app',{'native_document_cli':p.read_text()},[record(p)])
save(out/'current-closures.json',dict(preview_only=True,no_compiler_receipt_created=True,regenerate_at_each_future_attempt=True,selections=closures))
counts={s:dict(cases=len(cases),application_input_paths=len({p['path'] for c in cases for p in c['inputs']}),
              assertions=sum(sum(c['assertions'].values()) for c in cases)) for s,cases in closures.items()}
save(out/'input-pins.json',list(inputs.values()))
for p in inputs.values():assert sha(p['path'])==p['sha256'],p['path']
assert prep.current_head()==head
sizes=[p.stat().st_size for p in out.rglob('*') if p.is_file()]
assert sum(sizes)<128*1024*1024
status=Path('/proc/self/status').read_text()
result=dict(status='PASS',head=head,native_executed=False,compiler_or_linker_invoked=False,
    grants_created=False,environment_qualified=False,independent_source_review_repeated=False,
    baseline_oracle_source_inferred_not_executed=MARKER,identity=plan['identity'],parent_identity=plan['parent_identity'],
    identity_header=pin(header),identity90_aliases=identity_aliases,provider_changes_zero_based=changed,
    package_copy_byte_identical=True,regression_byte_identical=True,regression_require_call_sites=source.count('require(')-1,
    authenticated_inputs=len(authentication['inputs']),input_pins=len(inputs),closure_counts=counts,
    retained_preview_bytes_before_result=sum(sizes),seconds=time.monotonic()-START,
    process_memory_kib={k:int(re.search(r'^'+k+r':\s+(\d+)',status,re.M)[1]) for k in ['VmHWM','VmPeak']},
    rusage_maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    bounds=dict(address_space_bytes=512*1024*1024,cpu_seconds=30,outer_timeout_seconds=60,total_output_check_bytes=128*1024*1024),
    synchronous_git_children=git_children,all_children_joined=True)
save(out/'checks.json',result)
print(json.dumps(result,indent=2))
