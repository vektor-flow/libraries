import unittest
import numpy as np
from combined_transport import CombinedScene,ProfileTransport,BodyPlan
from field_transport import area,clock,topology
from scene_transport import draw_scene
from test_variety_transport import outline

class CombinedTests(unittest.TestCase):
 def test_profiles_follow_endpoint_geometry_and_keep_area(self):
  x=np.linspace(-180,180,128)
  def ribbon(y):return [np.vstack([np.c_[x,y-4],np.c_[x[::-1],(y+4)[::-1]]])]
  a,b=ribbon(x*x/500),ribbon(x**3/100000)
  plan=ProfileTransport(a,b)
  for t in np.linspace(0,1,13):
   p=plan.contours(t)[0];self.assertAlmostEqual(abs(area(p)),2880,places=3)
   self.assertEqual(topology(draw_scene([[p]],ss=8)>127),(1,0))
  for t in [0,1]:
   p=plan.contours(t)[0];q=plan.contours(t+.001 if t==0 else t-.001)[0]
   self.assertLess(np.max(abs(p-q)),.0001)
 def test_compound_split_and_affine_reverse(self):
  p=outline()*.5;q=outline()*.4
  a=[[p+[-200,0]],[q+[220,0]]]
  b=[[p*.65+[-250,0]],[p*.65+[-150,0]],[q@np.array([[1.2,.3],[0,.8]]).T+[220,0]]]
  forward=CombinedScene(a,b);reverse=CombinedScene(b,a);counts=[]
  self.assertEqual([kind for kind,_ in forward.groups],['replica','affine'])
  for t in np.linspace(0,1,13):
   ims,m=forward.images(t);other,_=reverse.images(1-t)
   np.testing.assert_array_equal(np.max(ims,axis=0),np.max(other,axis=0))
   counts.append(sum(x[0] for x in m))
  self.assertTrue(np.all(np.diff(counts)>=0));self.assertEqual((counts[0],counts[-1]),(2,3))
 def test_open_stroke_generated_curves_preserve_mass_and_endpoints(self):
  from stroke_transport import StrokeTransport
  x=np.linspace(-75,75,96)
  def stroke(y):
   p=np.c_[x,y];d=np.gradient(p,axis=0);n=np.c_[-d[:,1],d[:,0]];n/=np.linalg.norm(n,axis=1)[:,None]
   return [np.vstack([p+4*n,(p-4*n)[::-1]])]
  a,b=stroke(18*np.sin(x/35)),stroke(25*np.cos(x/45))
  plan=StrokeTransport(a,b)
  for t in np.linspace(0,1,9):
   im,mass=plan.image(t);self.assertEqual(topology(im>127),(1,0))
   self.assertAlmostEqual(mass,(1-clock(t))*plan.area0+clock(t)*plan.area1,places=2)
  for t,want in [(0,a),(1,b)]:
   im,_=plan.image(t);truth=draw_scene([want],ss=8)>127;mask=im>127
   self.assertGreater((mask&truth).sum()/(mask|truth).sum(),.95)
 def test_cropped_topology_matches_full_frame(self):
  from combined_transport import topology as cropped
  rng=np.random.default_rng(81)
  for density in [.1,.4,.7,.95]:
   for _ in range(20):
    mask=rng.random((21,33))<density
    self.assertEqual(cropped(mask),topology(mask))
  self.assertEqual(cropped(np.zeros((10,10),bool)),(0,0))
 def test_affine_precedes_nonrigid(self):
  p=outline();plan=BodyPlan([p],[p@np.array([[1.1,.2],[0,.9]]).T])
  self.assertEqual(plan.kind,'affine')
 def test_unsupported_hole_event_rejected(self):
  p=outline()
  with self.assertRaises(ValueError):CombinedScene([[p]],[[p,p*.4]])
if __name__=='__main__':unittest.main()
