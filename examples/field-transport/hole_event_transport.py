"""Bounded staged hole birth/death, with independently scheduled hole masks.

The exterior finishes deforming before holes open; holes close before exterior
motion. Only zero-to-N (or its reverse) is supported. Hole masks must stay inside
ink, remain disjoint and connected. This is geometry, not material conservation.
"""
from functools import lru_cache
import numpy as np
from scipy import ndimage as ndi
from field_transport import clock
from scene_transport import draw_scene
from combined_transport import topology

class HoleEventPlan:
 kind='event'
 def __init__(self,a,b,body_factory):
  self.a=a;self.b=b;self.reverse=len(a)>len(b)
  source,target=(b,a) if self.reverse else (a,b)
  if len(source)!=1 or len(target)<2:raise ValueError('Hole event requires zero-to-N holes')
  self.source=source;self.target=target;self.outer=body_factory([source[0]],[target[0]])
  self.plan=None
 @lru_cache(maxsize=8)
 def hole_masks(self,t):
  t=1-t if self.reverse else t
  v=clock(np.clip((t-.65)/.35,0,1))
  if v==0:return ()
  masks=[]
  for p in self.target[1:]:
   center=p.mean(0);loop=center+v*(p-center)
   im=draw_scene([[loop]],ss=8)
   if np.any(im>127) and topology(im>127)!=(1,0):raise ValueError('Hole event mask fragmented')
   masks.append(im)
  return tuple(masks)
 def expected_holes(self,t):return sum(bool(np.any(im>127)) for im in self.hole_masks(float(t)))
 def image(self,t):
  if not 0<=t<=1:raise ValueError('Time outside [0,1]')
  forward=1-t if self.reverse else t;u=min(forward/.65,1.)
  if self.outer.kind in ['tree','stroke']:im,_=self.outer.plan.image(u)
  else:im=draw_scene([self.outer.contours(u)],ss=8)
  used=np.zeros_like(im,dtype=bool)
  for hole in self.hole_masks(float(t)):
   active=hole>127
   if np.any(active&used) or np.any(active&~ndi.binary_erosion(im>127)):
    raise ValueError('Hole event touches exterior or another hole')
   used|=active;im=np.minimum(im,255-hole)
  if topology(im>127)!=(1,self.expected_holes(t)):raise ValueError('Hole event topology mismatch')
  return im,float(im.sum()/255)
