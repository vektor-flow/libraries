"""Smooth local corrections to an existing, independently validated route."""
import numpy as np
from field_transport import clock


def derivatives(route,u):
 if hasattr(route,'progress_derivatives'):return route.progress_derivatives(u)
 axis=np.eye(2)[route.axis]
 return route.spline(u,1)[...,None]*axis,route.spline(u,2)[...,None]*axis


class CompositeRoute:
 def __init__(self,base,correction):
  self.base=base;self.correction=correction;self.bounds=base.bounds
 def displacements(self,t):return self.base.displacements(t)+self.correction.displacements(t)
 def progress_derivatives(self,u):
  a,b=derivatives(self.base,u);c,d=derivatives(self.correction,u)
  return a+c,b+d


class TaperedRoute:
 """Fade a correction near endpoints, where coarse pooling can invent contact."""
 def __init__(self,route,width=.1):
  if not 0<width<.5:raise ValueError('Taper width must be inside (0, .5)')
  self.route=route;self.width=width;self.bounds=route.bounds
 def envelope(self,u):
  u=np.asarray(u);z=np.minimum(1.,np.minimum(u,1-u)/self.width)
  dz=np.where(u<self.width,1/self.width,np.where(u>1-self.width,-1/self.width,0.))
  return clock(z),30*z*z*(1-z)**2*dz,60*z*(1-z)*(1-2*z)*dz*dz
 def displacements(self,t):return self.route.displacements(t)*self.envelope(clock(t))[0]
 def progress_derivatives(self,u):
  w,dw,ddw=self.envelope(u);first,second=derivatives(self.route,u)
  value=self.route.spline(u)[...,None]*np.eye(2)[self.route.axis]
  return (w[...,None,None]*first+dw[...,None,None]*value,
          w[...,None,None]*second+2*dw[...,None,None]*first+ddw[...,None,None]*value)


