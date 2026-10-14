"""Endpoint-inferred affine motion for equal-sampled closed boundaries.

Bounded research adapter: rejects differing sampling and non-affine endpoints.
No symbol identities or authored correspondences are accepted.
"""
import numpy as np
from scipy.linalg import polar
from field_transport import clock

class AffineTransport:
 def __init__(self,a,b):
  if len(a)!=len(b) or any(x.shape!=y.shape for x,y in zip(a,b)):
   raise ValueError('Affine candidate requires equal boundary sampling')
  self.a=a;self.ca=a[0].mean(0);self.cb=b[0].mean(0)
  x=a[0]-self.ca;y=b[0]-self.cb;candidates=[]
  for reverse in [False,True]:
   target=y[::-1] if reverse else y
   for phase in range(len(y)):
    z=np.roll(target,phase,axis=0);matrix=np.linalg.lstsq(x,z,rcond=None)[0].T
    if np.linalg.det(matrix)<=0:continue
    error=np.max(np.linalg.norm(x@matrix.T-z,axis=1))
    if error>1e-6:continue
    rotation,stretch=polar(matrix);angle=np.arctan2(rotation[1,0],rotation[0,0]);values,vectors=np.linalg.eigh(stretch)
    if min(values)<=0:continue
    # Prefer least strain, then least rotation among geometric symmetries.
    score=float(np.sum(np.log(values)**2)+1e-6*angle**2)
    candidates.append((score,matrix,angle,values,vectors))
  if not candidates:raise ValueError('Endpoints are not affine equivalent')
  _,self.matrix,self.angle,self.values,self.vectors=min(candidates,key=lambda x:x[0])
  # All holes must agree with the same map, allowing cyclic indexing.
  for p,q in zip(a[1:],b[1:]):
   moved=(p-self.ca)@self.matrix.T+self.cb
   error=min(np.max(np.linalg.norm(moved-np.roll(v,k,axis=0),axis=1)) for v in [q,q[::-1]] for k in range(len(q)))
   if error>1e-6:raise ValueError('Holes do not share the affine map')
  self.expected=(1,len(a)-1)
 def contours(self,t):
  if not 0<=t<=1:raise ValueError('Time outside [0,1]')
  v=clock(t);angle=v*self.angle;c=np.cos(angle);s=np.sin(angle)
  rotation=np.array([[c,-s],[s,c]])
  stretch=(self.vectors*self.values**v)@self.vectors.T
  matrix=rotation@stretch;center=(1-v)*self.ca+v*self.cb
  return [(p-self.ca)@matrix.T+center for p in self.a]
