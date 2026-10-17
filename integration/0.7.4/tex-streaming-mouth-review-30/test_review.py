"""Independent handwritten expectations against TSL28 Python model, NOT VKF execution."""
from pathlib import Path
import copy,dataclasses,hashlib,json,sys,unittest,re
H=Path(__file__).resolve().parent;P=H.parent/'tex-streaming-lexer-28';R=H.parents[2]
sys.path.insert(0,str(P))
from reference_model import Mouth,Diagnostic
class Review(unittest.TestCase):
 def test_handwritten_boundaries(self):
  for row in json.loads((H/'boundary-cases.json').read_text()):
   with self.subTest(row['id']):
    m=Mouth(row['raw'].encode())
    for args in row['assign']:m.assign(*args)
    for kind,cat,value,a,b,prov,origin in row['tokens']:
     t=m.next();self.assertEqual((t.kind,t.category,t.value,t.start,t.stop,t.provenance),(kind,cat,value,a,b,prov))
     if origin is not None:self.assertEqual(t.origin,origin)
    t=m.next();self.assertEqual((t.kind,t.start,t.stop,t.origin),(0,len(m.raw),len(m.raw),-1))
 def test_rollback_from_nonzero_cursor_and_prefix(self):
  for raw,code,span in [('a%α\n \x7f',3,(6,7)),('x\\aα',1,(3,5)),('x\\ab^^63',2,(4,5)),('x!!z',2,(1,2))]:
   m=Mouth(raw.encode())
   if raw=='x!!z':m.assign(33,7)
   m.next();before=m.checkpoint()
   with self.assertRaises(Diagnostic) as error:m.next()
   self.assertEqual((error.exception.code,error.exception.start,error.exception.stop),(code,*span))
   self.assertEqual(m.checkpoint(),before)
  m=Mouth('a%α\n \x7f'.encode());old=m.next();m.assign(127,12);t=m.next()
  self.assertEqual((t.category,t.start,t.origin),(12,6,1));self.assertEqual(old.category,11)
  m=Mouth(b'x\\ab^^63');m.next()
  with self.assertRaises(Diagnostic):m.next()
  m.assign(94,12);self.assertEqual(m.next().value,'ab')
 def test_feedback_at_each_boundary(self):
  for target,cat,kind,value in [(64,13,3,'@'),(64,0,2,'b'),(64,9,1,'b'),(64,14,0,'')]:
   m=Mouth(b'\\a@b');word=m.next();m.assign(target,cat);t=m.next()
   self.assertEqual((word.value,t.kind,t.value),('a',kind,value))
  m=Mouth(b'\\a%z\n x');m.next();m.assign(37,12);self.assertEqual(m.next().value,'%')
  # New physical lines reset to new_line even after comment/escaped logical CR.
  m=Mouth(b'a\n!x');m.next();m.next();m.assign(33,10);self.assertEqual(m.next().value,'x')
 def test_checkpoint_difference_dimensions(self):
  m=Mouth(b'a b',origins=[dict(source=0,occurrence=0,start=0,stop=1,role='definition',definition=-1,invocation=-1)])
  m.next();saved=m.checkpoint()
  for field,value in [('revision','changed'),('source',1),('occurrence',1),('state',2),('offset',9),('index',9)]:
   changed=copy.deepcopy(saved);changed[field]=value;self.assertFalse(m.reusable(changed))
  for field in ['definition','invocation','role']:
   changed=copy.deepcopy(saved);changed['origins'][0][field]='changed';self.assertFalse(m.reusable(changed))
  changed=copy.deepcopy(saved);changed['cats'][64]=13;self.assertFalse(m.reusable(changed))
  m.assign(64,12);self.assertFalse(m.reusable(saved))
 def test_exact_input_pins(self):
  for row in json.loads((H/'input-pins.json').read_text()):
   self.assertEqual(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest(),row['sha256'],row['path'])
 def test_candidate_is_comment_and_regression_only(self):
  base=P/'candidate/examples/gpu-math/native-vkf';new=H/'candidate/examples/gpu-math/native-vkf'
  def code(p):return '\n'.join(x for x in p.read_text().splitlines() if not x.lstrip().startswith('#'))
  self.assertEqual(code(base/'tex_streaming_mouth.vkf'),code(new/'tex_streaming_mouth.vkf'))
  self.assertEqual((base/'host/latex_mouth_origins.mjs').read_bytes(),(new/'host/latex_mouth_origins.mjs').read_bytes())
  b=(base/'tex_streaming_mouth_tests.vkf').read_text();n=(new/'tex_streaming_mouth_tests.vkf').read_text()
  self.assertTrue(n.startswith(b[:-len('renderer_tests()\n')]))
  manifest=json.loads((H/'native-supplement.json').read_text());self.assertEqual(len(manifest['additional_positive']),29)
  for name in manifest['additional_positive']:
   self.assertEqual(n.count(name+'()->bit:'),1);self.assertIn(name+'()?!',n)
  self.assertEqual(n.count('\nrenderer_tests()\n'),1)
  self.assertFalse(manifest['executed']);self.assertFalse(manifest['compiled'])
  # Syntax comparison only: these patterns exist in real repository code.
  self.assertIn('.value:int($)',(R/'examples/gpu-math/native-vkf/resource_json.vkf').read_text())
  self.assertIn('str(chr(0))',(R/'examples/gpu-math/native-vkf/project_tests.vkf').read_text())
 def test_profile_and_contract_counterexample(self):
  m=Mouth(b'a ');m.next();t=m.next()
  self.assertEqual((t.start,t.stop,t.provenance,t.origin),(1,2,1,1))
  corrected=(H/'MOUTH-CONTRACT-reviewed.txt').read_text()
  self.assertIn('only when no trimmed trailing spaces remain',corrected)
  self.assertIn('nonempty composite control-token span',corrected)
  m=Mouth(b'\f');self.assertEqual(m.next().category,12) # Own profile, not plain's active FF.
  for raw in [b'^^',b'\\a^^',b'!!']:
   m=Mouth(raw)
   if raw==b'!!':m.assign(33,7)
   with self.assertRaises(Diagnostic):m.next()
if __name__=='__main__':unittest.main(verbosity=2)
