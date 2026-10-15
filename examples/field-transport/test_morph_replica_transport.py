import unittest
import numpy as np
from morph_replica_transport import MorphGroup
from combined_transport import BodyPlan,topology
from field_transport import clock

class MorphReplicaTests(unittest.TestCase):
 def test_different_shapes_split_without_area_erosion(self):
  angle=np.linspace(0,2*np.pi,48,endpoint=False);p=22*np.c_[np.cos(angle),np.sin(angle)]
  square=np.array([[-20,-20],[20,-20],[20,20],[-20,20]],float)+[-65,0]
  triangle=np.array([[-24,20],[0,-24],[24,20]],float)+[65,0]
  g=MorphGroup([p],[[square],[triangle]],BodyPlan);counts=[]
  for t in np.linspace(0,1,33):
   im,m=g.image(float(t));n,h=topology(im>127);counts.append(n)
   self.assertEqual(h,0);self.assertIn(n,[1,2])
   self.assertAlmostEqual(m,(1-clock(t))*g.area0+clock(t)*g.area1,delta=.01)
  self.assertEqual(counts[0],1);self.assertEqual(counts[-1],2)
  self.assertTrue(np.all(np.diff(counts)>=0))

if __name__=='__main__':unittest.main()
