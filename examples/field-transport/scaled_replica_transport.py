"""Experimental replica candidate: normalize shape before blending and scale area.

Uniform geometry scaling replaces threshold erosion. Hole-free scalar unions are
filled before sampling. Sampled validation remains required.
"""
from functools import lru_cache
from scipy.optimize import brentq
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import reconstruction
from replica_transport import Group
from field_transport import clock

class ScaledGroup(Group):
 def __init__(self,source,targets,separation_power=1.):
  if len(source)!=1 or not targets or any(len(body)!=1 for body in targets):
   raise ValueError('Scaled replicas require nonempty hole-free endpoints')
  if separation_power not in [.5,1.,2.]:raise ValueError('Unsupported separation power')
  self.separation_power=separation_power
  super().__init__(source,targets)
 def separation_progress(self,t):
  p=self.separation_power
  return clock(t/(p+(1-p)*t))
 def raw(self,t,scale=1.):
  v=clock(t);fields=[]
  ea=np.ptp(self.source[0],axis=0)
  for target,body in zip(self.b,self.targets):
   eb=np.ptp(body[0],axis=0);extent=(1-v)*ea+v*eb
   u=self.separation_progress(t)
   at=(1-u)*self.a.center+u*target.center
   dx=(self.X-at[0])/scale;dy=(self.Y-at[1])/scale
   fa=self.a.sample(dx*ea[0]/extent[0]+self.a.center[0],dy*ea[1]/extent[1]+self.a.center[1],self.a.center)
   fb=target.sample(dx*eb[0]/extent[0]+target.center[0],dy*eb[1]/extent[1]+target.center[1],target.center)
   fields.append(scale*((1-v)*fa+v*fb))
  f=np.max(fields,axis=0)
  seed=np.full_like(f,f.max());seed[[0,-1],:]=f[[0,-1],:];seed[:,[0,-1]]=f[:,[0,-1]]
  return reconstruction(seed,f,method='erosion',footprint=ndi.generate_binary_structure(2,1))
 @lru_cache(maxsize=384)
 def coverage(self,t):
  if not 0<=t<=1:raise ValueError('Time outside [0,1]')
  v=clock(t);desired=(1-v)*self.area0+v*self.area1
  def residual(scale):return float(np.clip(self.raw(t,scale)+.5,0,1).sum()-desired)
  scale=brentq(residual,.15,2.,xtol=1e-9)
  coverage=np.clip(self.raw(t,scale)+.5,0,1)
  if abs(coverage.sum()-desired)>.01:raise ValueError('Scaled area calibration failed')
  if np.any(coverage[[0,-1],:]>.001) or np.any(coverage[:,[0,-1]]>.001):raise ValueError('Group exceeds its finite field region')
  return np.uint8(np.rint(255*coverage)),float(coverage.sum())
 def image(self,t):
  coverage,mass=self.coverage(float(t))
  out=np.zeros((720,1280),np.uint8);x,y=self.lo+[640,360];X,Y=self.hi+[640,360]
  out[y:Y,x:X]=coverage
  return out,mass
