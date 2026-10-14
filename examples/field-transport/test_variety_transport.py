import unittest
import numpy as np
from field_transport import ring,topology,area
from scene_transport import draw_scene
from affine_transport import AffineTransport
from registered_transport import RegisteredTransport,rotation
from replica_transport import ReplicaScene,center
from plan_transport import plan_transport

def outline():
 t=np.linspace(0,2*np.pi,64,endpoint=False)
 r=70*(1+.12*np.cos(3*t)+.08*np.sin(2*t))
 return r[:,None]*np.c_[np.cos(t),np.sin(t)]

class VarietyTests(unittest.TestCase):
 def test_geometry_only_selection_prefers_affine_and_rejects_hole_creation(self):
  p=outline();name,plan=plan_transport([[p]],[[p@rotation(.7).T+[20,10]]])
  self.assertEqual(name,'affine')
  with self.assertRaises(ValueError):plan_transport([[p]],[ring(70,10)])
 def test_affine_inference_ignores_boundary_phase_and_orientation(self):
  a=[outline()];m=np.array([[1.3,.4],[.15,.85]])
  b=[np.roll((a[0]@m.T+[40,-30])[::-1],13,axis=0)]
  p=AffineTransport(a,b)
  np.testing.assert_allclose(p.matrix,m,atol=1e-10)
  values=[area(p.contours(float(t))[0]) for t in np.linspace(0,1,21)]
  self.assertTrue(np.all(np.diff(values)>0))
  for t in [0,1]:
   end=p.contours(t)[0]
   d=lambda e:np.linalg.norm(p.contours(t+e if t==0 else t-e)[0]-end)
   self.assertLess(d(.001),.002*d(.01))
 def test_affine_rejects_nonaffine_shape(self):
  a=outline();b=a.copy();b[5]+=[5,3]
  with self.assertRaises(ValueError):AffineTransport([a],[b])
 def test_registered_two_holes_rotate_without_colliding(self):
  outer=ring(105,20)[0]*[1.5,1]
  hole=ring(28,8)[0]
  a=[outer,hole+[-65,0],hole+[65,0]]
  b=[p@rotation(1.2).T for p in a]
  plan=RegisteredTransport(a,b)
  for t in np.linspace(0,1,17):
   self.assertEqual(topology(draw_scene([plan.contours(float(t))])>127),(1,2))
 def test_replica_nearly_identical_bars_keep_spatial_order(self):
  def bar(y,w):return [np.array([[-w/2,y-8],[w/2,y-8],[w/2,y+8],[-w/2,y+8]])]
  a=[bar(-40,240),bar(40,240.1)]
  b=[bar(-80,240.1),bar(0,240),bar(80,240.1)]
  plan=ReplicaScene(a,b)
  counts=[]
  for t in np.linspace(0,1,25):
   im,_=plan.image(float(t));n,h=topology(im>127);counts.append(n);self.assertEqual(h,0)
  self.assertEqual((counts[0],counts[-1]),(2,3));self.assertTrue(np.all(np.diff(counts)>=0))
 def test_replica_generated_shapes_and_reverse_have_continuous_area(self):
  for angle in [0,.65]:
   p=outline()@rotation(angle).T;a=[[p]];b=[[p*.7+[-110,-15]],[p*.7+[110,15]]]
   plan=ReplicaScene(a,b);reverse=ReplicaScene(b,a);counts=[];masses=[]
   for t in np.linspace(0,1,17):
    im,mass=plan.image(float(t));other,_=reverse.image(float(1-t));np.testing.assert_array_equal(im,other)
    n,h=topology(im>127);counts.append(n);self.assertEqual(h,0);masses.append(sum(mass))
   self.assertEqual((counts[0],counts[-1]),(1,2));self.assertTrue(np.all(np.diff(counts)>=0))
   self.assertTrue(np.all(np.diff(masses)<=.02))

if __name__=='__main__':unittest.main()
