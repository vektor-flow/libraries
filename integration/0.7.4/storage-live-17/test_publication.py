"""Bounded isolated tests of the exact publication primitive; no operational paths."""
import json,os,pathlib,resource,tempfile,time,unittest
from unittest.mock import patch
import publication as p
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
class Publication(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='publication-isolated-',dir=p.OUT)
  self.root=pathlib.Path(self.temp.name);self.op=self.root/'owners.json'
  self.old=b'{"workers":{"A":"old","F":"old"}}\n';self.op.write_bytes(self.old);self.op.chmod(0o400)
  self.desired={'workers':{'A':'old','F':'new'}};self.events=[]
 def tearDown(self):self.temp.cleanup()
 def publish(self):return p.atomic_publish(self.op,self.old,self.desired,lambda a,b:self.events.append((a,b)) or dict(before=a.hex(),after=b.hex()))
 def test_success(self):
  r=self.publish();self.assertEqual(self.op.read_bytes().hex(),r['after']);self.assertEqual(json.loads(self.op.read_bytes()),self.desired)
  self.assertEqual(self.op.stat().st_mode&0o777,0o400);self.assertEqual(len(self.events),1);self.assertEqual(list(self.root.iterdir()),[self.op])
 def test_stale_bytes(self):
  self.old=b'wrong';self.assertRaises(AssertionError,self.publish);self.assertEqual(self.events,[])
 def test_symlink_file(self):
  target=self.root/'target';self.op.rename(target);self.op.symlink_to(target)
  self.assertRaises(OSError,self.publish);self.assertEqual(target.read_bytes(),self.old)
 def test_symlink_parent(self):
  link=self.root/'link';link.symlink_to(self.root,target_is_directory=True);self.op=link/'owners.json'
  self.assertRaises(OSError,self.publish)
 def test_writable_parent(self):
  self.root.chmod(0o770);self.assertRaises(AssertionError,self.publish);self.assertEqual(self.events,[]);self.root.chmod(0o700)
 def test_writable_file(self):
  self.op.chmod(0o660);self.assertRaises(AssertionError,self.publish);self.assertEqual(self.events,[])
 def test_hardlink(self):
  os.link(self.op,self.root/'alias');self.assertRaises(AssertionError,self.publish);self.assertEqual(self.events,[])
 def test_before_publish_failure(self):
  def fail(*a):raise RuntimeError('isolated intent failure')
  self.assertRaises(RuntimeError,p.atomic_publish,self.op,self.old,self.desired,fail)
  self.assertEqual(self.op.read_bytes(),self.old);self.assertEqual(list(self.root.iterdir()),[self.op])
 def test_replace_failure_no_retry(self):
  with patch.object(p.os,'replace',side_effect=OSError('isolated replace failure')) as replace:
   self.assertRaises(OSError,self.publish);self.assertEqual(replace.call_count,1)
  self.assertEqual(self.op.read_bytes(),self.old);self.assertEqual(len(self.events),1)
 def test_exclusive_temp_collision(self):
  class Id:hex='collision'
  f=self.root/'.owners-live17-collision.tmp';f.write_bytes(b'preserve')
  with patch.object(p.uuid,'uuid4',return_value=Id()):self.assertRaises(FileExistsError,self.publish)
  self.assertEqual(f.read_bytes(),b'preserve');self.assertEqual(self.op.read_bytes(),self.old)
start=time.monotonic();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Publication)
result=unittest.TextTestRunner(verbosity=2).run(suite)
p.save('publication-tests.json',dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),success=result.wasSuccessful(),seconds=time.monotonic()-start,operational_paths_written=False))
raise SystemExit(not result.wasSuccessful())
