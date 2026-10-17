"""Structural/source checks only. No claim these execute or parse VKF."""
from pathlib import Path
import difflib,hashlib,json,re,unittest
H=Path(__file__).resolve().parent;R=H.parents[2];C=H/'candidate';N=C/'examples/gpu-math/native-vkf'
class SourceChecks(unittest.TestCase):
 def test_shared_source_inputs_unchanged(self):
  for row in json.loads((H/'input-pins.json').read_text()):
   if '/native-vkf/' not in row['path']:continue # root-owned status may advance
   b=Path(row['path']).read_bytes();self.assertEqual(hashlib.sha256(b).hexdigest(),row['sha256'],row['path'])
 def test_exact_source_and_origin_columns(self):
  source=(N/'tex_streaming_mouth.vkf').read_text()
  current=(R/'examples/gpu-math/native-vkf/tex_package_sources.vkf').read_text()
  self.assertEqual(re.search(r'^Sources:.*',source,re.M).group(),re.search(r'^Sources:.*',current,re.M).group())
  columns=re.search(r'^Origins:\((.*)\)$',source,re.M).group(1).split(',')
  self.assertEqual(columns,['revision:str','occurrence_sources:[int]','occurrence_via:[int]','source:[int]','occurrence:[int]','start:[int]','stop:[int]','role:[str]','definition:[int]','invocation:[int]'])
 def test_core_boundaries_present(self):
  s=(N/'tex_streaming_mouth.vkf').read_text()
  for marker in ['next(table:Sources,origins:Origins,input:State,categories:Categories)','TEX_PREVIEW_TOKEN_FORBIDDEN','code>=128? @:1','cat=15? @:failure','cat=14?','cat=5?','cat=10?','cat=0?','cat=13?','TEX_MOUTH_STALE_SOURCE','ac.values.(index)~=bc.values.(index)','ao.definition.(index)~=bo.definition.(index)']:
   self.assertIn(marker,s)
  self.assertNotIn('strip_comments',s);self.assertNotIn('tex_macros',s);self.assertNotIn('groups.control',s)
  self.assertNotRegex(s,r'\.state\.[a-z_]+:')
 def test_patch_exact_new_files_only(self):
  paths=sorted(p for p in C.rglob('*') if p.is_file());self.assertEqual(len(paths),3);patch=[]
  for p in paths:
   rel=p.relative_to(C).as_posix();self.assertFalse((R/rel).exists(),rel)
   patch.append(f'diff --git a/{rel} b/{rel}\nnew file mode 100644\n')
   patch.extend(difflib.unified_diff([],p.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+rel))
  self.assertEqual(''.join(patch),(H/'streaming-mouth.patch').read_text())
 def test_future_native_expected_cases_present(self):
  manifest=json.loads((H/'native-fixtures.json').read_text());self.assertFalse(manifest['executed']);self.assertFalse(manifest['compiled'])
  s=(N/'tex_streaming_mouth_tests.vkf').read_text()
  for name in manifest['positive']:self.assertIn(name+'()->bit:',s)
  for row in manifest['negative']:self.assertIn(row['function']+'()',s)
  for row in json.loads((H/'cases.json').read_text()):self.assertIn('case_'+row['id'].replace('-','_')+'()',s)
  self.assertGreater(s.count('?!'),130)
 def test_installed_inputs_and_license_pins(self):
  m=json.loads((H/'installed-sources.json').read_text())
  for row in m['files']+m['license_evidence']:
   b=Path(row['path']).read_bytes();self.assertEqual(len(b),row['bytes']);self.assertEqual(hashlib.sha256(b).hexdigest(),row['sha256'])
   for key in ['first_boundary','state_boundary']:
    if key in row:
     span=row[key];self.assertEqual(b[span['startByte']:span['stopByte']].decode(),span['text'])
if __name__=='__main__':unittest.main()
