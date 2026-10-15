"""Endpoint-inferred ribbon coordinates for single open-stroke silhouettes.

A scalar ribbon follows interpolated medial tangent angles and thickness. No character
labels, stroke annotations, or supplied point correspondences are used. Branched
and closed medial graphs are outside this bounded candidate's scope.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial.distance import cdist
from skimage.morphology import skeletonize
from field_transport import clock
from replica_transport import ScalarOutline

def medial_path(field):
 skeleton=skeletonize(field.field>0);yy,xx=np.nonzero(skeleton);count=len(xx)
 lookup=np.full(skeleton.shape,-1,int);lookup[yy,xx]=np.arange(count)
 rows=[];cols=[];weights=[]
 for dy,dx in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
  qy,qx=yy+dy,xx+dx;valid=(qy>=0)&(qx>=0)&(qy<skeleton.shape[0])&(qx<skeleton.shape[1])
  source=np.where(valid)[0];target=lookup[qy[valid],qx[valid]];keep=target>=0
  rows.extend(source[keep]);cols.extend(target[keep]);weights.extend([np.hypot(dx,dy)]*int(keep.sum()))
 graph=csr_matrix((weights,(rows,cols)),shape=(count,count));degree=np.diff(graph.indptr);ends=np.flatnonzero(degree==1)
 if not 2<=len(ends)<=20:raise ValueError('No bounded open-stroke medial path')
 distance,previous=dijkstra(graph,directed=False,indices=ends,return_predecessors=True)
 pairs=distance[:,ends];i,j=np.unravel_index(np.argmax(pairs),pairs.shape)
 if not np.isfinite(pairs[i,j]):raise ValueError('Disconnected medial graph')
 path=[];node=int(ends[j]);start=int(ends[i])
 while node!=start:
  path.append(node);node=int(previous[i,node])
  if node<0:raise ValueError('Incomplete medial path')
 path.append(start);path=np.array(path[::-1]);length=pairs[i,j]/field.ss
 if len(path)<.65*count:raise ValueError('Silhouette has substantial medial branches')
 points=(np.c_[xx[path],yy[path]]+.5)/field.ss-field.size/2+field.center
 radius=field.field[yy[path],xx[path]]
 if length<6*np.median(radius):raise ValueError('Silhouette is not stroke-like')
 points=ndi.gaussian_filter1d(points,.8,axis=0,mode='nearest')
 distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
 s=np.linspace(0,distance[-1],256)
 result=np.c_[np.interp(s,distance,points[:,0]),np.interp(s,distance,points[:,1])]
 if np.min(field.sample(result[:,0],result[:,1],field.center))<=0:
  raise ValueError('Smoothed medial path leaves silhouette')
 return result

class StrokeTransport:
 def __init__(self,a,b):
  if len(a)!=len(b) or len(a)!=1:raise ValueError('Stroke candidate requires one hole-free body')
  self.a=ScalarOutline(a);self.b=ScalarOutline(b);self.pa=medial_path(self.a);self.pb=medial_path(self.b)
  cost=lambda q:np.sum(((self.pa-self.a.center)-(q-self.b.center))**2)
  if cost(self.pb[::-1])<cost(self.pb):self.pb=self.pb[::-1]
  self.ra=self.a.sample(self.pa[:,0],self.pa[:,1],self.a.center)
  self.rb=self.b.sample(self.pb[:,0],self.pb[:,1],self.b.center)
  points=np.concatenate(a+b);padding=max(32.,.3*max(np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in [self.pa,self.pb]));self.lo=np.maximum(np.floor(points.min(0)-padding).astype(int),[-640,-360]);self.hi=np.minimum(np.ceil(points.max(0)+padding).astype(int),[640,360])
  if np.any(self.lo<[-640,-360]) or np.any(self.hi>[640,360]):raise ValueError('Stroke field exceeds viewport')
  y,x=np.mgrid[self.lo[1]:self.hi[1],self.lo[0]:self.hi[0]];self.x=x+.5;self.y=y+.5;self.points=np.c_[self.x.ravel(),self.y.ravel()]
  self.area0=float(np.clip(self.raw(0)+.5,0,1).sum());self.area1=float(np.clip(self.raw(1)+.5,0,1).sum())
 def tube(self,path,radius):
  result=np.full(len(self.points),-np.inf)
  for k in range(0,len(path),32):
   d=cdist(self.points,path[k:k+32])
   result=np.maximum(result,np.max(radius[None,k:k+32]-d,axis=1))
  return result.reshape(self.x.shape)
 def raw(self,t):
  v=clock(t)
  da=np.diff(self.pa,axis=0);db=np.diff(self.pb,axis=0)
  aa=np.unwrap(np.arctan2(da[:,1],da[:,0]));ab=np.unwrap(np.arctan2(db[:,1],db[:,0]))
  ab+=2*np.pi*np.round(np.mean(aa-ab)/(2*np.pi))
  angle=(1-v)*aa+v*ab;length=(1-v)*np.linalg.norm(da,axis=1)+v*np.linalg.norm(db,axis=1)
  path=np.vstack([np.zeros(2),np.cumsum(np.c_[np.cos(angle),np.sin(angle)]*length[:,None],axis=0)])
  path+=((1-v)*self.pa.mean(0)+v*self.pb.mean(0))-path.mean(0)
  f=self.tube(path,(1-v)*self.ra+v*self.rb)
  # Endpoint detail is retained as a continuous scalar residual. Its support
  # decays smoothly while the medial ribbon carries the changing shape.
  if v<.15:
   at=self.a.center+(self.b.center-self.a.center)*v
   original=self.a.sample(self.x,self.y,at)
   tube=self.tube(self.pa+(self.b.center-self.a.center)*v,self.ra)
   f+=max(0.,1-v/.15)**4*(original-tube)
  elif v>.85:
   at=self.b.center+(self.a.center-self.b.center)*(1-v)
   original=self.b.sample(self.x,self.y,at)
   tube=self.tube(self.pb+(self.a.center-self.b.center)*(1-v),self.rb)
   f+=max(0.,1-(1-v)/.15)**4*(original-tube)
  return f
 def image(self,t):
  f=self.raw(t);v=clock(t);desired=(1-v)*self.area0+v*self.area1;lo=-20.;hi=20.
  for _ in range(28):
   shift=(lo+hi)/2
   if np.clip(f+shift+.5,0,1).sum()<desired:lo=shift
   else:hi=shift
  coverage=np.clip(f+(lo+hi)/2+.5,0,1)
  if abs(coverage.sum()-desired)>.01:raise ValueError('Stroke area calibration failed')
  if np.any(coverage[[0,-1],:]) or np.any(coverage[:,[0,-1]]):raise ValueError('Stroke escaped field')
  out=np.zeros((720,1280),np.uint8);x,y=self.lo+[640,360];X,Y=self.hi+[640,360];out[y:Y,x:X]=np.uint8(np.rint(coverage*255))
  return out,float(coverage.sum())
