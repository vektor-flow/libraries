import unittest
from types import SimpleNamespace
import numpy as np
from scipy.interpolate import CubicSpline
from route_correction import CompositeRoute,TaperedRoute
from motion_clock import MotionClock
from field_transport import clock

class RouteCorrectionTests(unittest.TestCase):
 def test_two_axis_derivatives_and_stationary_endpoints(self):
  def base(axis,amount):
   spline=CubicSpline([0.,.5,1.],np.array([[0.],[amount],[0.]]),bc_type='clamped')
   return SimpleNamespace(axis=axis,spline=spline,bounds=np.zeros((2,1,2,2)),displacements=lambda t:spline(clock(t))[...,None]*np.eye(2)[axis])
  a=base(0,12.);b=base(1,-3.);taper=TaperedRoute(b,.025);route=CompositeRoute(a,taper)
  for u in [.02,.1,.4,.8]:
   h=1e-5;first,second=route.progress_derivatives(np.array([u]))
   f=lambda q:a.spline(q)[...,None]*[1,0]+b.spline(q)[...,None]*[0,1]*taper.envelope(q)[0]
   np.testing.assert_allclose(first[0],(f(u+h)-f(u-h))/(2*h),rtol=1e-6,atol=1e-5)
   np.testing.assert_allclose(second[0],(f(u+h)-2*f(u)+f(u-h))/h**2,rtol=1e-4,atol=1e-4)
  for t in [0.,1.]:np.testing.assert_array_equal(route.displacements(t),0.)
  self.assertLess(np.linalg.norm(route.displacements(1e-4)),1e-10)
  timing=MotionClock(route)
  self.assertGreater(timing.before['speed'],0.)
  self.assertTrue(np.all(np.diff([timing(t) for t in np.linspace(0,1,65)])>0))

if __name__=='__main__':unittest.main()
