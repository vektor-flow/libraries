import unittest
import numpy as np
from field_transport import ring,topology,clock
from scene_transport import Scene,draw_scene
from division_field import division,start_area,end_area
from rigid_routes import RoutedScene

class SceneTests(unittest.TestCase):
 def test_translation_keeps_contours_rigid(self):
  a=[ring(40,12)];b=[[p+[140,35] for p in a[0]]];scene=Scene(a,b)
  self.assertTrue(scene.parts[0][3])
  for t in [.1,.5,.9]:
   loops=scene.contours(t)[0]
   for p,q in zip(scene.contours(0)[0],loops):np.testing.assert_allclose(q-p,np.tile(clock(t)*np.array([140,35]),(len(p),1)),atol=1e-7)
   self.assertEqual(topology(draw_scene([loops])>127),(1,1))
 def test_exact_shapes_win_over_shorter_wrong_shape_assignments(self):
  square=np.array([[-25,-25],[25,-25],[25,25],[-25,25]])
  triangle=np.array([[-25,-25],[25,-25],[0,25]])
  a=[[square+[-350,0]],[triangle+[350,0]]]
  b=[[triangle+[-350,0]],[square+[350,0]]]
  scene=Scene(a,b,exact_first=True)
  self.assertTrue(all(p[3] for p in scene.parts))
  self.assertGreater(scene.parts[0][2][0],300)
 def test_routing_keeps_holes_and_separates_exchanging_bodies(self):
  a=[[p+[-100,0] for p in ring(30,10)],[p+[100,0] for p in ring(40,12)]]
  b=[[p+[100,0] for p in ring(30,10)],[p+[-100,0] for p in ring(40,12)]]
  scene=RoutedScene(a,b)
  for t in np.linspace(0,1,41):
   self.assertEqual(topology(draw_scene(scene.contours(float(t)))>127),(2,2))
  for t in [1e-4,1-1e-4]:
   anchor=0 if t<.5 else 1
   self.assertLess(max(np.max(abs(p-q)) for a,b in zip(scene.contours(t),scene.contours(anchor)) for p,q in zip(a,b)),1e-6)
 def test_vertical_exchange_uses_transverse_route(self):
  a=[[p+[0,-100] for p in ring(30,10)],[p+[0,100] for p in ring(40,12)]]
  b=[[p+[0,100] for p in ring(30,10)],[p+[0,-100] for p in ring(40,12)]]
  scene=RoutedScene(a,b)
  self.assertEqual(scene.axis,0)
  for t in np.linspace(0,1,41):
   self.assertEqual(topology(draw_scene(scene.contours(float(t)))>127),(2,2))
 def test_routing_rejects_overlapping_endpoints(self):
  with self.assertRaises(ValueError):RoutedScene([ring(30,10),ring(40,12)],[ring(30,10),ring(40,12)])
 def test_full_planar_search_handles_rotated_crossing_layout(self):
  from stress_transport import generated
  angle=float(np.random.default_rng(7104).uniform(0,np.pi))
  a,b=generated(104,4,angle,True);scene=RoutedScene(a,b)
  self.assertIsNone(scene.axis)
  for t in np.linspace(0,1,21):
   self.assertEqual(topology(draw_scene(scene.contours(float(t)),ss=8)>127),scene.expected)
 def test_target_list_order_does_not_supply_correspondence(self):
  from stress_transport import generated
  a,b=generated(7,4,np.pi/4);b=[b[i] for i in [2,0,3,1]]
  scene=RoutedScene(a,b)
  self.assertTrue(all(part[3] for part in scene.parts))
  for t in np.linspace(0,1,21):
   self.assertEqual(topology(draw_scene(scene.contours(float(t)),ss=8)>127),scene.expected)
 def test_count_mismatch_is_rejected(self):
  with self.assertRaises(ValueError):Scene([ring(40,12)],[ring(40,12),[p+[120,0] for p in ring(40,12)]])
 def test_division_is_monotone_and_coverage_changes_continuously(self):
  counts=[]
  for t in np.linspace(0,1,41):
   im,mass=division(float(t));count,holes=topology(im>127);counts.append(count)
   self.assertEqual(holes,0);self.assertAlmostEqual(mass,(1-clock(t))*start_area+clock(t)*end_area,delta=.003)
  self.assertEqual((counts[0],counts[-1]),(1,2));self.assertTrue(np.all(np.diff(counts)>=0))

if __name__=='__main__':unittest.main()
