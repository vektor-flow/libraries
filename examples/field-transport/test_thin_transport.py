import unittest
import numpy as np
from scipy import ndimage as ndi
from thin_transport import ThinTreeTransport,stroke_width
from thin_event_transport import ThinEventPlan
from conservative_thin_transport import ConservativeThinTransport
from combined_transport import topology
from scene_transport import draw_scene
from field_transport import clock


def arc(start,end,radius=45,width=8):
 theta=np.linspace(start,end,128)
 outer=(radius+width/2)*np.c_[np.cos(theta),np.sin(theta)]
 inner=(radius-width/2)*np.c_[np.cos(theta[::-1]),np.sin(theta[::-1])]
 return [np.vstack([outer,inner])]


class ThinTransportTests(unittest.TestCase):
 def test_equal_area_rotation_keeps_constant_ink(self):
  a=[np.array([[-45.,-4.],[45.,-4.],[45.,4.],[-45.,4.]])]
  b=[p@np.array([[0.,-1.],[1.,0.]]) for p in a]
  plan=ConservativeThinTransport(a,b)
  self.assertAlmostEqual(plan.areas[0],plan.areas[1],places=5)
  for t in np.linspace(0,1,17):
   im,mass=plan.image(float(t))
   self.assertAlmostEqual(mass,plan.areas[0],places=2)
   self.assertEqual(topology(im>127),(1,0))
   self.assertLessEqual(stroke_width(im),10.)
 def test_branch_to_curve_preserves_thickness_and_endpoints(self):
  a=[np.array([[-60,-4],[-4,-4],[-4,-60],[4,-60],[4,-4],[60,-4],[60,4],[4,4],[4,60],[-4,60],[-4,4],[-60,4]],float)]
  b=arc(-1.3,1.3,60)
  plan=ThinTreeTransport(a,b,frame_weight=0.)
  limit=max(stroke_width(plan.image(t)[0]) for t in [0.,1.])+2
  for t in np.linspace(0,1,65):
   im,_=plan.image(float(t));self.assertEqual(topology(im>127),(1,0))
   self.assertLessEqual(stroke_width(im),limit)
   if t in [0,1]:
    truth=draw_scene([a if t==0 else b],ss=8)>127;actual=im>127
    self.assertFalse(np.any(actual&~ndi.binary_dilation(truth)))
    self.assertFalse(np.any(ndi.binary_erosion(truth)&~actual))
  for t in [-.1,1.1]:
   with self.assertRaises(ValueError):plan.image(t)
 def test_thin_open_arc_closes_without_a_solid_intermediate(self):
  theta=np.linspace(0,2*np.pi,128,endpoint=False);unit=np.c_[np.cos(theta),np.sin(theta)]
  a=arc(.25,2*np.pi-.25);b=[49*unit,41*unit]
  plan=ThinEventPlan(a,b)
  previous=0;areas=[]
  self.assertLess(plan.event_time,.6)
  for t in np.linspace(0,1,65):
   im,mass=plan.image(float(t));n,h=topology(im>127)
   areas.append(mass)
   expected=(1-clock(float(t)))*plan.plan.areas[0]+clock(float(t))*plan.plan.areas[1]
   self.assertAlmostEqual(mass,expected,places=2)
   self.assertEqual(n,1);self.assertGreaterEqual(h,previous);previous=h
   self.assertLessEqual(stroke_width(im),plan.width_limit)
  self.assertEqual(previous,1)
  self.assertTrue(np.all(np.diff(areas)>=-.01))
  # The same accepted geometry supports removal without a second shape path.
  plan.reverse=True
  for t in [.0,.25,.5,.75,1.]:
   im,mass=plan.image(t)
   self.assertEqual(topology(im>127),(1,plan.expected_holes(t)))
   expected=(1-clock(1-t))*plan.plan.areas[0]+clock(1-t)*plan.plan.areas[1]
   self.assertAlmostEqual(mass,expected,places=2)
 def test_multiple_hole_event_is_explicitly_outside_thin_candidate(self):
  theta=np.linspace(0,2*np.pi,64,endpoint=False);unit=np.c_[np.cos(theta),np.sin(theta)]
  with self.assertRaisesRegex(ValueError,'zero-to-one'):
   ThinEventPlan([50*unit],[50*unit,10*unit-[20,0],10*unit+[20,0]])


if __name__=='__main__':unittest.main()
