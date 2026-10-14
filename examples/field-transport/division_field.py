"""Bounded analytic two-disc division fixture, not an arbitrary branching solver."""
import numpy as np
from field_transport import clock

y,x=np.mgrid[:320,:512];x=x+.5-256;y=y+.5-160

def raw(t):
 v=clock(t);center=-50+100*v;separation=120*v;radius=(1-v)*90+v*64
 a=radius-np.hypot(x-center-separation,y);b=radius-np.hypot(x-center+separation,y)
 rounding=100*v*(1-v)
 return .5*(a+b+np.sqrt((a-b)**2+rounding**2))

start_area=np.clip(raw(0)+.5,0,1).sum();end_area=np.clip(raw(1)+.5,0,1).sum()
def division(t):
 field=raw(t);v=clock(t);target=(1-v)*start_area+v*end_area;lo=-50.;hi=50.
 for _ in range(28):
  offset=(lo+hi)/2
  if np.clip(field+offset+.5,0,1).sum()<target:lo=offset
  else:hi=offset
 alpha=np.clip(field+(lo+hi)/2+.5,0,1)
 out=np.zeros((720,1280),np.uint8);out[200:520,384:896]=np.uint8(np.rint(alpha*255))
 return out,float(alpha.sum())
