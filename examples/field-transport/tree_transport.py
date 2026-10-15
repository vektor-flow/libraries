"""Connected medial-tree ribbon candidate from anonymous endpoint silhouettes.

Significant side branches attach to the inferred primary path. Missing branches
contract continuously into their attachment, with endpoint scalar residuals and
coverage-area calibration inherited from the stroke candidate. This is bounded
geometry research: cycles, unrelated-body routing and topology still require
independent validation; it is not a semantic equation matcher.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy import ndimage as ndi
from skimage.morphology import reconstruction
from field_transport import clock
from stroke_transport import StrokeTransport,medial_path


class TreeTransport(StrokeTransport):
 def __init__(self,a,b,frame_weight=1.):
  if not 0<=frame_weight<=1:raise ValueError('Frame weight outside [0,1]')
  self.frame_weight=frame_weight
  super().__init__(a,b)
 def image(self,t):
  if not 0<=t<=1:raise ValueError('Time outside [0,1]')
  return super().image(t)
 def path(self,field):
  path,branches=medial_path(field,with_branches=True)
  if not hasattr(self,'branches'):self.branches=[]
  self.branches.append(branches)
  return path
 def branch_pairs(self):
  if hasattr(self,'pairs'):return self.pairs
  a,b=self.branches
  if not a and not b:raise ValueError('Tree candidate requires a significant side branch')
  def descriptor(branch,path):
   k=int(np.argmin(np.linalg.norm(path-branch[0],axis=1)))
   tangent=path[min(k+1,len(path)-1)]-path[max(0,k-1)]
   tip=branch[-1]-branch[0];side=np.sign(tangent[0]*tip[1]-tangent[1]*tip[0])
   return k/(len(path)-1),side
  da=[descriptor(q,self.pa) for q in a];db=[descriptor(q,self.pb) for q in b]
  costs=np.array([[abs(x[0]-y[0])+abs(x[1]-y[1]) for y in db] for x in da]).reshape(len(a),len(b))
  rows,cols=linear_sum_assignment(costs)
  self.pairs=[(int(i),int(j)) for i,j in zip(rows,cols)]
  self.pairs += [(i,None) for i in range(len(a)) if i not in rows]
  self.pairs += [(None,j) for j in range(len(b)) if j not in cols]
  self.attachments=(da,db)
  return self.pairs
 def reconstructed(self,path,radius,branches):
  f=self.tube(path,radius)
  for branch,radii in branches:f=np.maximum(f,self.tube(branch,radii))
  return f
 def geometry(self,t):
  v=clock(t);pairs=self.branch_pairs()
  da=np.diff(self.pa,axis=0);db=np.diff(self.pb,axis=0)
  aa=np.unwrap(np.arctan2(da[:,1],da[:,0]));ab=np.unwrap(np.arctan2(db[:,1],db[:,0]))
  ab+=2*np.pi*np.round(np.mean(aa-ab)/(2*np.pi))
  angle=(1-v)*aa+v*ab;length=(1-v)*np.linalg.norm(da,axis=1)+v*np.linalg.norm(db,axis=1)
  path=np.vstack([np.zeros(2),np.cumsum(np.c_[np.cos(angle),np.sin(angle)]*length[:,None],axis=0)])
  path+=((1-v)*self.pa.mean(0)+v*self.pb.mean(0))-path.mean(0)
  branches=[];grid=np.linspace(0,1,len(path))
  for i,j in pairs:
   a=self.branches[0][i] if i is not None else None;b=self.branches[1][j] if j is not None else None
   sa=self.attachments[0][i][0] if a is not None else self.attachments[1][j][0]
   sb=self.attachments[1][j][0] if b is not None else sa
   at=(1-v)*sa+v*sb;root=np.array([np.interp(at,grid,path[:,k]) for k in range(2)])
   local_a=a-a[0] if a is not None else np.zeros_like(b)
   local_b=b-b[0] if b is not None else np.zeros_like(a)
   # Carry branch coordinates in the attachment's moving tangent frame;
   # global-vector interpolation can drag a branch across its own spine.
   def frame(points,s):
    d=np.gradient(points,axis=0);tangent=np.array([np.interp(s,grid,d[:,k]) for k in range(2)])
    tangent/=np.linalg.norm(tangent)
    return np.array([[tangent[0],-tangent[1]],[tangent[1],tangent[0]]])
   global_local=(1-v)*local_a+v*local_b
   local_a=local_a@frame(self.pa,sa)
   local_b=local_b@frame(self.pb,sb)
   ra=self.a.sample(a[:,0],a[:,1],self.a.center) if a is not None else np.full(len(b),np.interp(sa,grid,self.ra))
   rb=self.b.sample(b[:,0],b[:,1],self.b.center) if b is not None else np.full(len(a),np.interp(sb,grid,self.rb))
   local=(1-self.frame_weight)*global_local+self.frame_weight*((1-v)*local_a+v*local_b)@frame(path,at).T
   branches.append((root+local,(1-v)*ra+v*rb))
  return path,(1-v)*self.ra+v*self.rb,branches
 def raw(self,t):
  v=clock(t);path,radius,branches=self.geometry(t)
  f=self.reconstructed(path,radius,branches)
  if v<.15 or v>.85:
   start=v<.15;field=self.a if start else self.b;progress=v if start else 1-v
   offset=(self.b.center-self.a.center)*v if start else (self.a.center-self.b.center)*(1-v)
   primary=self.pa if start else self.pb;radii=self.ra if start else self.rb
   branches=[(p+offset,field.sample(p[:,0],p[:,1],field.center)) for p in self.branches[0 if start else 1]]
   original=field.sample(self.x,self.y,field.center+offset)
   tube=self.reconstructed(primary+offset,radii,branches)
   f+=max(0.,1-progress/.15)**4*(original-tube)
  if not getattr(self,'fill_cavities',True):return f
  # Fill enclosed scalar valleys before coverage-area calibration. This is a
  # grayscale geometry operator, not a binary patch on the accepted image.
  # It applies at every field level, including the later calibration threshold.
  seed=np.full_like(f,f.max())
  seed[[0,-1],:]=f[[0,-1],:];seed[:,[0,-1]]=f[:,[0,-1]]
  return reconstruction(seed,f,method='erosion',footprint=ndi.generate_binary_structure(2,1))
