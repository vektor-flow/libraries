from pathlib import Path
import hashlib,json,subprocess,datetime,os
H=Path(__file__).resolve().parent;R=H.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,pin in json.loads((H/'input-pins.json').read_text()).items():assert sha(R/rel)==pin,rel
peer=json.loads((H/'final-peer-contract-pins.json').read_text())
for rel,pin in peer['pins'].items():assert sha(R/rel)==pin,rel
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert head in ['4302f7a03a5d812bf1eaf35848557d157d2e5aae','124ded9a103af1df108ba5b3334021d78b811c65'],head
checks=json.loads((H/'final-results.json').read_text());assert checks['passed'] and checks['all_children_joined']
for name in ['checks01-results.json','checks02-results.json','final-results.json']:
 for stage in json.loads((H/name).read_text())['stages']:
  assert stage['joined'] and not Path('/proc',str(stage['pid'])).exists(),stage
files=[p for p in (H/'candidate').rglob('*') if p.is_file()]
assert len(files)==5
result={'id':'pdf-selection-implementation-22','owner':'01a14a1d-0472-78f3-a88e-39d98a0256da','coordinator':'01a14893-cb1e-7203-97dd-de3da44dcf31','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'DONE_SOURCE_PROPOSAL_NATIVE_READER_API_UNQUALIFIED','grant_head':'4302f7a03a5d812bf1eaf35848557d157d2e5aae','observed_root_successor_head':head,'all_production_input_pins_unchanged':True,'final_peer_contracts_pinned':True,'patch':{'path':'selection-implementation.patch','sha256':sha(H/'selection-implementation.patch'),'files':len(files),'applied':False},'schema':{'path':'SelectionPlan.schema.json','sha256':sha(H/'SelectionPlan.schema.json')},'handoff':'HANDOFF.txt','contract':'SELECTION-CONTRACT.txt','host_checks':{'selection_tests':13,'existing_bridge_tests':17,'existing_provenance_checks':5,'existing_provenance_comparisons':1711,'source_checks':7,'patch_check':'PASS','receipt':'final-results.json'},'host_memory':{'cap_bytes':536870912,'wall_timeout_seconds':60,'final_child_maxrss_kib':checks['child_maxrss_kib'],'initial_failure':'async loader extra isolate std::bad_alloc under same AS cap; checks01 retained; joined','repair':'sync Node registerHooks under same AS cap; checks02/final passed'},'all_children_joined_and_absent_at_seal':True,'native_executed':False,'native_fixtures':{'positive_harnesses':1,'negative_harnesses':8,'status':'UNEXECUTED','manifest':'native-fixtures.json'},'reader_qualified':False,'api_default_supported':False,'native_completion_registry_implemented':False,'shared_writes':False,'subagents':False,'commits':False,'operational_mutation':False,'remaining':['actual logical source/expansion/include/page-split producer','trusted native marshaller and same-invocation completion registry with byte pins','immutable native resource identity','standard reader text/ToUnicode fallback and source/map attachment','standalone guarded atomic PDF publication','native legacy equality/geometry/raster and reader qualification']}
(H/'result.json').write_text(json.dumps(result,indent=2)+'\n')
exclude={'artifact-pins.json','done-notification-intent.json','done-notification-result.json'}
pins={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in exclude}
(H/'artifact-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'status':result['status'],'head':head,'patch_sha256':result['patch']['sha256'],'schema_sha256':result['schema']['sha256'],'artifacts':len(pins),'all_children_joined':True}))
