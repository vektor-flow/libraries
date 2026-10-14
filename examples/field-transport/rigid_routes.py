"""Endpoint-only, fixed-shape planar routing experiment.

Collision obstacles are correlations of anonymous glyph silhouettes, not discs
or bounding boxes. A time/offset lattice finds corridors; constrained quadratic
smoothing reduces detour and acceleration inside each corridor. Cubic splines
and a quintic clock give C2 motion with stationary endpoints. This is a bounded
prioritized candidate search, not a complete path planner; final sampled raster
checks remain mandatory. No topology gate is relaxed.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize
from PIL import Image, ImageDraw
from field_transport import clock
from scene_transport import Scene

class RoutedScene(Scene):
 def __init__(self,a,b):
  super().__init__(a,b,exact_first=True)
  if not all(p[3] and abs(p[4])<1e-7 and abs(p[5]-1)<1e-7 for p in self.parts):
   raise ValueError('Fixed-shape routing requires unchanged translated geometry')
  self.offsets=np.zeros(len(self.parts));self.clearance=3.;self.grid=2.
  radius=max(np.max(abs(q)) for p,*_ in self.parts for q in p.a)
  n=int(np.ceil(radius/self.grid))*2+9;mid=(n-1)/2
  masks=[]
  for plan,*_ in self.parts:
   im=Image.new('L',(n,n));d=ImageDraw.Draw(im)
   for k,q in enumerate(plan.a):d.polygon([tuple(x) for x in q/self.grid+mid],fill=1 if k==0 else 0)
   masks.append(np.array(im)>0)
  self.obstacles=[]
  for i in range(len(masks)):
   for j in range(i):
    collision=fftconvolve(masks[j].astype(float),masks[i][::-1,::-1].astype(float),mode='full')>.5
    distance=(ndi.distance_transform_edt(~collision)-ndi.distance_transform_edt(collision))*self.grid
    self.obstacles.append((i,j,distance,n-1))
  self.times=np.linspace(0,1,151)
  starts=np.array([p[1] for p in self.parts]);ends=np.array([p[2] for p in self.parts])
  self.base=(1-self.times[:,None,None])*starts+self.times[:,None,None]*ends
  offsets=np.zeros((len(self.times),len(self.parts)))
  levels=np.arange(-240,241,6.);zero=int(np.argmin(abs(levels)))
  # Longest-moving bodies reserve their paths first; every later path avoids
  # all already routed bodies and the remaining straight candidate paths.
  for body in np.argsort(-np.linalg.norm(ends-starts,axis=1)):
   allowed=np.ones((len(self.times),len(levels)),bool)
   extent=max(abs(self.parts[body][0].a[0][:,1]))
   allowed &= abs(self.base[:,body,1,None]+levels)<345-extent
   for i,j,distance,mid in self.obstacles:
    if body not in [i,j]:continue
    other=j if body==i else i;sign=1 if body==i else -1
    delta=self.base[:,i]-self.base[:,j]
    yy=delta[:,1,None]+sign*(levels-offsets[:,other,None])
    xx=np.broadcast_to(delta[:,0,None],yy.shape)
    gap=ndi.map_coordinates(distance,[yy/self.grid+mid,xx/self.grid+mid],order=1,mode='constant',cval=500)
    allowed &= gap>=7
   # Exact endpoints have their actual measured clearance, not extra padding.
   allowed[0]=False;allowed[-1]=False;allowed[0,zero]=True;allowed[-1,zero]=True
   cost=np.full(len(levels),np.inf);cost[zero]=0;parents=[]
   transition=(levels[:,None]-levels[None,:])**2
   transition[abs(levels[:,None]-levels[None,:])>36]=np.inf
   for k in range(1,len(self.times)):
    values=cost[:,None]+transition
    previous=np.argmin(values,axis=0);cost=values[previous,np.arange(len(levels))]+.002*levels**2
    cost[~allowed[k]]=np.inf;parents.append(previous)
   if not np.isfinite(cost[zero]):raise ValueError(('No clear space-time path',int(body)))
   path=np.zeros(len(self.times));q=zero
   for k in range(len(self.times)-1,0,-1):path[k]=levels[q];q=parents[k-1][q]
   bounds=[]
   for k,value in enumerate(path):
    q=int(np.argmin(abs(levels-value)));lo=q;hi=q
    while lo>0 and allowed[k,lo-1]:lo-=1
    while hi+1<len(levels) and allowed[k,hi+1]:hi+=1
    bounds.append((levels[lo],levels[hi]))
   def energy(y):
    d=np.diff(y);dd=np.diff(y,n=2)
    value=.002*np.sum(y*y)+np.sum(d*d)+100*np.sum(dd*dd)
    gradient=.004*y;gradient[:-1]-=2*d;gradient[1:]+=2*d
    gradient[:-2]+=200*dd;gradient[1:-1]-=400*dd;gradient[2:]+=200*dd
    return value,gradient
   result=minimize(energy,path,jac=True,bounds=bounds,method='L-BFGS-B',options={'maxiter':2000,'ftol':1e-11,'gtol':1e-7})
   path=result.x;path[0]=path[-1]=0
   offsets[:,body]=path
  self.offsets=offsets
  self.spline=CubicSpline(self.times,offsets,axis=0,bc_type=((1,np.zeros(len(self.parts))),(1,np.zeros(len(self.parts)))))
 def contours(self,t):
  out=super().contours(t);offset=self.spline(clock(t))
  return [[q+[0,offset[i]] for q in body] for i,body in enumerate(out)]
