"""Opt-in candidate selection for contour failures; validation is not a proof.

Keep a valid existing body trajectory byte-for-byte. A failed hole-free contour
may try endpoint-inferred tree ribbons in a bounded set of fixed local frames.
No case identifiers, glyph names, or semantic correspondences enter selection.
"""
from functools import lru_cache
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
  if self.kind in ['contour','stroke'] and len(a)==len(b)==1:
   from thin_transport import stroke_width
   from conservative_thin_transport import ConservativeThinTransport
   def image(t):
    return self.plan.image(t)[0] if self.kind=='stroke' else draw_scene([self.contours(t)],ss=8)
   limit=max(stroke_width(image(t)) for t in [0.,1.])+2.
   if any(stroke_width(image(t))>limit for t in [.25,.5,.75]):
    for weight in [0.,1.,.5]:
     try:
      candidate=ConservativeThinTransport(a,b,frame_weight=weight)
      if not valid_body(candidate,a,b):raise ValueError('Thin ribbon topology/endpoint failure')
      if any(stroke_width(candidate.image(float(t))[0])>limit for t in np.linspace(0,1,33)):
       raise ValueError('Thin ribbon widened beyond endpoint envelope')
      self.kind='tree';self.plan=candidate;return
     except ValueError as exc:self.rejected_candidates.append(dict(thin_frame_weight=weight,error=str(exc)))
  if self.kind!='contour' or len(a)!=1 or valid_body(self,a,b):return
  for weight in [1.,0.,.5]:
   try:
    candidate=TreeTransport(a,b,frame_weight=weight)
    if not valid_body(candidate,a,b):raise ValueError('Sampled topology/endpoint failure')
    self.kind='tree';self.plan=candidate;return
   except ValueError as exc:self.rejected_candidates.append(dict(frame_weight=weight,error=str(exc)))
  # Keeping the original failure visible lets whole-scene validation reject it;
  # candidate selection is not permission to relax the existing acceptance gate.


def validated_replica(source,targets):
 from replica_transport import Group
 from scaled_replica_transport import ScaledGroup
 original=Group(source,targets)
 previous=1
 for t in np.linspace(0,1,65):
  im,_=original.image(float(t));n,h=topology(im>127)
  if h or not previous<=n<=len(targets):break
  previous=n
 else:return original
 from replica_transport import shape_error
 from morph_replica_transport import MorphGroup
 failures=[]
 factory=MorphGroup if any(shape_error(source,q)>.06 for q in targets) else ScaledGroup
 for power in [1.,.5,2.]:
  try:
   kwargs=dict(body_factory=ValidatedBodyPlan) if factory is MorphGroup else {}
   candidate=factory(source,targets,separation_power=power,**kwargs)
   previous=1
   for t in np.linspace(0,1,257):
    im,_=candidate.image(float(t));n,h=topology(im>127)
    if h or not previous<=n<=len(targets):raise ValueError((float(t),previous,n,h))
    previous=n
   candidate.rejected_candidates=failures
   return candidate
  except ValueError as exc:failures.append(dict(separation_power=power,error=str(exc)))
 raise ValueError(('Scaled replica topology',failures))



def event_body(a,b):
 if len(a)!=len(b):
  from hole_event_transport import HoleEventPlan
  from thin_event_transport import ThinEventPlan
  failures=[]
  for weight in [0.,1.,.5]:
   try:
    candidate=ThinEventPlan(a,b,frame_weight=weight)
    candidate.rejected_candidates=failures;return candidate
   except ValueError as exc:failures.append(dict(thin_frame_weight=weight,error=str(exc)))
  candidate=HoleEventPlan(a,b,ValidatedBodyPlan);candidate.rejected_candidates=failures
  return candidate
 return ValidatedBodyPlan(a,b)


class ValidatedCombinedScene(CombinedScene):
 def __init__(self,a,b):
  super().__init__(a,b,body_plan_factory=event_body,replica_factory=validated_replica,allow_hole_events=True,allow_general_branching=True)
  self.prepare_route()
 def prepare_route(self):
  self.cohort_route=None;self.motion_clock=None;self.motion_rejection=None
  try:
   for t in np.linspace(0,1,33):super().images(float(t))
   return
  except ValueError as exc:
   if not (isinstance(exc.args[0],tuple) and exc.args[0][0]=='Unrelated foreground overlap'):raise
  from cohort_routes import CohortRoutes
  def masks(t):
   ims,metrics=self.base_images(t)
   self.validate_images(ims,t,overlap=False)
   return ims
  def validate(route):
   self.cohort_route=route
   previous=None
   try:
    for t in np.r_[np.linspace(0,1,33),np.linspace(0,1,257)]:
     if t==0:previous=None
     ims,_=self.images(float(t));count=topology(np.max(ims,axis=0)>127)[0]
     if previous is not None:
      delta=count-previous;direction=np.sign(len(self.original_b)-len(self.original_a))
      if direction*delta<0 or (direction==0 and delta):raise ValueError('Routed scene count reversal')
     previous=count
   finally:self.cohort_route=None
  self.cohort_route=CohortRoutes(masks,len(self.groups),validate)
  self.prepare_motion()
 def prepare_motion(self):
  from motion_clock import MotionClock
  self.motion_clock=MotionClock(self.cohort_route);self.motion_rejection=None
  if self.motion_clock.integral is None:return
  previous=None;previous_holes=None
  try:
   for t in np.linspace(0,1,257):
    ims,_=self.images(float(t));n,h=topology(np.max(ims,axis=0)>127)
    if h!=self.expected_holes_at(float(t)):raise ValueError('Retimed hole schedule')
    if previous is not None:
     direction=np.sign(len(self.original_b)-len(self.original_a))
     holes=np.sign(sum(len(p)-1 for p in self.original_b)-sum(len(p)-1 for p in self.original_a))
     if direction*(n-previous)<0 or (direction==0 and n!=previous):raise ValueError('Retimed count reversal')
     if holes*(h-previous_holes)<0 or (holes==0 and h!=previous_holes):raise ValueError('Retimed hole reversal')
    previous=n;previous_holes=h
  except ValueError as exc:
   self.motion_rejection=str(exc);self.motion_clock=None
 def scene_time(self,t):
  motion=getattr(self,'motion_clock',None)
  return motion(t) if motion is not None else t
 def expected_holes_at(self,t):
  return super().expected_holes_at(self.scene_time(t))
 @lru_cache(maxsize=384)
 def base_crops(self,t):
  ims,metrics=super().images(t,validate=False);crops=[]
  for im in ims:
   yy,xx=np.nonzero(im)
   if not len(xx):raise ValueError('Empty cohort')
   x,y=xx.min(),yy.min();X,Y=xx.max()+1,yy.max()+1
   crops.append((int(x),int(y),im[y:Y,x:X].copy()))
  return crops,metrics
 def base_images(self,t):
  crops,metrics=self.base_crops(float(t));ims=[]
  for x,y,crop in crops:
   im=np.zeros((720,1280),np.uint8);im[y:y+crop.shape[0],x:x+crop.shape[1]]=crop;ims.append(im)
  return ims,metrics
 def validate_images(self,ims,t,overlap=True):
  occupied=np.zeros((720,1280),bool)
  for (kind,plan),im in zip(self.groups,ims):
   n,h=topology(im>127)
   if kind=='replica':
    if h or not 1<=n<=len(plan.targets):raise ValueError(('Routed branch topology',t,n,h))
   else:
    holes=plan.expected_holes(1-t if self.reverse else t) if kind=='event' else len(plan.a)-1
    if (n,h)!=(1,holes):raise ValueError(('Routed body topology',t,n,h))
   if overlap and np.any(occupied&(im>127)):raise ValueError(('Routed cohort overlap',t))
   occupied|=im>127
 def images(self,t,validate=True):
  t=self.scene_time(t)
  if self.cohort_route is None:return super().images(t,validate=validate)
  ims,metrics=self.base_images(t);out=[];new_metrics=[]
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
