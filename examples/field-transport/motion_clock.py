"""Shared, monotone timing for an already collision-checked cohort path.

The proxy follows endpoint centers plus the actual avoidance spline. It is not
an optical-flow or material-velocity estimate. All groups and topology events
must use the same remapping; retiming individual bodies invalidates clearance.
"""
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import brentq
from field_transport import clock


class MotionClock:
 def __init__(self,route):
  t=np.linspace(0,1,8193);u=clock(t)
  du=30*t*t*(1-t)**2;ddu=60*t*(1-t)*(1-2*t)
  delta=route.bounds[-1].mean(1)-route.bounds[0].mean(1)
  if hasattr(route,'progress_derivatives'):
   first,dd=route.progress_derivatives(u)
  else:
   axis=np.eye(2)[route.axis]
   first=route.spline(u,1)[:,:,None]*axis
   dd=route.spline(u,2)[:,:,None]*axis
  d=delta[None,:,:]+first
  velocity=d*du[:,None,None]
  acceleration=dd*du[:,None,None]**2+d*ddu[:,None,None]
  speed=np.linalg.norm(velocity,axis=2).max(1)
  accel=np.linalg.norm(acceleration,axis=2).max(1)
  self.before=dict(speed=float(speed.max()),acceleration=float(accel.max()))
  self.integral=None;self.after=self.before.copy();best=1.
  if speed.max()<1e-8:return
  # Both peak speed and peak acceleration must improve. Smooth positive density
  # gives a C2 inverse with finite endpoint rate: the original stationary
  # velocity/acceleration therefore survive without adding a second easing.
  for width in [.005,.01,.02,.04]:
   for weight in [1.,3.,10.]:
    density=speed+weight*np.sqrt(accel)
    density=gaussian_filter1d(density,width*(len(t)-1))+max(1.,.5*density.mean())
    rate=PchipInterpolator(t,density)
    integral=rate.antiderivative();total=float(integral(1)-integral(0))
    first=rate(t)/total;second=rate.derivative()(t)/total
    v=velocity/first[:,None,None]
    a=acceleration/first[:,None,None]**2-velocity*second[:,None,None]/first[:,None,None]**3
    after=dict(speed=float(np.linalg.norm(v,axis=2).max()),acceleration=float(np.linalg.norm(a,axis=2).max()))
    score=max(after[k]/self.before[k] for k in after)
    if score<best:
     best=score;self.integral=integral;self.total=total;self.after=after
     self.parameters=dict(width=width,weight=weight)
  # Avoid changing an already satisfactory trajectory for negligible benefit.
  if best>.95:self.integral=None;self.after=self.before.copy()
 def __call__(self,t):
  if not 0<=t<=1:raise ValueError('Time outside [0,1]')
  if self.integral is None or t in (0,1):return float(t)
  return float(brentq(lambda q:(self.integral(q)-self.integral(0))/self.total-t,0,1,xtol=1e-14))
