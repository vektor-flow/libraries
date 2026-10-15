"""Opt-in candidate selection for contour failures; validation is not a proof.

Keep a valid existing body trajectory byte-for-byte. A failed hole-free contour
may try endpoint-inferred tree ribbons in a bounded set of fixed local frames.
No case identifiers, glyph names, or semantic correspondences enter selection.
"""
import numpy as np
from scipy.optimize import brentq
from scipy import ndimage as ndi
from combined_transport import BodyPlan,CombinedScene,topology
from field_transport import clock
from scene_transport import draw_scene
from tree_transport import TreeTransport


def valid_body(plan,a,b,samples=65):
 times=np.linspace(0,1,samples)
 if isinstance(plan,TreeTransport):
  times=np.unique(np.r_[np.linspace(0,1,257),[brentq(lambda t:clock(t)-u,0,1) for u in np.linspace(0,1,51)[1:-1]]])
 for t in times:
  if isinstance(plan,TreeTransport):im,_=plan.image(float(t))
  else:im=draw_scene([plan.contours(float(t))],ss=8)
  if topology(im>127)!=(1,len(a)-1):return False
  if t in [0,1]:
   truth=draw_scene([a if t==0 else b],ss=8)>127;actual=im>127
   if np.any(actual&~ndi.binary_dilation(truth)) or np.any(ndi.binary_erosion(truth)&~actual):return False
 return True


class ValidatedBodyPlan(BodyPlan):
 def __init__(self,a,b):
  super().__init__(a,b)
  self.rejected_candidates=[]
  if self.kind!='contour' or len(a)!=1 or valid_body(self,a,b):return
  for weight in [1.,0.,.5]:
   try:
    candidate=TreeTransport(a,b,frame_weight=weight)
    if not valid_body(candidate,a,b):raise ValueError('Sampled topology/endpoint failure')
    self.kind='tree';self.plan=candidate;return
   except ValueError as exc:self.rejected_candidates.append(dict(frame_weight=weight,error=str(exc)))
  # Keeping the original failure visible lets whole-scene validation reject it;
  # candidate selection is not permission to relax the existing acceptance gate.


class ValidatedCombinedScene(CombinedScene):
 def __init__(self,a,b):
  super().__init__(a,b,body_plan_factory=ValidatedBodyPlan)
  self.cohort_route=None
  try:
   for t in np.linspace(0,1,33):super().images(float(t))
   return
  except ValueError as exc:
   if not (isinstance(exc.args[0],tuple) and exc.args[0][0]=='Unrelated foreground overlap'):raise
  from cohort_routes import CohortRoutes
  def masks(t):
   ims,metrics=super(ValidatedCombinedScene,self).images(t,validate=False)
   self.validate_images(ims,t,overlap=False)
   return ims
  def validate(route):
   self.cohort_route=route
   previous=None
   try:
    for t in np.linspace(0,1,257):
     ims,_=self.images(float(t));count=topology(np.max(ims,axis=0)>127)[0]
     if previous is not None:
      delta=count-previous;direction=np.sign(len(self.original_b)-len(self.original_a))
      if direction*delta<0 or (direction==0 and delta):raise ValueError('Routed scene count reversal')
     previous=count
   finally:self.cohort_route=None
  self.cohort_route=CohortRoutes(masks,len(self.groups),validate)
 def validate_images(self,ims,t,overlap=True):
  occupied=np.zeros((720,1280),bool)
  for (kind,plan),im in zip(self.groups,ims):
   n,h=topology(im>127)
   if kind=='replica':
    if h or not 1<=n<=len(plan.targets):raise ValueError(('Routed branch topology',t,n,h))
   else:
    holes=len(plan.a)-1
    if (n,h)!=(1,holes):raise ValueError(('Routed body topology',t,n,h))
   if overlap and np.any(occupied&(im>127)):raise ValueError(('Routed cohort overlap',t))
   occupied|=im>127
 def images(self,t,validate=True):
  if self.cohort_route is None:return super().images(t,validate=validate)
  ims,metrics=super().images(t,validate=False);out=[];new_metrics=[]
  for im,offset in zip(ims,self.cohort_route.displacements(t)):
   yy,xx=np.nonzero(im)
   lo=np.array([xx.min(),yy.min()])-2;hi=np.array([xx.max()+1,yy.max()+1])+2
   if np.any(lo+offset<2) or np.any(hi+offset>[1278,718]):raise ValueError('Routed cohort escaped viewport')
   integer=np.floor(offset).astype(int);fraction=offset-integer
   crop=im[lo[1]:hi[1],lo[0]:hi[0]].astype(float)
   shifted=ndi.shift(crop,fraction[::-1],order=1,mode='constant',cval=0.,prefilter=False)
   moved=np.zeros_like(im);x,y=lo+integer;X,Y=hi+integer
   moved[y:Y,x:X]=np.uint8(np.rint(shifted));out.append(moved)
   n,h=topology(moved>127);new_metrics.append((n,h,float(moved.sum()/255)))
  if validate:self.validate_images(out,t)
  return out,new_metrics
