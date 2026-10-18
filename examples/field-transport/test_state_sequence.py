import unittest
import numpy as np
from scipy import ndimage as ndi
from state_sequence import StateSequence
from scene_transport import draw_scene
from combined_transport import topology

class StateSequenceTests(unittest.TestCase):
 def states(self):
  a=np.linspace(0,2*np.pi,64,endpoint=False);disc=16*np.c_[np.cos(a),np.sin(a)]
  return [[[disc]],[[disc+[-30,0]],[disc+[30,0]]],[[disc+[-60,0]],[disc],[disc+[60,0]]]]
 def test_same_algorithm_carries_every_key_state(self):
  states=self.states();plan=StateSequence(states)
  for t,state in enumerate(states):
   im=plan.image(t)>127;truth=draw_scene(state,ss=8)>127
   self.assertFalse(np.any(im&~ndi.binary_dilation(truth)))
   self.assertFalse(np.any(ndi.binary_erosion(truth)&~im))
   self.assertEqual(topology(im),(len(state),0))
  for t in np.linspace(0,2,17):
   im=plan.image(float(t));self.assertEqual(im.shape,(720,1280));self.assertEqual(im.dtype,np.uint8)
 def test_domain_and_deterministic_replay(self):
  plan=StateSequence(self.states())
  np.testing.assert_array_equal(plan.image(.4),plan.image(.4))
  for t in [-.1,2.1,np.nan]:
   with self.assertRaises(ValueError):plan.image(t)
  with self.assertRaises(ValueError):StateSequence([[]])

if __name__=='__main__':unittest.main()
