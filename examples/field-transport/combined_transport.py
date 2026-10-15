"""Compose endpoint-inferred body transforms under one clock.

Bounded research planner, not arbitrary image understanding. Inputs are anonymous
closed foreground boundaries. Reference axes/grid are separate background ink.
Every candidate must pass geometric and raster validation before acceptance.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
from field_transport import Transport,clock,area,topology as full_topology
from scene_transport import draw_scene
from replica_transport import Group,center,shape_error
from affine_transport import AffineTransport
from registered_transport import RegisteredTransport
from rigid_routes import RoutedScene
from stroke_transport import StrokeTransport

def topology(mask):
 yy,xx=np.nonzero(mask)
 if not len(xx):return (0,0)
 return full_topology(np.pad(mask[yy.min():yy.max()+1,xx.min():xx.max()+1],1))

def translation_error(a,b):
 if len(a)!=len(b):return np.inf
 delta=center(b)-center(a)
 return max(max(cKDTree(p+delta).query(q)[0].max(),cKDTree(q).query(p+delta)[0].max()) for p,q in zip(a,b))

class ProfileTransport:
 """Infer thin x-monotone ribbons from polygon intersections, not formulas.

The vertical profile correspondence avoids transporting long strokes by perimeter
phase, which can collapse them into thick blobs. No curve samples are supplied
as correspondences; profiles are recovered independently from each silhouette.
"""
 def __init__(self,a,b):
  if len(a)!=1 or len(b)!=1:raise ValueError('Profile requires hole-free ribbons')
  self.a=self.profile(a[0]);self.b=self.profile(b[0]);self.expected=(1,0)
 def profile(self,p):
  lo,hi=p.min(0),p.max(0);extent=hi-lo
  if extent[0]<120 or abs(area(p))/np.prod(extent)>.18:
   raise ValueError('Not a long thin ribbon')
  x=np.linspace(lo[0]+1e-6,hi[0]-1e-6,512);q=np.roll(p,-1,axis=0)
  valid=(x[:,None]>=np.minimum(p[:,0],q[:,0]))&(x[:,None]<np.maximum(p[:,0],q[:,0]))
  dx=q[:,0]-p[:,0];y=p[:,1]+(x[:,None]-p[:,0])*(q[:,1]-p[:,1])/np.where(abs(dx)>1e-12,dx,1)
  if np.any(valid.sum(1)!=2):raise ValueError('Ribbon is not x-monotone')
  lower=np.min(np.where(valid,y,np.inf),axis=1);upper=np.max(np.where(valid,y,-np.inf),axis=1)
  widths=upper-lower
  if widths.min()<=0 or widths.max()>45:raise ValueError('Ribbon thickness outside bounded profile scope')
  return x,(lower+upper)/2,widths/2
 def contours(self,t):
  v=clock(t);x,c,w=[(1-v)*p+v*q for p,q in zip(self.a,self.b)]
  # Preserve the eased visible area, without globally swelling the centerline.
  mass=lambda p:float(np.trapezoid(2*p[2],p[0]))
  wanted=(1-v)*mass(self.a)+v*mass(self.b);w=w*wanted/mass((x,c,w))
  return [np.vstack([np.c_[x,c-w],np.c_[x[::-1],(c+w)[::-1]]])]

class BodyPlan:
 def __init__(self,a,b):
  self.a=a;self.b=b;self.ca=center(a);self.cb=center(b)
  if translation_error(a,b)<.15:self.kind='rigid';self.plan=None;return
  try:self.plan=AffineTransport(a,b);self.kind='affine';return
  except ValueError:pass
  try:self.plan=ProfileTransport(a,b);self.kind='profile';return
  except ValueError:pass
  try:self.plan=StrokeTransport(a,b);self.kind='stroke';return
  except ValueError:pass
  local_a=[p-self.ca for p in a];local_b=[p-self.cb for p in b]
  self.plan=(RegisteredTransport if len(a)>2 else Transport)(local_a,local_b)
  self.kind='registered' if len(a)>2 else 'contour'
 def contours(self,t):
  v=clock(t)
  if self.kind=='rigid':return [p+v*(self.cb-self.ca) for p in self.a]
  if self.kind in ['affine','profile']:return self.plan.contours(t)
  return [p+(1-v)*self.ca+v*self.cb for p in self.plan.contours(t)]

class CombinedScene:
 def __init__(self,a,b,body_plan_factory=BodyPlan):
  self.original_a=a;self.original_b=b;self.reverse=len(a)>len(b)
  if self.reverse:a,b=b,a
  self.a=a;self.b=b
  costs=np.full((len(a),len(b)),1e9);exact=np.zeros_like(costs,dtype=bool)
  for i,p in enumerate(a):
   for j,q in enumerate(b):
    if len(p)!=len(q):continue
    error=shape_error(p,q);exact[i,j]=translation_error(p,q)<.15
    extent_p=np.maximum(np.ptp(p[0],axis=0),.1);extent_q=np.maximum(np.ptp(q[0],axis=0),.1)
    costs[i,j]=np.linalg.norm(center(p)-center(q))+200*error+60*np.linalg.norm(np.log(extent_p/extent_q))+(0 if exact[i,j] else 2000)
  rows,cols=linear_sum_assignment(costs)
  if np.any(costs[rows,cols]>1e8):raise ValueError('No same-hole primary assignment')
  owners={int(j):int(i) for i,j in zip(rows,cols)}
  for j in range(len(b)):
   if j in owners:continue
   eligible=[i for i,p in enumerate(a) if len(p)==len(b[j])==1 and shape_error(p,b[j])<.06]
   if not eligible:raise ValueError('Unmatched outline requires unsupported branching')
   owners[j]=min(eligible,key=lambda i:np.linalg.norm(center(a[i])-center(b[j])))
  self.groups=[];rigid_a=[];rigid_b=[];self.rigid_indices=[]
  for i,p in enumerate(a):
   targets=[b[j] for j in range(len(b)) if owners[j]==i]
   if len(targets)>1:
    if len(p)!=1 or any(shape_error(p,q)>.06 for q in targets):
     raise ValueError('Cohort requires unsupported non-affine branching')
    self.groups.append(('replica',Group(p,targets)))
   else:
    plan=body_plan_factory(p,targets[0]);self.groups.append((plan.kind,plan))
    if plan.kind=='rigid':
     self.rigid_indices.append(i);rigid_a.append(p);rigid_b.append(targets[0])
  self.route=None
  # Retain direct motion when it is already clear. Routing's coarser planning
  # raster must not become a prerequisite for stationary fine native glyphs.
  if len(rigid_a)>1:
   try:
    for t in np.linspace(0,1,41):
     draw_scene([[p+clock(t)*(center(q)-center(pbody)) for p in pbody] for pbody,q in zip(rigid_a,rigid_b)],ss=8)
   except ValueError:self.route=RoutedScene(rigid_a,rigid_b)
  self.raster_ss={i:8 for i in range(len(self.groups))}
  # Choose one sampling resolution per rigid body for its entire trajectory.
  # Subpixel translations can reveal counters caused solely by coarse polygon
  # coverage; retain the same topology gate and increase rendering precision.
  for t in np.linspace(0,1,41):
   routed=dict(zip(self.rigid_indices,self.route.contours(t))) if self.route else {}
   for i in self.rigid_indices:
    if self.raster_ss[i]>8:continue
    loops=routed[i] if i in routed else self.groups[i][1].contours(t)
    if topology(draw_scene([loops],ss=8)>127)!=(1,len(loops)-1):self.raster_ss[i]=32
  self.expected_holes=sum(len(p)-1 for p in a)
  if self.expected_holes!=sum(len(p)-1 for p in b):raise ValueError('Hole event is unsupported')
 def images(self,t,validate=True):
  if not 0<=t<=1:raise ValueError('Time outside [0,1]')
  t=1-t if self.reverse else t
  routed=dict(zip(self.rigid_indices,self.route.contours(t))) if self.route else {}
  out=[];occupied=np.zeros((720,1280),bool);metrics=[]
  for i,(kind,plan) in enumerate(self.groups):
   if kind=='replica':im,mass=plan.image(t);loops=None
   elif kind in ['stroke','tree']:im,mass=plan.plan.image(t);loops=None
   else:
    loops=routed.get(i) if i in routed else plan.contours(t)
    im=draw_scene([loops],ss=self.raster_ss[i])
    if self.raster_ss[i]>8:im=np.uint8(np.rint(ndi.gaussian_filter(im.astype(float),.7)))
    mass=float(im.sum()/255)
   mask=im>127;n,h=topology(mask)
   if validate:
    if np.any(occupied&mask):raise ValueError(('Unrelated foreground overlap',i,t))
    if kind in ['stroke','tree'] and (n,h)!=(1,0):raise ValueError(('Stroke topology',i,t,n,h))
    if kind not in ['replica','stroke','tree'] and (n,h)!=(1,len(loops)-1):raise ValueError(('Body topology',i,t,n,h))
    if kind=='replica' and (h!=0 or not 1<=n<=len(plan.targets)):raise ValueError(('Branch topology',i,t,n,h))
   occupied|=mask;out.append(im);metrics.append((n,h,mass))
  return out,metrics
