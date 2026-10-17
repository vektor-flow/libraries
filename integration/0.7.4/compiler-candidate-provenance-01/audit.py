from pathlib import Path
import json, hashlib, re

ROOT=Path('/home/viktor/Projects/Vektor Flow')
REPO=ROOT/'.worktrees/gpu-math-20261014-libraries'
OUT=REPO/'integration/0.7.4/compiler-candidate-provenance-01'
CO=ROOT/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers'
CACHE=Path('/home/viktor/.cache/vkf-s0-runtimes-20261012')
E=CACHE/'Integrator/independent-worker-E'
D=CACHE/'Proof/tests/independent-worker-D'
A=CACHE/'Frontend/experiments/independent-worker-A'
C=CACHE/'Native/reports/native3-integer-power01/independent-worker-C'
pins={}
def read(p):
 p=Path(p);raw=p.read_bytes();pins[str(p)]={'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 return json.loads(raw) if p.suffix=='.json' else raw.decode()
def save(name,value):
 (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

for p in [CO/'storage20gb/compiler-candidate-provenance-01-visible-chat-grant.json',*[REPO/'integration/0.7.4'/n for n in ['HANDOVER.txt','COORDINATOR-STATUS.txt','source-imports.json','toolchain-pins.json']],A/'iteration333/handoff.txt',A/'iteration246-static-nominal-resume01/handoff.txt',C/'iteration256-seal01/handoff.txt']:
 read(p)
intakes={}
for n in ['A333-root-intake-refill-20261017.json','E329-intake-constructor-blocked-refill-20261017.json','E330-intake-closure-stop-refill-20261017.json','A252-B330-D288-intake-refill-20261017.json']:
 intakes[n]=read(CO/'storage20gb'/n)
index=[];lineage=[]
for p in sorted(E.glob('handoff-iteration-*.json'), key=lambda p:int(re.search(r'iteration-(\d+)',p.name)[1])):
 d=read(p);n=d.get('iteration');index.append({**pins[str(p)],'iteration':n,'status':d.get('status'),'assignment_complete':d.get('assignment_complete'),'integration_ready':d.get('integration_ready'),'internal_passed_issue_keys':d.get('internal_passed_issue_keys'),'production_compiler_changed':d.get('production_compiler_changed'),'summary':d.get('summary')})
 if n in list(range(214,231))+[273,274,275,283,285,286,288,289,290,329,330]:
  lineage.append({'handoff':pins[str(p)],'facts':{k:d[k] for k in ['iteration','source_thread','status','assignment_complete','integration_ready','summary','limitations','internal_passed_issue_keys','input_runtime_pins','ready_packet','owned_jobs_joined'] if k in d}})
grants=[]
for n in [218,226,227,229,230,288]:
 p=CO/f'worker-e-iteration-{n}-20gb-grant.json';d=read(p)
 grants.append({'pin':pins[str(p)],'utc':d.get('utc'),'owner':d.get('owner'),'iteration':n,'scope':d['profile'].get('edit_scope'),'next_work':d['profile'].get('next_work')})
rejected=[]
for n in [226,227,229]:
 p=E/f'ready-packet-iteration{n}.json';d=read(p)
 rejected.append({'pin':pins[str(p)],'facts':{k:d[k] for k in ['integration_ready','assignment_complete','candidate_profile','candidate_profiles','owned_jobs_joined','feedback','services'] if k in d}})
ready=read(D/'ready-packet-iteration288.json')
profile=read(D/'iteration288-evidence/ready-delta-profile.json')
parent=read(profile['parent']['path'])
base=read(profile['base_profile']['path'])
relevant=[]
for obj in base['objects']:
 for dep in obj.get('dependencies',[]):
  if any(t in dep.get('effective','') for t in ['function_lowering.cpp','recursive_result_constraints','record_construction.cpp']):
   relevant.append({'index':obj.get('index'),'dependency':dep})
# Some profiles store dependency fields under different nesting. Retain exact matching metadata only.
def walk(v):
 if isinstance(v,dict):
  if 'sha256' in v and any(t in str(v.get('effective','')) for t in ['function_lowering.cpp','recursive_result_constraints','record_construction.cpp']):
   if v not in [x.get('dependency') for x in relevant]:relevant.append({'dependency':v})
  for x in v.values():walk(x)
 elif isinstance(v,list):
  for x in v:walk(x)
walk(base)
checks=[]
for label,record in [('D288 ready profile',ready['profile']),('D288 parent',profile['parent']),('D288 base',profile['base_profile']),('D285 parent',parent['parent']),('A333 handoff',intakes['A333-root-intake-refill-20261017.json']['handoff'])]:
 actual=pins.get(record['path'])
 checks.append({'label':label,'expected':record,'actual':actual,'matches':bool(actual and actual['sha256']==record['sha256'])})
for n,key in [(329,'E329-intake-constructor-blocked-refill-20261017.json'),(330,'E330-intake-closure-stop-refill-20261017.json')]:
 actual=pins[str(E/f'handoff-iteration-{n}.json')]
 checks.append({'label':f'E{n} handoff intake','actual':actual,'expected_sha256':intakes[key]['handoff_sha256'],'matches':actual['sha256']==intakes[key]['handoff_sha256']})
for item in lineage:
 d=item['facts'];ip=d.get('input_runtime_pins',{});g=ip.get('grant') if isinstance(ip,dict) else None
 if g and g['path'] in pins:checks.append({'label':f"E{d['iteration']} handoff grant",'expected':g,'actual':pins[g['path']],'matches':g['sha256']==pins[g['path']]['sha256']})
comparison={'compiler_pin':ready['compiler'],'identity':ready['identity'],'ready_packet':pins[str(D/'ready-packet-iteration288.json')],'D288_profile':pins[str(D/'iteration288-evidence/ready-delta-profile.json')],'D285_profile':pins[profile['parent']['path']],'F303_base_profile':pins[profile['base_profile']['path']],'D288_replaced_indices':[x['index'] for x in profile['replacements']],'D285_replaced_indices':[x['index'] for x in parent['replacements']],'provenance_note':profile['provenance_note'],'relevant_base_dependencies':relevant,'candidate_sources_opened':False,'binary_or_object_hashes_recomputed':False,'interpretation':'D288 inherits F303 function-lowering revision 1c8bc780... through D285; D288 changes 39/42/90, D285 preserves the function-lowering entry. Metadata does not import E226/E227/E229 convergence revisions. Absence of these rejected revisions is not missing accepted work. Source-imports records application generation A343-F349-r1 and host E382, not an additional compiler candidate.'}
save('e-handoff-index.json',index)
save('lineage.json',{'grants':grants,'handoffs':lineage,'rejected_candidate_metadata':rejected,'intakes':intakes})
save('d288-coverage.json',comparison)
save('pin-checks.json',checks)
save('evidence-pins.json',list(pins.values()))
save('disposition.json',{'result':'NO_ACCEPTED_CANDIDATE','candidate':None,'accepted_missing_from_D288':False,'historical_E_ownership_established_at':218,'later_authenticated_disjoint_compiler_continuation_found':False,'owned_jobs_launched':0,'owned_jobs_joined':True,'original419_credited':293,'native47_passed':18,'compiler_blocker':'compose/from_leaves remains','scope':'Metadata provenance audit only; no compiler bodies, diagnostic artifacts, builds, runtime or operational-state changes.'})
print(json.dumps({'handoffs_indexed':len(index),'pins':len(pins),'checks':len(checks),'checks_all_match':all(x['matches'] for x in checks),'base_dependencies':relevant,'D285_indices':comparison['D285_replaced_indices'],'rejected_ready_flags':[(x['facts'].get('integration_ready'),x['facts'].get('assignment_complete')) for x in rejected]},indent=2))
