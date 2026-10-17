"""Source-delta and independent content checks; NOT a native interpreter/reader."""
from pathlib import Path
import hashlib,json,difflib,re,unittest
H=Path(__file__).resolve().parent;R=H.parents[2];B=R/'examples/gpu-math/native-vkf';C=H/'candidate/examples/gpu-math/native-vkf'
class SourceContracts(unittest.TestCase):
 def test_inputs_unchanged(self):
  for path,pin in json.loads((H/'input-pins.json').read_text()).items():
   self.assertEqual(hashlib.sha256((R/path).read_bytes()).hexdigest(),pin,path)
 def test_native_schema_and_host_seal(self):
  typ=(H/'plan-type.txt').read_text().strip()
  for name in ['document_pdf_bulk.vkf','pdf_selection_plan.vkf']:
   self.assertIn(typ,(C/name).read_text())
  schema=(H/'SelectionPlan.schema.json').read_bytes();data=json.loads(schema)
  self.assertEqual([(r['name'],r['type']) for r in data['fields']], [tuple(p.split(':')) for p in typ.split('(',1)[1][:-1].split(',')])
  self.assertIn(hashlib.sha256(schema).hexdigest(),(C/'host/latex_pdf_selection.mjs').read_text())
 def test_exact_legacy_core_body_preserved_after_removing_selected_hooks(self):
  before=(B/'document_pdf_bulk.vkf').read_text();after=(C/'document_pdf_bulk.vkf').read_text()
  old=before[before.index('    arena:doc.arena\n'):before.index('\n# Bulk chunks')]
  new=after[after.index('    arena:doc.arena\n'):after.index('\n# Bulk chunks')]
  new=new.replace('    selected_cluster:0\n','',1).replace('        selection_begin:1\n','',1)
  new=new.replace('            selected?\n                item=selection_firsts.(selected_cluster)? .selection_begin:command_count\n','',1)
  hook='''            selected?
                item+1=selection_firsts.(selected_cluster)+selection_counts.(selected_cluster)?
                    drawing:text_chunks.join(commands,selection_begin,command_count)
                    commands.(selection_begin):selection.actual_text(selection_texts.(selected_cluster),drawing)
                    .command_count:selection_begin+1
                    .selected_cluster:selected_cluster+1
'''
  self.assertEqual(new.count(hook),1);new=new.replace(hook,'',1)
  self.assertEqual(new,old)
  self.assertIn('encode_core(doc,fonts,operators,default_color,false,no_firsts,no_counts,no_texts)',after)
  self.assertIn('logical:selection_plan.validate(doc,plan)\n    @:encode_core',after)
  self.assertEqual(before[before.index('# Bulk chunks'):],after[after.index('# Bulk chunks'):])
 def test_record_and_serializer_unchanged(self):
  for typ in ['Arena','PageDocument','Result','Catalog']:
   old=re.search('^'+typ+r':.*$',(B/'document_pdf_bulk.vkf').read_text(),re.M).group()
   new=re.search('^'+typ+r':.*$',(C/'document_pdf_bulk.vkf').read_text(),re.M).group()
   self.assertEqual(old,new)
  self.assertFalse((C/'pdf_selection.vkf').exists())
  self.assertFalse((C/'pdf_objects.vkf').exists())
 def test_independent_utf16be_vectors(self):
  # Explicit expectations vs standard codec, no native execution claim.
  for text,hexed in [('😀','D83DDE00'),('fi','00660069'),('e\u0301','00650301'),('x','0078')]:
   self.assertEqual(text.encode('utf-16-be').hex().upper(),hexed)
   self.assertIn('/ActualText <FEFF'+hexed+'>',(C/'pdf_selection_encoder_tests.vkf').read_text())
 def test_model_cluster_wrapping_preserves_every_drawing_byte_and_order(self):
  # Model only, independent per-page token stream. Cross-page clusters are
  # rejected by real HOST tests; native fixture executes hook later.
  logical=['😀','fi','e\u0301','x','x'];counts=[1,1,2,1,1];firsts=[0,1,2,4,5]
  emitted=[]; pages=[]
  for lo,hi in [(0,4),(4,6)]:
   legacy=['q 1 0 0 -1 0 100 cm'];selected=[legacy[0]]
   for cluster,(first,count) in enumerate(zip(firsts,counts)):
    if not lo<=first<hi:continue
    drawing=''.join('\n0 0 0 rg\nq 1 0 0 1 '+str(i*12)+' 30 cm /G0 Do Q' for i in range(first,first+count))
    legacy.append(drawing)
    marked='/Span << /ActualText <FEFF'+logical[cluster].encode('utf-16-be').hex().upper()+'> >> BDC\n'+drawing+'\nEMC\n'
    selected.append(marked);emitted.append(logical[cluster])
   legacy.append('\nQ');selected.append('\nQ');original=''.join(legacy);wrapped=''.join(selected)
   recovered=re.sub(r'/Span << /ActualText <[A-F0-9]+> >> BDC\n(.*?)\nEMC\n',r'\1',wrapped,flags=re.S)
   self.assertEqual(recovered,original)
   self.assertEqual(wrapped.count('BDC'),wrapped.count('EMC'));pages.append(wrapped)
  self.assertEqual(emitted,['😀','fi','e\u0301','x','x']);self.assertEqual(len(pages),2)
 def test_patch_reconstruction(self):
  patch=[]
  for p in sorted((H/'candidate').rglob('*')):
   if not p.is_file():continue
   rel=p.relative_to(H/'candidate').as_posix();old=R/rel
   patch.append(f'diff --git a/{rel} b/{rel}\n')
   if not old.exists():patch.append('new file mode 100644\n')
   patch.extend(difflib.unified_diff(old.read_text().splitlines(True) if old.exists() else [],p.read_text().splitlines(True),fromfile='a/'+rel if old.exists() else '/dev/null',tofile='b/'+rel))
  self.assertEqual((H/'selection-implementation.patch').read_text(),''.join(patch))
unittest.main()
