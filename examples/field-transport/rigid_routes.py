"""Endpoint-only, fixed-shape planar routing experiment.

Collision obstacles are correlations of anonymous glyph silhouettes, not discs
or bounding boxes. Time/offset lattices find transverse or full planar corridors; constrained quadratic
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
from field_transport import clock,topology
from scene_transport import Scene,draw_scene

class RoutedScene(Scene):
 def __init__(self,a,b):
  super().__init__(a,b,exact_first=True)
  if not all(p[3] and abs(p[4])<1e-7 and abs(p[5]-1)<1e-7 for p in self.parts):
   raise ValueError('Fixed-shape routing requires unchanged translated geometry')
  for endpoint in [a,b]:
   if topology(draw_scene(endpoint)>127)!=self.expected:raise ValueError("Invalid endpoint topology")
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
  failures=[];candidates=[]
  order=np.argsort([-np.linalg.norm(p[2]-p[1]) for p in self.parts])
  # A failed priority can block a feasible coordinated route. Retry priorities
  # derived from the geometry, never from formula names or fixture identities.
  orders=[order,order[::-1]]+[np.roll(order,k) for k in range(1,len(order))]
  for priority in orders:
   for axis in [1,0]:
    try:
     self._plan_axis(axis,priority)
     self._validate_corridors()
     u=np.linspace(0,1,1001);path=self.spline(u)
     d=np.diff(path,axis=0);dd=np.diff(path,n=2,axis=0)
     cost=float(.002*np.mean(path*path)+np.mean((1000*d)**2)+.01*np.mean((1000**2*dd)**2))
     candidates.append((cost,axis,self.offsets.copy(),self.spline))
    except ValueError as exc:failures.append(str(exc))
   if candidates:break
  self.candidate_failures=failures
  if candidates:
   self.route_cost,self.axis,self.offsets,self.spline=min(candidates,key=lambda c:c[0])
   return
  for priority in orders:
   try:
    self._plan_plane(priority);self._validate_corridors();return
   except ValueError as exc:failures.append(str(exc))
  raise ValueError(('No validated planar route',failures))

 def _plan_axis(self,axis,priority):
  self.axis=axis
  self.times=np.linspace(0,1,151)
  starts=np.array([p[1] for p in self.parts]);ends=np.array([p[2] for p in self.parts])
  self.base=(1-self.times[:,None,None])*starts+self.times[:,None,None]*ends
  offsets=np.zeros((len(self.times),len(self.parts)))
  levels=np.arange(-240 if axis==1 else -480,241 if axis==1 else 481,6.);zero=int(np.argmin(abs(levels)))
  # Every later path avoids all already routed bodies and the remaining
  # straight candidate paths for this geometry-derived priority.
  for body in priority:
   allowed=np.ones((len(self.times),len(levels)),bool)
   extent=max(abs(self.parts[body][0].a[0][:,axis]))
   limit=345 if axis==1 else 625
   allowed &= abs(self.base[:,body,axis,None]+levels)<limit-extent
   for i,j,distance,mid in self.obstacles:
    if body not in [i,j]:continue
    other=j if body==i else i;sign=1 if body==i else -1
    delta=self.base[:,i]-self.base[:,j]
    changed=delta[:,axis,None]+sign*(levels-offsets[:,other,None])
    fixed=np.broadcast_to(delta[:,1-axis,None],changed.shape)
    xx,yy=(fixed,changed) if axis==1 else (changed,fixed)
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
 def _plan_plane(self,priority):
  """Full planar offset search when a transverse corridor cannot connect."""
  self.axis=None;self.times=np.linspace(0,1,151)
  starts=np.array([p[1] for p in self.parts]);ends=np.array([p[2] for p in self.parts])
  self.base=(1-self.times[:,None,None])*starts+self.times[:,None,None]*ends
  offsets=np.zeros((len(self.times),len(self.parts),2))
  xs=np.arange(-480,481,12.);ys=np.arange(-240,241,12.)
  X,Y=np.meshgrid(xs,ys);grid=np.stack([X,Y],axis=-1);zero=(len(ys)//2,len(xs)//2)
  moves=[(dy,dx) for dy in [-1,0,1] for dx in [-1,0,1]]
  for body in priority:
   extent=np.max(abs(np.concatenate(self.parts[body][0].a)),axis=0)
   centers=self.base[:,body,None,None,:]+grid
   allowed=np.all(abs(centers)+extent<[625,345],axis=-1)
   for i,j,distance,mid in self.obstacles:
    if body not in [i,j]:continue
    other=j if body==i else i;sign=1 if body==i else -1
    delta=self.base[:,i]-self.base[:,j]
    q=(delta[:,None,None,:]+sign*(grid-offsets[:,other,None,None,:]))/self.grid+mid
    gap=ndi.map_coordinates(distance,[q[:,:,:,1],q[:,:,:,0]],order=1,mode='constant',cval=500)
    allowed &= gap>=7
   allowed[0]=False;allowed[-1]=False;allowed[0,zero[0],zero[1]]=True;allowed[-1,zero[0],zero[1]]=True
   cost=np.full(X.shape,np.inf);cost[zero]=0;parents=[]
   for k in range(1,len(self.times)):
    best=np.full(X.shape,np.inf);parent=np.zeros(X.shape,np.uint8)
    for m,(dy,dx) in enumerate(moves):
     candidate=np.roll(cost,(dy,dx),axis=(0,1))+144*(dy*dy+dx*dx)
     if dy>0:candidate[:dy]=np.inf
     if dy<0:candidate[dy:]=np.inf
     if dx>0:candidate[:,:dx]=np.inf
     if dx<0:candidate[:,dx:]=np.inf
     take=candidate<best;best[take]=candidate[take];parent[take]=m
    cost=best+.002*(X*X+Y*Y);cost[~allowed[k]]=np.inf;parents.append(parent)
   if not np.isfinite(cost[zero]):raise ValueError(('No full planar corridor',int(body)))
   path=np.zeros((len(self.times),2));indices=[];y,x=zero
   for k in range(len(self.times)-1,0,-1):
    path[k]=grid[y,x];indices.append((y,x));dy,dx=moves[parents[k-1][y,x]];y-=dy;x-=dx
   indices=list(reversed(indices+[(y,x)]));bounds=[[],[]]
   for k,(y,x) in enumerate(indices):
    loY=hiY=y;loX=hiX=x
    while loY>0 and allowed[k,loY-1,x]:loY-=1
    while hiY+1<len(ys) and allowed[k,hiY+1,x]:hiY+=1
    while loX>0 and np.all(allowed[k,loY:hiY+1,loX-1]):loX-=1
    while hiX+1<len(xs) and np.all(allowed[k,loY:hiY+1,hiX+1]):hiX+=1
    bounds[0].append((xs[loX],xs[hiX]));bounds[1].append((ys[loY],ys[hiY]))
   def energy(v):
    d=np.diff(v);dd=np.diff(v,n=2)
    value=.002*np.sum(v*v)+np.sum(d*d)+100*np.sum(dd*dd)
    g=.004*v;g[:-1]-=2*d;g[1:]+=2*d;g[:-2]+=200*dd;g[1:-1]-=400*dd;g[2:]+=200*dd
    return value,g
   for dimension in [0,1]:
    solution=minimize(energy,path[:,dimension],jac=True,bounds=bounds[dimension],method='L-BFGS-B',options={'maxiter':2000,'ftol':1e-11,'gtol':1e-7})
    path[:,dimension]=solution.x
   path[0]=path[-1]=0;offsets[:,body]=path
  self.offsets=offsets
  zeros=np.zeros((len(self.parts),2))
  self.spline=CubicSpline(self.times,offsets,axis=0,bc_type=((1,zeros),(1,zeros)))

 def displacements(self,u):
  values=self.spline(u)
  return values if self.axis is None else values[...,None]*np.eye(2)[self.axis]

 def _validate_corridors(self):
  u=np.linspace(0,1,1001)
  starts=np.array([p[1] for p in self.parts]);ends=np.array([p[2] for p in self.parts])
  centers=(1-u[:,None,None])*starts+u[:,None,None]*ends
  centers+=self.displacements(u)
  for i,j,distance,mid in self.obstacles:
   delta=(centers[:,i]-centers[:,j])/self.grid+mid
   gaps=ndi.map_coordinates(distance,[delta[:,1],delta[:,0]],order=1,mode='constant',cval=500)
   if gaps.min()<min(self.clearance,float(gaps[0]),float(gaps[-1]))-1e-6:
    raise ValueError('Smoothed path left the collision-free corridor')
  for i,part in enumerate(self.parts):
   extent=np.max(abs(np.concatenate(part[0].a)),axis=0)
   if np.any(abs(centers[:,i])+extent>[625,345]):raise ValueError('Smoothed path outside viewport')

 def contours(self,t):
  out=super().contours(t);offset=self.displacements(clock(t))
  return [[q+offset[i] for q in body] for i,body in enumerate(out)]
