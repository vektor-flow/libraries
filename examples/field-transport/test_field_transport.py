import unittest
import numpy as np
from field_transport import Atlas,Transport,ring,raster,topology,area,crossings
class FieldTests(unittest.TestCase):
 def test_atlas_alpha_is_distance_not_opacity_or_rgb(self):
  import tempfile,gzip,json
  from pathlib import Path
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);data=np.zeros((2,2,4),np.uint8);data[:,:,3]=[[0,255],[64,192]]
   (p/'atlas.rgba.gz').write_bytes(gzip.compress(data.tobytes()))
   (p/'typing-data.json').write_text(json.dumps(dict(atlasSize=[2,2],range=8,tiles={'display/X':dict(uv=[0,0,1,1])})))
   f=Atlas(p).field('display/X');self.assertEqual(f[0,0],-4);self.assertEqual(f[0,1],4)
   self.assertLess(f[1,0],0);self.assertGreater(f[1,1],0)

 def test_hole_and_area_through_nonuniform_deformation(self):
  a=ring(100,20);b=[p*np.array([.8,1.3])+[15,0] for p in a];p=Transport(a,b)
  areas=[]
  for t in np.linspace(0,1,41):
   loops=p.contours(t);self.assertEqual(topology(raster(loops,320)>127),(1,1));self.assertFalse(crossings(*loops));areas.append(area(loops[0])-area(loops[1]))
  self.assertTrue(np.all(np.diff(areas)>=-1e-8))
 def test_endpoint_motion_ramps(self):
  p=Transport(ring(100,20),[x*[.8,1.3] for x in ring(100,20)])
  for t in [0,1]:
   endpoint=p.contours(t)[0]
   d=lambda e:np.linalg.norm(p.contours(t+e if t==0 else t-e)[0]-endpoint)
   self.assertLess(d(.001),.002*d(.01))
 def test_topology_change_rejected(self):
  with self.assertRaises(ValueError):Transport(ring(),ring()[:1])
 def test_crossing_detection(self):
  self.assertTrue(crossings(np.array([[0,0],[2,2],[0,2],[2,0]]),np.array([[0,0],[2,2],[0,2],[2,0]]),True))
if __name__=='__main__':unittest.main()
