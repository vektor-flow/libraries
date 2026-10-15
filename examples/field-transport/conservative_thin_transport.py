"""Preserve ink area by adjusting medial length, while retaining local radii.

The prescribed quintic area is solved on the continuous coverage field, after
small-cavity filtering. Shape formation can precede translation/area progress;
all clocks have stationary endpoint velocity and acceleration. Independent
width, topology, endpoint and scene checks must still accept this candidate.
"""
import numpy as np
from scipy.optimize import brentq
from scipy.spatial.distance import cdist
from skimage.morphology import area_closing
from thin_transport import ThinTreeTransport
from field_transport import clock

class ConservativeThinTransport(ThinTreeTransport):
 def __init__(self,a,b,frame_weight=0.,rate=1.,min_cavity_area=0):
  super().__init__(a,b,frame_weight=frame_weight)
  if rate<=0:raise ValueError("Positive shape rate required")
  self.rate=rate;self.min_cavity_area=min_cavity_area
  self.areas=[ThinTreeTransport.image(self,t)[1] for t in [0.,1.]]
 def local_tube(self,path,radius):
  f=np.full(self.x.shape,-20.)
  for k in range(0,len(path),16):
   points=path[k:k+16];r=radius[k:k+16];pad=r.max()+20
   lo=np.maximum(np.floor(points.min(0)-pad).astype(int)-self.lo,0)
   hi=np.minimum(np.ceil(points.max(0)+pad).astype(int)-self.lo,self.x.shape[::-1])
   x,y=lo;X,Y=hi
   if X<=x or Y<=y:continue
   q=np.c_[self.x[y:Y,x:X].ravel(),self.y[y:Y,x:X].ravel()]
   f[y:Y,x:X]=np.maximum(f[y:Y,x:X],np.max(r[None,:]-cdist(q,points),axis=1).reshape(Y-y,X-x))
  return f
 def image(self,t):
  if not 0<=t<=1:raise ValueError("Time outside [0,1]")
  v=clock(t);q=self.rate*t/(1+(self.rate-1)*t)
  path,radii,branches=self.geometry(q)
  center=(1-v)*self.a.center+v*self.b.center
  oldcenter=(1-clock(q))*self.a.center+clock(q)*self.b.center
  target=(1-v)*self.areas[0]+v*self.areas[1]
  residual=None;weight=0.
  u=clock(q)
  if u<.15 or u>.85:
   start=u<.15;endpoint=self.a if start else self.b
   weight=(1-(u if start else 1-u)/.15)**4
   ep,er,eb=self.geometry(0. if start else 1.)
   offset=center-endpoint.center
   et=self.local_tube(ep+offset,er)
   for p,r in eb:et=np.maximum(et,self.local_tube(p+offset,r))
   residual=np.clip(endpoint.sample(self.x,self.y,center),-20,20)-np.clip(et,-20,20)
  def field(scale):
   transform=lambda p:center+scale*(p-oldcenter)
   f=self.local_tube(transform(path),radii)
   for p,r in branches:f=np.maximum(f,self.local_tube(transform(p),r))
   if residual is not None:f+=weight*residual
   if self.min_cavity_area:
    yy,xx=np.nonzero(f>-.5)
    if len(xx):
     x=max(0,xx.min()-2);X=min(f.shape[1],xx.max()+3)
     y=max(0,yy.min()-2);Y=min(f.shape[0],yy.max()+3)
     f[y:Y,x:X]=area_closing(f[y:Y,x:X],area_threshold=self.min_cavity_area,connectivity=1)
   return f
  def mass(scale):return np.clip(field(scale)+.5,0,1).sum()-target
  scale=brentq(mass,.1,3.,xtol=1e-7) if 0<t<1 else 1.
  f=field(scale)
  coverage=np.clip(f+.5,0,1)
  if abs(coverage.sum()-target)>.01:raise ValueError("Thin geometry area calibration failed")
  if np.any(coverage[[0,-1],:]) or np.any(coverage[:,[0,-1]]):raise ValueError("Conservative thin geometry escaped field")
  out=np.zeros((720,1280),np.uint8);x,y=self.lo+[640,360];X,Y=self.hi+[640,360]
  out[y:Y,x:X]=np.uint8(np.rint(coverage*255))
  self.last_scale=scale
  return out,float(coverage.sum())

