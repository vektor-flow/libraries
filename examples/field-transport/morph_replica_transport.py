"""Replica geometry from individually planned body morphs, then geometric scaling."""
from functools import lru_cache
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import reconstruction
from scaled_replica_transport import ScaledGroup
from field_transport import clock
from scene_transport import draw_scene
from combined_transport import topology
from replica_transport import center
from stroke_transport import connected_field

class MorphGroup(ScaledGroup):
 def __init__(self,source,targets,body_factory,separation_power=1.):
  self.body_plans=[body_factory(source,target) for target in targets]
  super().__init__(source,targets,separation_power=separation_power)
 @lru_cache(maxsize=16)
 def fields(self,t):
  out=[]
  for plan in self.body_plans:
   if plan.kind in ['tree','stroke']:im,_=plan.plan.image(t)
   else:im=draw_scene([plan.contours(t)],ss=8)
   x,y=self.lo+[640,360];X,Y=self.hi+[640,360];coverage=im[y:Y,x:X]/255.
   mask=coverage>.5;f=ndi.distance_transform_edt(mask)-ndi.distance_transform_edt(~mask)
   f-=np.where(mask,.5,-.5)
   partial=(coverage>0)&(coverage<1);f[partial]=coverage[partial]-.5
   out.append(connected_field(f))
  return out
 def raw(self,t,scale=1.):
  v=clock(t);u=self.separation_progress(t);fields=[]
  for f,target in zip(self.fields(float(t)),self.targets):
   cb=center(target);ca=center(self.source);at=(1-u)*ca+u*cb;nominal=(1-v)*ca+v*cb
   xx=((self.X-at[0])/scale+nominal[0]-self.lo[0]-.5)
   yy=((self.Y-at[1])/scale+nominal[1]-self.lo[1]-.5)
   fields.append(scale*ndi.map_coordinates(f,[yy,xx],order=1,mode='constant',cval=-100.))
  f=np.max(fields,axis=0);seed=np.full_like(f,f.max())
  seed[[0,-1],:]=f[[0,-1],:];seed[:,[0,-1]]=f[:,[0,-1]]
  return reconstruction(seed,f,method='erosion',footprint=ndi.generate_binary_structure(2,1))
