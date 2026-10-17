"""Independent integrated-source, exact oracle, full plan, succession and guard checks."""
import ast,copy,difflib,hashlib,json,resource,subprocess,sys,tempfile,time
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import adapter as a
sys.path.insert(0,str(a.PACKAGE));import payload,prepare as p
start=time.monotonic();checks=[];children=[]
def check(value,label):
 assert value,label
 checks.append(label)
def host(argv):
 c=subprocess.run(argv,capture_output=True,timeout=8,check=True);return c.stdout
seal=a.static_contract();plan=a.load_pin(seal['control_plan']);grant=a.read(H/'grant.snapshot.json')
check(grant['source_commit']==a.current_head()==seal['source_commit'],'grant HEAD and fresh seal exact')
old=host(['/usr/bin/git','-C',str(a.REPO),'show',grant['source_commit']+'^:integration/0.7.4/compiler-build-preparation-03/prepare.py'])
current=(a.PACKAGE/'prepare.py').read_bytes();reviewed=H.parent/'metadata-entry-repair-31'
check(current==(reviewed/'prepare.py').read_bytes(),'integrated generator exactly reviewed repair31 candidate')
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_patch_',dir=H) as tmp:
 f=Path(tmp)/'prepare.py';f.write_bytes(old)
 host(['/usr/bin/patch','--batch',str(f),str(reviewed/'prepare.py.patch')])
 check(f.read_bytes()==current,'repair31 patch independently reconstructs integrated HEAD generator')
 changed=host(['/usr/bin/git','-C',str(a.REPO),'diff-tree','--no-commit-id','--name-only','-r',grant['source_commit']]).decode().splitlines()
 check(changed==['integration/0.7.4/compiler-build-preparation-03/prepare.py','integration/0.7.4/metadata-entry-repair-31/root-adoption.json'],'integration commit touches only generator and root adoption evidence')
# Reverse the exact reviewed block to prove every other byte unchanged.
before="        p=REPAIR/'regressions/metadata_actual_lengths.vkf';case('metadata',{ 'metadata':p.read_text()},[dict(expected_exit=0,stdout='true\\n')])\n"
after="        p=REPAIR/'regressions/metadata_actual_lengths.vkf'\n        text=p.read_text()\n        require(text.endswith('\\ntrue\\n'),'metadata final expression changed; review required')\n        # Bare top-level values are discarded; emit the unchanged success value.\n        case('metadata',{'metadata':text[:-5]+'::true\\n'},[dict(expected_exit=0,stdout='true\\n')])\n"
check(current.decode().count(after)==1 and current.decode().replace(after,before).encode()==old,'only metadata branch changes; every other generator byte preserved')
raw=Path(plan['out'])/'metadata/raw/metadata.vkf';original=(p.REPAIR/'regressions/metadata_actual_lengths.vkf').read_bytes();generated=raw.read_bytes()
lines=[line for line in original.splitlines(keepends=True) if b'?!' in line]
check(len(lines)==6 and lines==[line for line in generated.splitlines(keepends=True) if b'?!' in line],'six exact assertion bytes including line endings and order')
check(generated==original[:-5]+b'::true\n','only two inserted colon bytes')
check(generated.count(b'::true\n')==1 and generated.endswith(b'\n::true\n') and max(generated.index(line)+len(line) for line in lines)<=len(generated)-len(b'::true\n'),'explicit output occurs once after all six assertions')
# Run the actual isolated metadata generator branch with malformed tails; no plan or execution.
tree=ast.parse(current);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='tests_plan')
branch=next(n for n in ast.walk(function) if isinstance(n,ast.If) and ast.unparse(n.test)=="selection == 'metadata'")
code=compile(ast.Module(body=branch.body,type_ignores=[]),'actual metadata branch','exec')
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_tail_',dir=H) as tmp:
 t=Path(tmp);(t/'regressions').mkdir();source=t/'regressions/metadata_actual_lengths.vkf'
 for data in (original[:-1],original[:-5]+b'false\n',generated,original[:-5]):
  source.write_bytes(data);seen=[]
  try:exec(code,dict(REPAIR=t,require=a.require,case=lambda *args,**kw:seen.append(args)))
  except ValueError:pass
  else:raise AssertionError('malformed tail accepted')
  check(not seen,'changed/absent/already-emitting suffix rejected '+hashlib.sha256(data).hexdigest())
s=plan['stages'][-1]
check(s['stdout'].encode()==bytes.fromhex('747275650a') and s['expected_exit']==0 and Path(s['stdin']).read_bytes()==b'','original true-newline/exit/stdin oracle exact')
for code,out,err in [(0,'',''),(0,'true',''),(0,'true\n\n',''),(0,'false\n',''),(0,' true\n',''),(1,'true\n','')]:
 try:payload.check_result(s,code,out,err)
 except ValueError:check(True,'strict oracle rejects '+repr((code,out,err)))
 else:raise AssertionError('oracle loosened')
payload.check_result(s,0,'true\n','');check(True,'exact success oracle accepted without executing native')
a.check_plan(plan,seal['source_commit'],a.load_pin(seal['review']))
for mutate in (lambda q:q['stages'][1].update(cwd=str(Path(q['out'])/'metadata')),lambda q:q.update(unreviewed=True),lambda q:q['stages'][0].update(timeout=31),lambda q:q['stages'][-1].update(stdout=''),lambda q:q['cases'][0]['assertions'].update(metadata=5)):
 q=copy.deepcopy(plan);mutate(q)
 try:a.check_plan(q,seal['source_commit'],a.load_pin(seal['review']))
 except ValueError:check(True,'full-plan equality rejects mutation '+repr(q['stages'][-1]))
 else:raise AssertionError('full plan mutation accepted')
check((H/'adapter.py').read_text().replace("PACKAGE = HERE / 'generator'","PACKAGE = HERE.parent / 'compiler-build-preparation-03'")== (H.parent/'metadata-control-preparation-27/adapter.py').read_text(),'only PACKAGE binding differs; accepted complete adapter logic preserved')
# Execute only the pure pre-rotation predicate statements with in-memory TEST_ONLY rows.
rt=ast.parse((H/'root_steps.py').read_text());main=next(n for n in rt.body if isinstance(n,ast.FunctionDef) and n.name=='main')
rotate=next(n for n in main.body if isinstance(n,ast.If) and ast.unparse(n.test)=="args.step == 'rotate'")
pre=[]
for n in rotate.body:
 if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='root.mkdir':break
 pre.append(n)
precode=compile(ast.Module(body=pre,type_ignores=[]),'pure predecessor predicates','exec')
join=a.read(H.parent/'metadata-native-29/root-terminal-review.json')['join']
valid=dict(worker='A',stage='joined',sequence=15,owner='01a14a3a-d0d8-7a10-a188-717e31a22e31',join=join)
class TestLedger:
 def __init__(self,state):self.state=state
 def snapshot(self):return self.state
 def owner(self,state,worker):return valid['owner']
def exercise(key,row,owner='TEST_ONLY_FRESH_OWNER',independent=True,extra=None):
 state=dict(phases={key:row});state['phases'].update(extra or {})
 ns=dict(root=H/'TEST_ONLY_AUTHORITY_NEVER_CREATED',ledger=TestLedger(state),quiescent=lambda d:None,d=dict(owner=owner),verify_join=lambda r,j:independent,pinned_json=lambda ref:a.load_pin(ref))
 exec(precode,ns)
exercise('A:metadata-native29-01',valid);check(True,'exact USED joined native29 predecessor predicates accept read-only test state')
for key,row,owner,independent,extra in [
 ('A:d288-native24-01',dict(valid,sequence=14),'new',True,None),
 ('A:compiler-native17-01',dict(valid,sequence=13),'new',True,None),
 ('A:metadata-native29-01',dict(valid,stage='running'),'new',True,None),
 ('A:metadata-native29-01',dict(valid,owner='stale'),'new',True,None),
 ('A:metadata-native29-01',dict(valid,join=dict(join,sha256='0'*64)),'new',True,None),
 ('A:metadata-native29-01',valid,valid['owner'],True,None),
 ('A:metadata-native29-01',valid,'new',False,None),
 ('A:metadata-native29-01',valid,'new',True,{'A:intervening':dict(valid,sequence=16)})]:
 try:exercise(key,row,owner,independent,extra)
 except AssertionError:check(True,'succession rejects '+repr((key,row['sequence'],row['stage'],owner,independent,extra)))
 else:raise AssertionError('wrong predecessor accepted')
check(not (H/'TEST_ONLY_AUTHORITY_NEVER_CREATED').exists(),'predecessor tests made no authority directory or live lock call')
# Iteration gate uses actual source AST and in-memory decisions.
decision=next(n for n in rt.body if isinstance(n,ast.FunctionDef) and n.name=='decision')
gate=next(n for n in decision.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and len(n.value.args)>1 and isinstance(n.value.args[1],ast.Constant) and n.value.args[1].value=='fresh root execution owner/iteration required')
for iteration in (27,31,32):
 try:exec(compile(ast.Module(body=[gate],type_ignores=[]),'iteration gate','exec'),dict(a=a,d=dict(owner='TEST_ONLY',iteration=iteration)))
 except ValueError:check(True,'iteration '+str(iteration)+' rejected')
 else:raise AssertionError('stale iteration accepted')
exec(compile(ast.Module(body=[gate],type_ignores=[]),'iteration gate','exec'),dict(a=a,d=dict(owner='TEST_ONLY',iteration=33)));check(True,'iteration33 is minimum future proposal')
check('ledger.rotate_owner(tp,verify_join=verify_join)' in (H/'root_steps.py').read_text(),'independent in-lock installed rotation verifier retained')
for ref in a.read(H/'binding32-initial-observation.snapshot.json')['protected_pins']:a.verify(ref)
check(True,'binding32 historical protected pins still exact in current read-only recheck')
check(not host(['/usr/bin/git','-C',str(a.REPO),'diff','HEAD','--']),'tracked shared source untouched')
report=dict(passed=True,checks=checks,check_count=len(checks),assertions=[dict(hex=x.hex(),sha256=hashlib.sha256(x).hexdigest()) for x in lines],source_commit=seal['source_commit'],patch_scope='only reviewed metadata branch; all other generator bytes identical',children=children,native_execution=False,operational_mutations=0,seconds=time.monotonic()-start)
a.save(H/'independent-verification.json',report);print(json.dumps(dict(passed=True,checks=len(checks),seconds=report['seconds'])))
