import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from scipy.interpolate import CubicSpline
from motion_clock import MotionClock
from field_transport import clock
from validated_transport import ValidatedCombinedScene
from combined_transport import CombinedScene


class MotionClockTests(unittest.TestCase):
 def route(self):
  u=np.linspace(0,1,101)
  offset=100*np.exp(-((u-.9)/.025)**2);offset[0]=offset[-1]=0
  return SimpleNamespace(axis=1,bounds=np.array([[[[0,0],[10,10]]],[[[300,0],[310,10]]]]),spline=CubicSpline(u,offset[:,None],bc_type=((1,[0]),(1,[0]))))
 def test_sharp_detour_slows_without_changing_path_or_duration(self):
  route=self.route();timing=MotionClock(route)
  self.assertIsNotNone(timing.integral)
  t=np.linspace(0,1,20001);q=np.array([timing(float(v)) for v in t])
  self.assertEqual(q[0],0);self.assertEqual(q[-1],1)
  self.assertTrue(np.all(np.diff(q)>0))
  def positions(v):return np.c_[300*clock(v),route.spline(clock(v))[:,0]]
  def peaks(p):
   vel=np.gradient(p,t,axis=0);acc=np.gradient(vel,t,axis=0)
   return np.linalg.norm(vel,axis=1).max(),np.linalg.norm(acc,axis=1).max()
  before=peaks(positions(t));after=peaks(positions(q))
  self.assertLess(after[0],.95*before[0]);self.assertLess(after[1],.95*before[1])
  # Stationary velocity AND acceleration: displacement decays cubically.
  for end in [0,1]:
   distance=lambda e:np.linalg.norm(positions(np.array([timing(abs(end-e))]))-positions(np.array([end])))
   self.assertLess(distance(1e-5),.002*distance(1e-4))
 def test_stationary_route_and_invalid_time(self):
  route=self.route();route.bounds[:]=route.bounds[0];route.spline=CubicSpline([0,1],[[0],[0]])
  timing=MotionClock(route)
  self.assertIsNone(timing.integral);self.assertEqual(timing(.3),.3)
  for t in [-.1,1.1,float('nan')]:
   with self.assertRaises(ValueError):timing(t)
 def test_retiming_rejection_keeps_original_route(self):
  scene=object.__new__(ValidatedCombinedScene);scene.cohort_route=self.route()
  route=scene.cohort_route
  with patch.object(scene,'images',side_effect=ValueError('New sample collided')):
   scene.prepare_motion()
  self.assertIsNone(scene.motion_clock)
  self.assertEqual(scene.motion_rejection,'New sample collided')
  self.assertIs(scene.cohort_route,route)
  self.assertEqual(scene.scene_time(.3),.3)
 def test_images_and_hole_events_share_one_clock_in_both_directions(self):
  scene=object.__new__(ValidatedCombinedScene);scene.cohort_route=None
  scene.motion_clock=lambda t:t*t
  scene.groups=[('event',SimpleNamespace(expected_holes=lambda t:int(t>.5)))]
  for reverse in [False,True]:
   scene.reverse=reverse
   with patch.object(CombinedScene,'images',return_value=('images','metrics')) as render:
    self.assertEqual(scene.images(.6),('images','metrics'))
    render.assert_called_once_with(.36,validate=True)
   self.assertEqual(scene.expected_holes_at(.6),int((1-.36 if reverse else .36)>.5))


if __name__=='__main__':unittest.main()
