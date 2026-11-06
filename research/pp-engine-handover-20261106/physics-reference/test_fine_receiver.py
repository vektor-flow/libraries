import unittest
import numpy as np
from fine_receiver_reference import capture_segments

class FineReceiverTests(unittest.TestCase):
 def test_thin_stroke_crossing_is_captured_where_the_actual_mask_exists(self):
  alpha=np.zeros((10,40));alpha[:,3]=1
  r=capture_segments(alpha,[[0,.5,.2]],[[1,.5,.2]],[.25],20,1,(1,1,1))
  self.assertTrue(r['captured'][0]);self.assertAlmostEqual(r['positions'][0,0],3.5/40,places=14)
  self.assertEqual(r['pixels'][0,1],3);self.assertEqual(r['exposure'][0],.25)
 def test_cell_overlap_never_absorbs_gas_outside_the_native_stroke(self):
  alpha=np.zeros((10,40));alpha[:,3]=1
  r=capture_segments(alpha,[[.025,.5,.2]],[[.025,.5,.2]],[.01],100,1,(1,1,1))
  self.assertFalse(r['captured'][0]);self.assertEqual(r['exposure'][0],0)
 def test_periodic_boundary_and_partition_preserve_the_same_interception(self):
  alpha=np.zeros((10,40));alpha[:,1]=1
  full=capture_segments(alpha,[[.9,.5,.2]],[[1.2,.5,.2]],[.25],20,1,(1,1,1));needed=.25;point=np.array([[.9,.5,.2]])
  for _ in range(10):
   r=capture_segments(alpha,point,point+np.array([[.03,0,0]]),[needed],20,.1,(1,1,1));needed-=r['exposure'][0];point=r['positions']
   if r['captured'][0]:break
  self.assertTrue(full['captured'][0]);self.assertTrue(r['captured'][0]);np.testing.assert_allclose(point,full['positions'],atol=1e-14,rtol=0)
 def test_a_crossing_budget_failure_is_explicit(self):
  with self.assertRaisesRegex(RuntimeError,'budget'):capture_segments(np.ones((10,40)),[[0,.5,.2]],[[20,.5,.2]],[10000],1,1,(1,1,1),max_segments=8)
 def test_creation_can_absorb_only_at_the_moving_wave_front(self):
  alpha=np.ones((10,40));r=capture_segments(alpha,[[.5,.5,.2]],[[.5,.5,.2]],[.5],9,1,(1,1,1),front=(.05,.95,.1))
  self.assertTrue(r['captured'][0]);self.assertAlmostEqual(r['fractions'][0],.5,places=14)
  r=capture_segments(alpha,[[.7,.5,.2]],[[.7,.5,.2]],[.01],100,1,(1,1,1),front=(0,.2,.05))
  self.assertFalse(r['captured'][0]);self.assertEqual(r['exposure'][0],0)
 def test_moving_front_partition_and_periodic_wrap_preserve_interception(self):
  alpha=np.ones((10,40));start=np.array([[.9,.5,.2]]);velocity=np.array([[.3,0,0]]);front=np.array([.03,.13,.08]);full=capture_segments(alpha,start,start+velocity,[.3],20,1,(1,1,1),front=front)
  point=start.copy();remaining=.3
  for i in range(10):
   edge=front[0]+(front[1]-front[0])*i/10;next_edge=front[0]+(front[1]-front[0])*(i+1)/10
   part=capture_segments(alpha,point,point+velocity/10,[remaining],20,.1,(1,1,1),front=(edge,next_edge,front[2]));remaining-=part['exposure'][0];point=part['positions']
   if part['captured'][0]:break
  self.assertTrue(full['captured'][0]);self.assertTrue(part['captured'][0]);np.testing.assert_allclose(point,full['positions'],atol=1e-14,rtol=0)

if __name__=='__main__':unittest.main()
