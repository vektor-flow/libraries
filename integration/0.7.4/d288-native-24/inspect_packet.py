import pathlib,sys,json,time
OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
from preflight import a,PACKET,save
start=time.monotonic()
s=a.static_contract();r=a.read(PACKET/'root-inputs.json');c=a.read(PACKET/'root-packet/contract.json')
g=a.read(PACKET/'root-packet/grant.candidate.json');m=a.read(PACKET/'root-packet/manifest.candidate.json')
p=a.read(PACKET/'staging/d288/plan.json');actual=a.load_pin(c['plan'])
expected,assets=a.relocate(p,pathlib.Path(c['attempt_root'])/'d288')
assert actual==expected and c['request']==r and len(assets)==len(c['assets'])
for (dest,b),ref in zip(assets,c['assets']):
 assert dest==ref['target'] and a.raw(ref['source']['path'])==b
 a.verify(ref['source'])
for ref in p['inputs']+p['generated']+g['inputs']:a.verify(ref)
a.check_plan(actual,r['source_commit'],a.load_pin(s['review']))
assert all(m[k]==g[k] for k in a.MATCH) and m['grant']['sha256']==a.pin(PACKET/'root-packet/grant.candidate.json')['sha256']
assert a.current_head()==s['source_commit']==r['source_commit']
root=pathlib.Path(c['attempt_root']);assert not root.exists() and not root.is_symlink()
links=[dict(stage=x['name'],argv=x['argv'],expected=x.get('expected')) for x in actual['stages'] if x['name'].startswith('link-')]
# Compare original frozen D288 stages after only authorized relocation/cwd/vgdb changes.
original=a.read(OUT.parent/'compiler-controls-preparation-18/staging/d288/plan.json')
prior,prior_assets=a.relocate(original,pathlib.Path(actual['out']))
assert actual['cases']==prior['cases'] and len(actual['cases'])==10 and len(actual['stages'])==20
for old,new in zip(prior['stages'],actual['stages']):
 if old['name'].endswith('-compile'):
  old['cwd']=str(pathlib.Path(actual['out'])/'home')
  assert new['timeout']==180 and all(pathlib.Path(new['argv'][i]).is_absolute() for i in (0,1,3))
 else:
  old['argv'].insert(1,'--vgdb=no')
  assert new['timeout']==60 and new['valgrind'] is True
 assert old==new, new['name']
assert prior_assets==assets, 'original generated input bytes changed beyond relocation'
for item in actual['symlinks']:
 assert dict(path=str(pathlib.Path(item['target']).resolve()),sha256=item['sha256']) in a.controller_inputs(actual['inputs'])
 assert pathlib.Path(item['path']).is_relative_to(pathlib.Path(actual['out'])/'home')
 assert a.pin(item['target'])['sha256']==item['sha256']
assert len(actual['symlinks'])==30
assert a.read(PACKET/'test-results.json')['passed'] and a.read(PACKET/'test-results.json')['tests']==13
result=dict(exact_relocation=True,assets_exact=True,original_oracles_preserved=True,three_required_fixes_verified=True,stdlib_sources=30,attempt_absent=True,inputs_verified=len(p['inputs']),static_pins=len(s['pins']),grant_inputs=len(g['inputs']),stages=[dict(name=x['name'],timeout=x['timeout'],oracle={k:x[k] for k in ('expected_exit','stdout','stderr_contains') if k in x}) for x in actual['stages']],link_order=links,grant=a.pin(PACKET/'root-packet/grant.candidate.json'),manifest=a.pin(PACKET/'root-packet/manifest.candidate.json'),seconds=time.monotonic()-start)
save('assembled-inspection.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('link_order','grant','manifest')}))
