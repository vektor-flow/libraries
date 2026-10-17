from pathlib import Path
import difflib
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SRC=ROOT/'examples/gpu-math/native-vkf'
name='typed_packet_reference_harness_tests.vkf'
before=(SRC/name).read_text()
after=before.replace('metadata_json:.scene_metadata_json\n','metadata_json:.scene_metadata_json\nordered_json:.test_ordered_json\n')
after=after.replace('        extra_matches(a.extras.(i),b.metadata,b.metadata_roots.(i))?! "column extras exact"','        ordered_json.metadata_matches(a.extras.(i),b.metadata,b.metadata_roots.(i))?! "column extras exact"')
after=after.replace('        (old_json=new_json)?! "debug leaf export exact"','        ordered_json.json_matches(old_json,new_json)?! "debug leaf export exact"')
after=after.replace('renderer_tests()\n','ordered_json.contract_tests()?! "Independent ordered JSON comparison contract"\nrenderer_tests()\n')
# The old helper and its byte-contract assertions remain an explicit separate
# obligation. The two differential boundaries now follow the accepted contract.
(OUT/'candidate'/name).write_text(after)
patch=''
for p in sorted((OUT/'candidate').glob('*.vkf')):
    prior=(SRC/p.name).read_text() if (SRC/p.name).exists() else ''
    patch+=''.join(difflib.unified_diff(prior.splitlines(True),p.read_text().splitlines(True),fromfile='a/examples/gpu-math/native-vkf/'+p.name if prior else '/dev/null',tofile='b/examples/gpu-math/native-vkf/'+p.name))
(OUT/'final.patch').write_text(patch)
