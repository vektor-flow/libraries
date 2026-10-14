import unittest
import numpy as np
from field_transport import ring,topology,clock
from scene_transport import Scene,draw_scene
from division_field import division,start_area,end_area

class SceneTests(unittest.TestCase):
 def test_translation_keeps_contours_rigid(self):
  a=[ring(40,12)];b=[[p+[140,35] for p in a[0]]];scene=Scene(a,b)
  self.assertTrue(scene.parts[0][3])
  for t in [.1,.5,.9]:
   loops=scene.contours(t)[0]
   for p,q in zip(scene.contours(0)[0],loops):np.testing.assert_allclose(q-p,np.tile(clock(t)*np.array([140,35]),(len(p),1)),atol=1e-7)
   self.assertEqual(topology(draw_scene([loops])>127),(1,1))
 def test_count_mismatch_is_rejected(self):
  with self.assertRaises(ValueError):Scene([ring(40,12)],[ring(40,12),[p+[120,0] for p in ring(40,12)]])
 def test_division_is_monotone_and_coverage_changes_continuously(self):
  counts=[]
  for t in np.linspace(0,1,41):
   im,mass=division(float(t));count,holes=topology(im>127);counts.append(count)
   self.assertEqual(holes,0);self.assertAlmostEqual(mass,(1-clock(t))*start_area+clock(t)*end_area,delta=.003)
  self.assertEqual((counts[0],counts[-1]),(1,2));self.assertTrue(np.all(np.diff(counts)>=0))

if __name__=='__main__':unittest.main()
