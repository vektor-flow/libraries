from pathlib import Path
import copy,dataclasses,hashlib,json,unittest
from reference_model import Mouth,Token,Diagnostic,tokens,strict_token
H=Path(__file__).resolve().parent
class ReferenceChecks(unittest.TestCase):
 def test_handwritten_tables(self):
  for row in json.loads((H/'cases.json').read_text()):
   with self.subTest(row['id']):
    if 'diagnostic' in row:
     m=Mouth(row['raw'].encode());before=m.checkpoint()
     with self.assertRaises(Diagnostic) as e:m.next()
     self.assertEqual(e.exception.code,row['diagnostic']);self.assertTrue(m.reusable(before))
    else:
     ts=tokens(row['raw'].encode(),row.get('assign',[]))
     self.assertEqual([[t.kind,t.category,t.value] for t in ts],row['tokens'])
     if 'spans' in row:self.assertEqual([[t.start,t.stop,t.provenance] for t in ts],row['spans'])
 def test_assignment_between_reads_and_retained_tokens(self):
  m=Mouth(b'@\\a@b %x');old=m.next();self.assertEqual(old.category,12)
  m.assign(64,11);word=m.next();self.assertEqual(word.value,'a@b');self.assertEqual(old.category,12)
  m.assign(37,12);percent=m.next();self.assertEqual(percent.value,'%');self.assertEqual(percent.category,12)
 def test_lookahead_not_frozen(self):
  m=Mouth(b'\\a@b');self.assertEqual(m.next().value,'a');m.assign(64,13)
  self.assertEqual(m.next().kind,3)
 def test_category_table_breadth(self):
  # Every ordinary category accepted by assignment, with independent expectations.
  expected={0:[2,-1,'a'],1:[1,1,'!'],2:[1,2,'!'],3:[1,3,'!'],4:[1,4,'!'],6:[1,6,'!'],7:[1,7,'!'],8:[1,8,'!'],9:[1,11,'a'],10:[1,11,'a'],11:[1,11,'!'],12:[1,12,'!'],13:[3,13,'!'],14:[0,-1,'']}
  for cat,wanted in expected.items():
   m=Mouth(b'!a');m.assign(33,cat);t=m.next();self.assertEqual([t.kind,t.category,t.value],wanted)
  m=Mouth(b'!a');m.assign(33,15)
  with self.assertRaises(Diagnostic) as e:m.next()
  self.assertEqual(e.exception.code,3)
 def test_reject_unsupported_assignments(self):
  for code,cat in [(13,12),(10,11),(200,12),(-1,11),(64,5),(64,16),(64,-1)]:
   with self.assertRaises(ValueError):Mouth(b'').assign(code,cat)
 def test_checkpoint_invalidation_and_replay(self):
  m=Mouth(b'a b');m.next();point=m.checkpoint();self.assertTrue(m.reusable(point))
  for key in ['revision','source','occurrence','state','generation','offset','index','units','cats','origins']:
   altered=copy.deepcopy(point)
   if isinstance(altered[key],int):altered[key]+=1
   elif isinstance(altered[key],str):altered[key]+='changed'
   else:altered[key].append('changed')
   self.assertFalse(m.reusable(altered),key)
  first=m.next();m.__dict__=copy.deepcopy(point);self.assertEqual(m.next(),first)
  # Returning a category to its old value still invalidates generation/state cache.
  m.__dict__=copy.deepcopy(point);m.assign(64,11);m.assign(64,12);self.assertFalse(m.reusable(point))
 def test_origin_indices_and_non_authored_endline(self):
  prefix=[dict(source=1,occurrence=0,start=3,stop=7,role='definition',definition=-1,invocation=-1)]
  m=Mouth(b'a',source=3,occurrence=5,origins=prefix);t=m.next();self.assertEqual((t.source,t.occurrence,t.origin),(3,5,1))
  self.assertEqual(m.origins[0],prefix[0]);self.assertEqual(m.origins[1]['start'],0)
  e=m.next();self.assertEqual((e.provenance,e.origin,e.start,e.stop),(1,-1,1,1));self.assertEqual(len(m.origins),2)
 def test_no_preview_to_strict(self):
  t=tokens(b'}')[0];self.assertTrue(strict_token(t))
  recovery=dataclasses.replace(t,origin=-1,source=-1,occurrence=-1,provenance=2)
  with self.assertRaisesRegex(ValueError,'TEX_PREVIEW_TOKEN_FORBIDDEN'):strict_token(recovery)
 def test_installed_first_boundaries(self):
  expected=['ifnum','NeedsTeXFormat','ProvidesPackage']
  manifest=json.loads((H/'installed-sources.json').read_text())
  for row,name in zip(manifest['files'],expected):
   raw=Path(row['path']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256'])
   m=Mouth(raw)
   for _ in range(1000):
    t=m.next()
    if t.kind==2 and t.value!='par':break
   else:self.fail('first boundary not found')
   self.assertEqual(t.value,name);self.assertEqual(t.start,row['first_boundary']['startByte'])
   self.assertEqual(raw[t.start:t.stop],('\\'+name).encode())
   self.assertEqual(m.origins[t.origin]['start'],t.start)
 def test_installed_state_boundaries_no_execution(self):
  manifest=json.loads((H/'installed-sources.json').read_text())
  for row,expected in zip(manifest['files'],[['catcode','`','{'],['edef','@temp','{','catcode'],['expandafter','edef','csname']]):
   raw=Path(row['path']).read_bytes();m=Mouth(raw);m.offset=row['state_boundary']['startByte']
   if row['id']!='base/latex.ltx':m.assign(64,11)
   self.assertEqual([m.next().value for _ in expected],expected)
  raw=Path(manifest['files'][2]['path']).read_bytes();pos=raw.index(b'^^A')
  m=Mouth(raw);m.offset=pos
  with self.assertRaises(Diagnostic) as e:m.next()
  self.assertEqual((e.exception.code,e.exception.start),(2,pos))
if __name__=='__main__':unittest.main()
