"""Sampled space-time routing for changing anonymous raster cohorts.

Masks are generated from the actual body plans. Max-pooled silhouette
correlations provide conservative candidate obstacles; full-resolution replay
must independently validate the final route. This bounded prioritized search
is neither a complete planner nor a continuous collision proof.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize,brentq
from field_transport import clock


class CohortRoutes:
 def __init__(self,images,groups,validate,movable=None,sample_counts=(51,201),physical_samples=False):
  self.movable=None if movable is None else tuple(movable)
  self.physical_samples=physical_samples
  failures=[]
  for samples in sample_counts:
   try:
    self._prepare(images,groups,validate,samples)
    self.planning_samples=samples;self.rejected_resolutions=failures;return
   except ValueError as exc:failures.append(dict(samples=samples,error=str(exc)))
  raise ValueError(('No sampled cohort route',failures))
 def _prepare(self,images,groups,validate,samples):
  self.times=np.linspace(0,1,samples);self.grid=4.;self.obstacles=[];bounds=[];centers=[]
  if self.physical_samples:self.times=clock(self.times)
  for k,u in enumerate(self.times):
   t=brentq(lambda t:clock(t)-u,0,1) if 0<u<1 else u
   masks=images(t);cropped=[];frame_bounds=[]
   for im in masks:
    mask=im>127;yy,xx=np.nonzero(mask)
    if not len(xx):raise ValueError('Empty cohort cannot be routed')
    frame_bounds.append([[xx.min(),yy.min()],[xx.max()+1,yy.max()+1]])
    pooled=mask.reshape(180,4,320,4).any((1,3));y,x=np.nonzero(pooled)
    lo=np.array([x.min(),y.min()]);hi=np.array([x.max()+1,y.max()+1])
    cropped.append((pooled[lo[1]:hi[1],lo[0]:hi[0]],lo))
   obstacles=[]
   for i in range(groups):
    for j in range(i):
     a,oa=cropped[i];b,ob=cropped[j]
     collision=fftconvolve(b.astype(float),a[::-1,::-1].astype(float),mode='full')>.5
     distance=ndi.distance_transform_edt(~collision)*self.grid
     origin=oa-ob+np.array(a.shape[::-1])-1
     obstacles.append((i,j,distance,origin))
   self.obstacles.append(obstacles);bounds.append(frame_bounds)
  self.bounds=np.asarray(bounds);centers=self.bounds.mean(2)
  travel=np.linalg.norm(centers[-1]-centers[0],axis=1)
  priority=np.argsort(-travel,kind='stable')
  if self.movable is not None:priority=np.array([i for i in priority if i in self.movable])
  orders=[priority,priority[::-1]]+[np.roll(priority,k) for k in range(1,groups)]
  failures=[]
  for step in [36.,96.,192.]:
   for ramp in [False,True]:
    for order in orders:
     for axis in [1,0]:
      try:
       self._plan(axis,order,ramp,step)
       validate(self)
       self.rejected=failures;return
      except ValueError as exc:failures.append(str(exc))
  raise ValueError(('No sampled cohort corridor',failures))
 def _plan(self,axis,priority,ramp=False,max_step=36.):
  self.axis=axis;groups=self.bounds.shape[1]
  levels=np.arange(-240,241,6.) if axis==1 else np.arange(-480,481,12.)
  zero=int(np.argmin(abs(levels)));offsets=np.zeros((len(self.times),groups))
  transition=(levels[:,None]-levels[None,:])**2
  transition[abs(levels[:,None]-levels[None,:])>max_step]=np.inf
  for body in priority:
   allowed=(self.bounds[:,body,0,axis,None]+levels>=5)&(self.bounds[:,body,1,axis,None]+levels<=(715 if axis==1 else 1275))
   for k,obstacles in enumerate(self.obstacles):
    for i,j,distance,origin in obstacles:
     if body not in [i,j]:continue
     other=j if body==i else i;sign=1 if body==i else -1
     q=np.broadcast_to(origin[:,None],(2,len(levels))).copy().astype(float)
     q[axis]+=sign*(levels-offsets[k,other])/self.grid
     gap=ndi.map_coordinates(distance,[q[1],q[0]],order=1,mode='constant',cval=1e4)
     clearance=8.*clock(min(1.,self.times[k]/.15,(1-self.times[k])/.15)) if ramp else 8.
     allowed[k]&=gap>=max(.01,clearance)
   allowed[0]=False;allowed[-1]=False;allowed[0,zero]=allowed[-1,zero]=True
   cost=np.full(len(levels),np.inf);cost[zero]=0;parents=[]
   for k in range(1,len(self.times)):
    values=cost[:,None]+transition;previous=np.argmin(values,axis=0)
    cost=values[previous,np.arange(len(levels))]+.002*levels**2
    cost[~allowed[k]]=np.inf;parents.append(previous)
   if not np.isfinite(cost[zero]):raise ValueError(('No connected cohort corridor',int(body),axis))
   path=np.zeros(len(self.times));q=zero
   for k in range(len(self.times)-1,0,-1):path[k]=levels[q];q=int(parents[k-1][q])
   bounds=[]
   for k,value in enumerate(path):
    q=int(np.argmin(abs(levels-value)));lo=hi=q
    while lo>0 and allowed[k,lo-1]:lo-=1
    while hi+1<len(levels) and allowed[k,hi+1]:hi+=1
    bounds.append((levels[lo],levels[hi]))
   def energy(y):
    d=np.diff(y);dd=np.diff(y,n=2)
    value=.002*np.sum(y*y)+np.sum(d*d)+100*np.sum(dd*dd)
    g=.004*y;g[:-1]-=2*d;g[1:]+=2*d;g[:-2]+=200*dd;g[1:-1]-=400*dd;g[2:]+=200*dd
    return value,g
   result=minimize(energy,path,jac=True,bounds=bounds,method='L-BFGS-B',options={'maxiter':1500,'ftol':1e-11,'gtol':1e-7})
   path=result.x;path[0]=path[-1]=0;offsets[:,body]=path
  self.offsets=offsets
  self.spline=CubicSpline(self.times,offsets,axis=0,bc_type=((1,np.zeros(groups)),(1,np.zeros(groups))))
 def displacements(self,t):return self.spline(clock(t))[:,None]*np.eye(2)[self.axis]
