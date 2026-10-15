"""Width-first medial ribbons, including a cut cycle that closes into a hole.

An endpoint skeleton spanning tree supplies anonymous paths and branches. Cuts
remove graph edges, not endpoint ink: the retained tube closes when its ends
meet again. Widths interpolate locally; neither threshold dilation, global area
calibration nor cavity filling is used. Visible area may change with length.
"""
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from tree_transport import TreeTransport
from stroke_transport import medial_path

from replica_transport import ScalarOutline


def stroke_width(im):
 mask=im>127;y,x=np.nonzero(mask)
 if not len(x):raise ValueError('Empty thin geometry')
 mask=np.pad(mask[y.min():y.max()+1,x.min():x.max()+1],1)
 radii=ndi.distance_transform_edt(mask)[skeletonize(mask)]
 return float(2*np.quantile(radii,.9))


class ThinTreeTransport(TreeTransport):
 def __init__(self,a,b,frame_weight=1.,align_cycles=True):
  if not 0<=frame_weight<=1:raise ValueError('Frame weight outside [0,1]')
  self.frame_weight=frame_weight;self.fill_cavities=False;self.align_cycles=align_cycles
  self.a=ScalarOutline(a);self.b=ScalarOutline(b);self.cut_hint=None
  if len(a)>len(b):
   self.pb=self.path(self.b)
   if align_cycles:self.cut_hint=(self.pb[0]+self.pb[-1])/2-self.b.center+self.a.center
   self.pa=self.path(self.a);self.branches=self.branches[::-1]
  else:
   self.pa=self.path(self.a)
   if len(b)>len(a) and align_cycles:self.cut_hint=(self.pa[0]+self.pa[-1])/2-self.a.center+self.b.center
   self.pb=self.path(self.b)
  cost=lambda q:np.sum(((self.pa-self.a.center)-(q-self.b.center))**2)
  if cost(self.pb[::-1])<cost(self.pb):self.pb=self.pb[::-1]
  self.ra=self.a.sample(self.pa[:,0],self.pa[:,1],self.a.center)
  self.rb=self.b.sample(self.pb[:,0],self.pb[:,1],self.b.center)
  points=np.concatenate(a+b);padding=max(32.,.3*max(np.linalg.norm(np.diff(p,axis=0),axis=1).sum() for p in [self.pa,self.pb]));self.lo=np.maximum(np.floor(points.min(0)-padding).astype(int),[-640,-360]);self.hi=np.minimum(np.ceil(points.max(0)+padding).astype(int),[640,360])
  y,x=np.mgrid[self.lo[1]:self.hi[1],self.lo[0]:self.hi[0]];self.x=x+.5;self.y=y+.5;self.points=np.c_[self.x.ravel(),self.y.ravel()]
 def path(self,field):
  path,branches=medial_path(field,with_branches=True,spanning_tree=True,cut_hint=self.cut_hint)
  if not hasattr(self,'branches'):self.branches=[]
  self.branches.append(branches)
  return path
 def branch_pairs(self):
  if not any(self.branches):self.pairs=[];self.attachments=([],[]);return []
  return super().branch_pairs()
 def image(self,t):
  if not 0<=t<=1:raise ValueError('Time outside [0,1]')
  f=self.raw(t)
  if getattr(self,'min_cavity_area',0):
   from skimage.morphology import area_closing
   f=area_closing(f,area_threshold=self.min_cavity_area,connectivity=1)
  coverage=np.clip(f+.5,0,1)
  if np.any(coverage[[0,-1],:]) or np.any(coverage[:,[0,-1]]):raise ValueError('Thin tree escaped field')
  out=np.zeros((720,1280),np.uint8);x,y=self.lo+[640,360];X,Y=self.hi+[640,360];out[y:Y,x:X]=np.uint8(np.rint(coverage*255))
  return out,float(coverage.sum())
