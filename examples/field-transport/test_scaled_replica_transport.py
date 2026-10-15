import unittest
import numpy as np
from scipy import ndimage as ndi
from scaled_replica_transport import ScaledGroup
from combined_transport import topology
from scene_transport import draw_scene
from field_transport import clock

class ScaledReplicaTests(unittest.TestCase):
 def test_thin_branched_copies_keep_area_and_connectivity(self):
  w=3.;r=35.
  p=np.array([[-w,-r],[w,-r],[w,-w],[r,-w],[r,w],[w,w],[w,r],[-w,r],[-w,w],[-r,w],[-r,-w],[-w,-w]])
  c,s=np.cos(.55),np.sin(.55);p=p@np.array([[c,-s],[s,c]]).T
  a=[p];b=[[p*.75+[-70,-12]],[p*1.15+[70,12]]]
  group=ScaledGroup(a,b);counts=[]
  for t in np.linspace(0,1,33):
   im,mass=group.image(float(t));n,h=topology(im>127);counts.append(n)
   self.assertEqual(h,0);self.assertIn(n,[1,2])
   self.assertAlmostEqual(mass,(1-clock(t))*group.area0+clock(t)*group.area1,delta=.01)
   if t in [0,1]:
    truth=draw_scene([a] if t==0 else b,ss=8)>127;actual=im>127
    self.assertFalse(np.any(actual&~ndi.binary_dilation(truth)))
    self.assertFalse(np.any(ndi.binary_erosion(truth)&~actual))
  self.assertTrue(np.all(np.diff(counts)>=0))
 def test_separation_clocks_keep_stationary_velocity_and_acceleration(self):
  q=np.array([[-15,-15],[15,-15],[15,15],[-15,15]],float)
  for power in [.5,1.,2.]:
   g=ScaledGroup([q],[[q+[-40,0]],[q+[40,0]]],separation_power=power)
   self.assertEqual(g.separation_progress(0),0)
   self.assertEqual(g.separation_progress(1),1)
   self.assertLess(g.separation_progress(.001),.002*g.separation_progress(.01))
   self.assertLess(1-g.separation_progress(.999),.002*(1-g.separation_progress(.99)))
 def test_invalid_time_and_holes_rejected(self):
  q=np.array([[-15,-15],[15,-15],[15,15],[-15,15]],float)
  with self.assertRaises(ValueError):ScaledGroup([q,q*.3],[[q]])
  g=ScaledGroup([q],[[q+[-30,0]],[q+[30,0]]])
  for t in [-.1,1.1]:
   with self.assertRaises(ValueError):g.image(t)

if __name__=='__main__':unittest.main()
