import unittest
import numpy as np
from scipy import ndimage as ndi
from tree_transport import TreeTransport
from combined_transport import topology
from scene_transport import draw_scene
from field_transport import clock


class TreeTests(unittest.TestCase):
 def test_attached_branch_grows_without_fragmentation_and_preserves_area(self):
  a=[np.array([[-8,-80],[8,-80],[8,80],[-8,80]],float)]
  b=[np.array([[-8,-80],[8,-80],[8,-8],[70,-8],[70,8],[8,8],[8,80],[-8,80]],float)]
  plan=TreeTransport(a,b,frame_weight=0.)
  self.assertEqual([len(p) for p in plan.branches],[0,1])
  for t in np.linspace(0,1,65):
   im,mass=plan.image(float(t));self.assertEqual(topology(im>127),(1,0))
   self.assertAlmostEqual(mass,(1-clock(t))*plan.area0+clock(t)*plan.area1,places=2)
   if t in [0,1]:
    truth=draw_scene([a if t==0 else b],ss=8)>127;mask=im>127
    self.assertFalse(np.any(mask&~ndi.binary_dilation(truth)))
    self.assertFalse(np.any(ndi.binary_erosion(truth)&~mask))
 def test_closed_or_hole_topology_is_rejected(self):
  from field_transport import ring
  with self.assertRaises(ValueError):TreeTransport(ring(80,15),ring(90,15))
 def test_frame_weight_is_bounded(self):
  with self.assertRaises(ValueError):TreeTransport([],[],frame_weight=2.)


if __name__=='__main__':unittest.main()
