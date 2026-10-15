"""A sampled one-hole event from closure of a width-preserving medial ribbon."""
import numpy as np
from scipy import ndimage as ndi
from thin_transport import stroke_width
from conservative_thin_transport import ConservativeThinTransport
from combined_transport import topology
from scene_transport import draw_scene


class ThinEventPlan:
 kind='event'
 def __init__(self,a,b,frame_weight=0.):
  if sorted([len(a),len(b)])!=[1,2]:raise ValueError('Thin event requires zero-to-one holes')
  self.a=a;self.b=b;self.reverse=len(a)>len(b)
  source,target=(b,a) if self.reverse else (a,b)
  self.plan=ConservativeThinTransport(source,target,frame_weight=frame_weight,rate=4.,min_cavity_area=4)
  # Remove sub-four-pixel scalar cavities at every field level. These can be
  # parasitic counters beside a closing junction; keep the large cycle cavity.
  # Endpoint, width and complete hole-schedule checks still apply afterward.
  self.plan.min_cavity_area=4
  self.start_holes=0;self.end_holes=1
  self.width_limit=max(stroke_width(self.plan.image(t)[0]) for t in [0.,1.])+2.
  previous=self.start_holes;interval=None
  for t in np.linspace(0,1,257):
   im,_=self.plan.image(float(t));n,h=topology(im>127)
   if n!=1 or h not in [0,1] or (h-previous)*(self.end_holes-self.start_holes)<0:
    raise ValueError(('Thin event topology reversal',float(t),n,h))
   if stroke_width(im)>self.width_limit:raise ValueError('Thin event widened beyond endpoint envelope')
   if h!=previous:interval=(float(t-1/256),float(t))
   previous=h
   if t in [0,1]:
    truth=draw_scene([source if t==0 else target],ss=8)>127;actual=im>127
    if h!=(self.start_holes if t==0 else self.end_holes) or np.any(actual&~ndi.binary_dilation(truth)) or np.any(ndi.binary_erosion(truth)&~actual):
     raise ValueError('Thin event endpoint mismatch')
  if interval is None:raise ValueError('Thin event never occurred')
  lo,hi=interval
  # A declared phase threshold is checked independently by subsequent images;
  # expected_holes does not inspect the rendered frame or copy its hole count.
  for _ in range(35):
   middle=(lo+hi)/2;h=topology(self.plan.image(middle)[0]>127)[1]
   if h==self.start_holes:lo=middle
   elif h==self.end_holes:hi=middle
   else:raise ValueError('Extra hole at event boundary')
  self.event_time=hi
 def expected_holes(self,t):
  q=1-t if getattr(self,'reverse',False) else t
  return self.start_holes if q<self.event_time else self.end_holes
 def image(self,t):
  im,mass=self.plan.image(1-t if getattr(self,'reverse',False) else t)
  if topology(im>127)!=(1,self.expected_holes(t)):raise ValueError(('Thin event schedule mismatch',t))
  return im,mass
