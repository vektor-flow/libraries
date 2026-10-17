import pathlib,sys,os,stat,json,time,hashlib,subprocess
OUT=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))
from preflight import a,PACKET,STORAGE,save
start=time.monotonic();tag=sys.argv[1]
g=a.read(STORAGE/'metadata-native-36-visible-chat-grant.json');a.verify(g['root_decision']);d=a.load_pin(g['root_decision'])
assert g['owner_thread']==d['owner']=='01a14a8f-593f-7e52-ab64-5f143417903e' and g['max_native_attempts']==1
assert a.current_head()==g['source_commit']==d['source_commit']=='0d6d2bea2eb8015ee56f95b1e0eaf78e3d3c3108'
assert subprocess.run(['git','diff','--quiet'],cwd=a.REPO).returncode==0
for ref in d['root_review'].values():a.verify(ref)
review=a.load_pin(d['root_review']['review35']);assert not review['blockers']
for k in ('packet_delivery','packet_artifact_manifest','source_contract','plan','recipe'):a.verify(review[k])
verified=[];counts={}
for name,n in [('metadata-repaired-binding-32/artifact-pins.json',119),('metadata-repaired-binding-32/input-pins.json',1074),('metadata-binding-review-35/artifact-pins.json',38),('metadata-native-29/attempt-artifact-pins.json',62)]:
 rows=a.read(OUT.parent/name);assert len(rows)==n,(name,len(rows))
 for ref in rows:
  p=pathlib.Path(ref['path'])
  if ref.get('type')=='symlink':
   assert p.is_symlink() and os.readlink(p)==ref['readlink'];assert a.pin(p)['sha256']==ref['target_sha256']
  else:
   a.verify(ref)
   if ref.get('type')=='regular':assert stat.S_ISREG(p.lstat().st_mode) and p.stat().st_nlink==ref['nlink'] and p.stat().st_size==ref['bytes']
  verified.append(ref)
 counts[name]=n
s=a.static_contract();plan=a.load_pin(s['control_plan']);a.check_plan(plan,g['source_commit'],a.load_pin(s['review']))
proof=a.read(OUT.parent/'metadata-entry-repair-31/source-proof.json');assert proof['passed']
for excerpt in proof['source_excerpts']:
 a.verify(excerpt['source']);lines=pathlib.Path(excerpt['source']['path']).read_text().splitlines()
 assert '\n'.join(lines[excerpt['first_line']-1:excerpt['last_line']])==excerpt['text']
oracle=a.read(PACKET/'exact-oracles.json');raw=(PACKET/'staging/metadata/metadata/raw/metadata.vkf').read_bytes();original=(OUT.parent/'metadata-control-preparation-27/staging/metadata/metadata/raw/metadata.vkf').read_bytes()
assert original.endswith(b'\ntrue\n') and raw==original[:-5]+b'::true\n' and raw.count(b'::true\n')==1
assert [x.hex() for x in raw.splitlines(keepends=True) if b'?!' in x]==[x['hex'] for x in oracle['assertions']]
assert plan['stages'][-1]['stdout'].encode().hex()==oracle['expected_stdout_hex']=='747275650a'
receipt=a.load_pin(s['compiler_receipt']);a.verify(receipt['compiler']);assert receipt['compiler']['sha256']=='52116e581d041836505756fcde17d504422429e410f0c84cb353409e121948d9'
with pathlib.Path(receipt['compiler']['path']).open('rb') as f:assert f.read(4)==b'\x7fELF'
save(tag+'-authority-pins.json',verified)
save(tag+'-audit.json',dict(passed=True,counts=counts,grant=a.pin(STORAGE/'metadata-native-36-visible-chat-grant.json'),decision=g['root_decision'],compiler=receipt['compiler'],assertions=oracle['assertions'],expected_stdout_hex='747275650a',seconds=time.monotonic()-start))
print(json.dumps(dict(passed=True,counts=counts,seconds=time.monotonic()-start)))
