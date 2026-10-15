import unittest
import numpy as np
from scipy import ndimage as ndi
from hole_event_transport import HoleEventPlan
from combined_transport import BodyPlan,topology
from scene_transport import draw_scene

class HoleEventTests(unittest.TestCase):
 def test_open_and_close_two_disjoint_holes(self):
  angle=np.linspace(0,2*np.pi,96,endpoint=False);unit=np.c_[np.cos(angle),np.sin(angle)]
  a=[80*unit];b=[80*unit,13*unit+[-30,0],18*unit+[30,0]]
  forward=HoleEventPlan(a,b,BodyPlan);reverse=HoleEventPlan(b,a,BodyPlan);counts=[]
  for t in np.linspace(0,1,65):
   im,_=forward.image(float(t));other,_=reverse.image(float(1-t))
   np.testing.assert_array_equal(im,other)
   n,h=topology(im>127);self.assertEqual(n,1);counts.append(h)
   self.assertEqual(h,forward.expected_holes(t))
   if t in [0,1]:
    truth=draw_scene([a if t==0 else b],ss=8)>127;actual=im>127
    self.assertFalse(np.any(actual&~ndi.binary_dilation(truth)))
    self.assertFalse(np.any(ndi.binary_erosion(truth)&~actual))
  self.assertEqual(counts[0],0);self.assertEqual(counts[-1],2)
  self.assertTrue(np.all(np.diff(counts)>=0))
 def test_hole_touching_exterior_rejected(self):
  q=np.array([[-30,-30],[30,-30],[30,30],[-30,30]],float)
  plan=HoleEventPlan([q],[q,q*.5+[25,0]],BodyPlan)
  with self.assertRaisesRegex(ValueError,'touches exterior'):plan.image(1.)

if __name__=='__main__':unittest.main()
