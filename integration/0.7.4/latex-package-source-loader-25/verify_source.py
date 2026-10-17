"""Preparation/source invariants only; no native execution or TeX oracle."""
from pathlib import Path
import hashlib,json,re,unittest,difflib
H=Path(__file__).resolve().parent;R=H.parents[2];C=H/'candidate'
class SourceChecks(unittest.TestCase):
 def test_shared_inputs_unchanged(self):
  for row in json.loads((H/'input-pins.json').read_text()):
   b=Path(row['path']).read_bytes()
   self.assertEqual(len(b),row['bytes']);self.assertEqual(hashlib.sha256(b).hexdigest(),row['sha256'],row['path'])
 def test_installed_inputs_licenses_and_exact_boundary_positions(self):
  m=json.loads((H/'installed-sources.json').read_text())
  for row in m['files']+m['license_evidence']:
   b=Path(row['path']).read_bytes();self.assertEqual(hashlib.sha256(b).hexdigest(),row['sha256'])
   for name in ['first_boundary','state_boundary']:
    if name not in row:continue
    x=row[name];self.assertEqual(b[x['startByte']:x['stopByte']].decode(),x['text'])
    self.assertEqual(b[:x['startByte']].count(b'\n')+1,x['line'])
 def test_host_native_source_column_contract(self):
  native=(C/'examples/gpu-math/native-vkf/tex_package_sources.vkf').read_text()
  typ=re.search(r'^Sources:\((.*)\)$',native,re.M).group(1)
  self.assertEqual(typ.split(','),['schema:int','revision:str','ids:[str]','versions:[int]','texts:[str]','hashes:[str]'])
  self.assertIn('Span:(source:int,start:int,stop:int)',native)
  # This checks the explicit failure gate/contract, not VKF execution semantics.
  self.assertIn('false?! "TEX_PACKAGE_INTERPRETER_UNAVAILABLE:',native)
  self.assertNotIn('macros.expand',native)
 def test_small_isolated_patch_exact_payload(self):
  paths=sorted(p for p in C.rglob('*') if p.is_file())
  self.assertEqual(len(paths),4)
  patch=[]
  for p in paths:
   rel=p.relative_to(C).as_posix();self.assertFalse((R/rel).exists(),rel)
   patch.append(f'diff --git a/{rel} b/{rel}\nnew file mode 100644\n')
   patch.extend(difflib.unified_diff([],p.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+rel))
  self.assertEqual(''.join(patch),(H/'package-source-foundation.patch').read_text())
 def test_native_followup_cases_are_declared_unexecuted(self):
  fixtures=json.loads((H/'native-fixtures.json').read_text())
  self.assertFalse(fixtures['executed']);self.assertEqual(len(fixtures['negative']),3)
  tests=(C/'examples/gpu-math/native-vkf/tex_package_sources_tests.vkf').read_text()
  for row in fixtures['negative']:self.assertIn(row['function']+'()',tests)
  self.assertIn('(p.read(table,(source:0,start:2,stop:6))="😀")',tests)
if __name__=='__main__':unittest.main()
