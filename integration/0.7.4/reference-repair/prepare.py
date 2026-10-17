"""Prepare PRIVATE review artifacts only. Does not invoke a compiler or edit shared inputs."""
from pathlib import Path
import hashlib,json,re,difflib,subprocess
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SRC=ROOT/'examples/gpu-math/native-vkf'
HIST=Path('/home/viktor/.cache/vkf-s0-runtimes-20261012/Integrator/independent-worker-F/iteration303-qualification01')
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,b):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def jsonwrite(p,j):write(p,(json.dumps(j,indent=2)+'\n').encode())
plan=json.loads((HIST/'plan.json').read_text())
manifest=json.loads((HIST/'manifest.json').read_text())
post=json.loads((HIST/'posthashes.json').read_text())
def rows(j):
 if isinstance(j,dict):
  if 'path' in j and 'sha256' in j:yield j
  for v in j.values():yield from rows(v)
 elif isinstance(j,list):
  for v in j:yield from rows(v)
indexes=[{r['path']:r for r in rows(j)} for j in [plan,manifest,post]]
need=['document_scene_paragraph','document_scene_export']; frozen={};evidence=[]
while need:
 name=need.pop()
 if name in frozen:continue
 p=HIST/'renderer-source'/(name+'.vkf');b=p.read_bytes();h=sha(b)
 pins=[idx[str(p)] for idx in indexes]
 assert all(r['sha256']==h for r in pins)
 assert pins[2]['unchanged'] is True
 frozen[name]=b
 need+=re.findall(r'^\w+:\.(\w+)\s*$',b.decode(),re.M)
 evidence.append({'path':str(p),'sha256':h,'historical_pin_matches':['plan.renderer_source_pins','manifest.inputs','posthashes (unchanged=true)']})
for name,b in frozen.items():
 write(OUT/'original-reference'/(name+'.vkf'),b)
 # Only import targets change. Existing aliases, algorithms and literal values remain exact.
 transformed=re.sub(r'^(\w+:\.)(\w+)(\s*)$',lambda m:m[1]+'ref_f303_'+m[2]+m[3],b.decode(),flags=re.M)
 write(OUT/'candidate'/('ref_f303_'+name+'.vkf'),transformed.encode())
# Independent pre-normalization copy provides an additional algorithm identity check.
c278=Path('/home/viktor/.cache/vkf-s0-runtimes-20261012/Native/reports/native3-integer-power01/independent-worker-C/iteration278-provider01/apply-base/document_scene_paragraph.vkf')
s=frozen['document_scene_paragraph'].decode()
for alias,name in re.findall(r'^(\w+):\.(\w+)\s*$',s,re.M):s=re.sub(r'\b'+alias+r'\b',name,s)
assert s==c278.read_text()
write(OUT/'original-reference'/'c278_document_scene_paragraph.vkf',c278.read_bytes())
# Legacy input stays 31 fields. Current output declaration is copied verbatim (40 fields).
adapter=(SRC/'typed_packet_reference_adapter.vkf').read_text()
legacy=next(l for l in adapter.splitlines() if l.startswith('LegacyPacket:'))
packet=next(l for l in (SRC/'document_scene_paragraph_linear.vkf').read_text().splitlines() if l.startswith('Packet:'))
adapter=re.sub(r'^Packet:.*$',lambda _:packet,adapter,flags=re.M)
insert='''    # Ordering ordinals are retained; absent authored provenance is explicitly unknown.
    (input.glyph_count>=0 /\\ input.glyph_count<=input.glyph_operations.length() /\\ input.scene_count>=0 /\\ input.scene_count<=input.scene_operations.length())?! "Legacy active operation bounds"
    operations:0
    at:0
    at<input.glyph_count?>
        op:input.glyph_operations.(at)
        (op>= -1)?! "Legacy glyph operation domain"
        op>=operations? .operations:op+1
        .at:at+1
    .at:0
    at<input.scene_count?>
        op:input.scene_operations.(at)
        (op>= -1)?! "Legacy scene operation domain"
        op>=operations? .operations:op+1
        .at:at+1
    [int] unknown_starts:[-1:operations]
    [int] unknown_stops:[-1:operations]
    [int] no_events:[0:0]
'''
adapter=adapter.replace('    scenes:store.empty()',insert+'    scenes:store.empty()\n    no_ids:scenes.anchor_ids')
adapter=adapter.replace('pass:input.pass)','pass:input.pass,a260_text:"",a260_starts:unknown_starts,a260_stops:unknown_stops,a272_anchor_operations:no_events,a272_anchor_ids:no_ids,a277_anchor_scenes:no_events,a280_anchor_leaves:no_events,a280_anchor_slots:no_events,a282_anchor_points:no_events)')
harness=(SRC/'typed_packet_reference_harness_tests.vkf').read_text()
harness=harness.replace('document_scene_paragraph:.document_scene_paragraph','document_scene_paragraph:.ref_f303_document_scene_paragraph\nreference_export:.ref_f303_document_scene_export')
harness=re.sub(r'^Packet:.*$',lambda _:legacy.replace('LegacyPacket:','Packet:',1),harness,flags=re.M)
harness=harness.replace('before:document_scene_paragraph.from_paragraph(packet_adapter.from_legacy(q))','before:document_scene_paragraph.from_paragraph(q)')
harness=harness.replace('metadata_json.encode(a.metadata,a.metadata_roots.(i))','a.extras.(i)')
harness=harness.replace('old_json:document_scene_export.leaf(a,i,1,1)','old_json:reference_export.leaf(a,i,1,1)')
patch=''
for name,content in [('typed_packet_reference_adapter.vkf',adapter),('typed_packet_reference_harness_tests.vkf',harness)]:
 old=(SRC/name).read_text();write(OUT/'candidate'/name,content.encode())
 patch+=''.join(difflib.unified_diff(old.splitlines(True),content.splitlines(True),fromfile='a/examples/gpu-math/native-vkf/'+name,tofile='b/examples/gpu-math/native-vkf/'+name))
write(OUT/'review.patch',patch.encode())
orig=(SRC/'typed_packet_reference_harness_tests.vkf').read_text()
assert re.findall(r'\?![^\n]*',orig)==re.findall(r'\?![^\n]*',harness)
oldref=(SRC/'document_scene_paragraph_linear_reference_tests.vkf').read_text()
# Every independent literal JS geometry assertion and fixture JSON line is retained exactly.
js=[l for l in oldref.splitlines() if '?! "actual JS' in l]
assert all(l in harness.splitlines() for l in js)
fixtures=[l for l in oldref.splitlines() if re.match(r'    index=\d\? values',l)]
assert all(l in harness.splitlines() for l in fixtures)
currentpins={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in SRC.glob('*.vkf')}
jsonwrite(OUT/'provenance.json',{'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'historical_sources':evidence,'historical_receipts':{str(HIST/f):sha((HIST/f).read_bytes()) for f in ['manifest.json','plan.json','posthashes.json']},'c278_identity':{'path':str(c278),'sha256':sha(c278.read_bytes()),'alias_canonicalization_equal':True},'current_source_pins':currentpins,'candidate_pins':{str(p.relative_to(OUT)):sha(p.read_bytes()) for p in (OUT/'candidate').glob('*.vkf')}})
result={'native_build_executed':False,'frozen_reference_modules':len(frozen),'historical_triplicate_pins_verified':len(evidence),'harness_assertion_markers_preserved':len(re.findall(r'\?!',orig)),'original_JS_assertion_lines_exact':len(js),'original_JS_fixture_lines_exact':len(fixtures),'legacy_fields':len(legacy.split(',')),'output_fields':len(packet.split(',')),'reference_has_no_linear_dependency':not any('paragraph_linear' in b.decode() for b in frozen.values()),'production_source_files_changed':[]}
jsonwrite(OUT/'static-checks.json',result)
print(json.dumps(result,indent=2))
