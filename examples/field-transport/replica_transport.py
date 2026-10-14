"""Geometry-only repeated-outline split/merge candidate. Not arbitrary branching."""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
from scipy.special import logsumexp
from PIL import Image,ImageDraw
from field_transport import clock,topology
from scene_transport import draw_scene

def center(body):
 p=np.concatenate(body);return (p.min(0)+p.max(0))/2

def shape_error(a,b):
 if len(a)!=len(b):return 100.
 scores=[]
 for x,y in zip(a,b):
  x=(x-(x.min(0)+x.max(0))/2)/np.maximum(np.ptp(x,axis=0),1e-8)
  y=(y-(y.min(0)+y.max(0))/2)/np.maximum(np.ptp(y,axis=0),1e-8)
  scores.append(max(cKDTree(x).query(y)[0].max(),cKDTree(y).query(x)[0].max()))
 return max(scores)

class ScalarOutline:
 def __init__(self,body):
  self.center=center(body);local=[p-self.center for p in body];extent=np.max(abs(np.concatenate(local)),axis=0)
  self.size=np.ceil(2*extent+96).astype(int);self.ss=4
  im=Image.new('L',tuple(self.size*self.ss));d=ImageDraw.Draw(im)
  for i,p in enumerate(local):d.polygon([tuple(q) for q in (p+self.size/2)*self.ss],fill=255 if i==0 else 0)
  mask=np.asarray(im)>127
  self.field=(ndi.distance_transform_edt(mask)-ndi.distance_transform_edt(~mask))/self.ss
 def sample(self,X,Y,at):
  xx=(X-at[0]+self.size[0]/2)*self.ss-.5;yy=(Y-at[1]+self.size[1]/2)*self.ss-.5
  return ndi.map_coordinates(self.field,[yy,xx],order=1,mode='constant',cval=-100.)

class Group:
 def __init__(self,source,targets):
  self.source=source;self.targets=targets;self.a=ScalarOutline(source);self.b=[ScalarOutline(p) for p in targets]
  points=np.concatenate([p for body in [source]+targets for p in body]);lo=np.floor(points.min(0)-48).astype(int);hi=np.ceil(points.max(0)+48).astype(int)
  lo=np.maximum(lo,[-640,-360]);hi=np.minimum(hi,[640,360]);self.lo=lo;self.hi=hi
  Y,X=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]];self.X=X+.5;self.Y=Y+.5
  self.temperature=min(20.,max(2.,np.min(np.ptp(source[0],axis=0))*.25))
  self.area0=float(np.clip(self.raw(0)+.5,0,1).sum());self.area1=float(np.clip(self.raw(1)+.5,0,1).sum())
 def raw(self,t):
  v=clock(t);fields=[];centers=[]
  for target in self.b:
   at=(1-v)*self.a.center+v*target.center
   centers.append(at)
   fields.append((1-v)*self.a.sample(self.X,self.Y,at)+v*target.sample(self.X,self.Y,at))
  tau=self.temperature*16*v*v*(1-v)*(1-v)
  if tau<1e-6:return np.max(fields,axis=0)
  # Localize the contact bridge. A spatially constant smooth union can tear a
  # flat contact face across its entire width at once, leaving fragile holes
  # under subpixel sampling/encoding. A curved, central neck opens at its edges
  # first and disconnects last at the center, for arbitrary outline families.
  midpoint=np.mean(centers,axis=0)
  radius=max(4.,.35*np.max(np.ptp(self.source[0],axis=0)))
  weight=np.exp(-((self.X-midpoint[0])**2+(self.Y-midpoint[1])**2)/(2*radius*radius))
  temperature=np.maximum(tau*weight,1e-8)
  return temperature*logsumexp(np.array(fields)/temperature,axis=0)
 def image(self,t):
  f=self.raw(t);v=clock(t);desired=(1-v)*self.area0+v*self.area1;lo=-40.;hi=40.
  for _ in range(28):
   shift=(lo+hi)/2
   if np.clip(f+shift+.5,0,1).sum()<desired:lo=shift
   else:hi=shift
  coverage=np.clip(f+(lo+hi)/2+.5,0,1)
  if abs(coverage.sum()-desired)>.01:raise ValueError('Area calibration failed')
  if np.any(coverage[[0,-1],:]>.001) or np.any(coverage[:,[0,-1]]>.001):raise ValueError('Group exceeds its finite field region')
  out=np.zeros((720,1280),np.uint8);x,y=self.lo+[640,360];X,Y=self.hi+[640,360]
  out[y:Y,x:X]=np.uint8(np.rint(255*coverage))
  return out,float(coverage.sum())

class ReplicaScene:
 def __init__(self,a,b):
  self.reverse=len(a)>len(b)
  if self.reverse:a,b=b,a
  if len(a)==len(b):raise ValueError('Replica transport requires a count change')
  self.source=a;self.target=b
  self.counts=(len(a),len(b))
  if any(len(body)!=1 for body in a+b):raise ValueError('This replica candidate requires hole-free bodies')
  for side in [a,b]:
   if topology(draw_scene(side,ss=8)>127)!=(len(side),0):raise ValueError('Invalid replica endpoints')
  ca=np.array([center(p) for p in a]);cb=np.array([center(p) for p in b])
  errors=np.array([[shape_error(x,y) for y in b] for x in a]);cost=np.linalg.norm(ca[:,None]-cb[None,:],axis=2)+10*errors
  cost[errors>.06]=1e9;rows,cols=linear_sum_assignment(cost)
  if np.any(cost[rows,cols]>1e8):raise ValueError('Endpoints are not repeated affine-equivalent outlines')
  owners={int(j):int(i) for i,j in zip(rows,cols)}
  for j in range(len(b)):
   if j not in owners:
    i=int(np.argmin(cost[:,j]))
    if cost[i,j]>1e8:raise ValueError('Unmatched new outline requires nonrigid branching')
    owners[j]=i
  self.groups=[]
  for i,source in enumerate(a):
   targets=[b[j] for j in range(len(b)) if owners[j]==i]
   if len(targets)==1:
    target=targets[0];delta=center(target)-center(source)
    if max(cKDTree(p+delta).query(q)[0].max() for p,q in zip(source,target))<.15:
     self.groups.append(('rigid',source,delta));continue
   self.groups.append(('field',Group(source,targets)))
 def image(self,t):
  t=1-t if self.reverse else t;out=np.zeros((720,1280),np.uint8);mass=[]
  for group in self.groups:
   if group[0]=='rigid':
    _,body,delta=group;im=draw_scene([[p+clock(t)*delta for p in body]],ss=8);mass.append(float(im.sum()/255))
   else:im,m=group[1].image(t);mass.append(m)
   if np.any((out>127)&(im>127)):raise ValueError('Unrelated cohort overlap')
   np.maximum(out,im,out=out)
  return out,mass
