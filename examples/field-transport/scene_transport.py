"""Native endpoint geometry scene adapter; glyph names never enter assignment."""
import numpy as np
import contourpy
from scipy.optimize import linear_sum_assignment
from PIL import Image,ImageDraw
from field_transport import Transport,clock,area,normalize,topology,crossings,resample

def inside(q,p):
 a=p;b=np.roll(p,-1,axis=0)
 return bool(np.count_nonzero(((a[:,1]>q[1])!=(b[:,1]>q[1]))&(q[0]<(b[:,0]-a[:,0])*(q[1]-a[:,1])/(b[:,1]-a[:,1]+1e-30)+a[:,0]))%2)

def bodies(loops):
 loops=sorted(loops,key=lambda x:-abs(area(x)));out=[]
 for p in loops:
  parents=[i for i,b in enumerate(out) if inside(p[0],b[0])]
  if parents:out[parents[-1]].append(p)
  else:out.append([p])
 return out

def endpoint(atlas,box):
 loops=[]
 for item in box['items']:
  if item['kind']=='glyph':
   f=atlas.field(item['key']);plane=np.array(atlas.data['tiles'][item['key']]['plane']);step=(plane[2:]-plane[:2])/np.array(f.shape[::-1])
   for p in contourpy.contour_generator(z=f).lines(0):loops.append(((p+.5)*step+plane[:2])*[item.get('sx',1),item.get('sy',1)]+[item['x'],item['y']])
  elif item['kind']=='rule':
   x,y,w,h=[item[k] for k in ['x','y','width','height']];loops.append(np.array([[x,y],[x+w,y],[x+w,y+h],[x,y+h]]))
  else:raise ValueError(('Unsupported endpoint primitive',item))
 return bodies(loops)

def fit(a,b):
 clouds=[np.concatenate([p for body in scene for p in body]) for scene in [a,b]]
 bounds=[(p.min(0),p.max(0)) for p in clouds]
 scale=min(1000/max((hi-lo)[0] for lo,hi in bounds),340/max((hi-lo)[1] for lo,hi in bounds))
 result=[]
 for scene,(lo,hi) in zip([a,b],bounds):result.append([[resample((p-(lo+hi)/2)*scale) for p in body] for body in scene])
 return result

class Scene:
 def __init__(self,a,b):
  if len(a)!=len(b):raise ValueError(('Branching required',len(a),len(b)))
  self.source=a;self.target=b
  center=lambda body:(np.concatenate(body).min(0)+np.concatenate(body).max(0))/2
  ca=np.array([center(x) for x in a]);cb=np.array([center(x) for x in b]);cost=np.linalg.norm(ca[:,None,:]-cb[None,:,:],axis=2)
  for i,x in enumerate(a):
   for j,y in enumerate(b):
    if len(x)!=len(y):cost[i,j]=1e9
    else:
     u=normalize([p-ca[i] for p in x]);v=normalize([p-cb[j] for p in y])
     exact=all(np.max(abs(p-q))<.05 for p,q in zip(u,v))
     if not exact:cost[i,j]+=500
  rows,cols=linear_sum_assignment(cost)
  if any(cost[i,j]>1e8 for i,j in zip(rows,cols)):raise ValueError('Per-body hole topology needs a different planner')
  self.parts=[]
  for i,j in zip(rows,cols):
   x=[p-ca[i] for p in a[i]];y=[p-cb[j] for p in b[j]];plan=Transport(x,y)
   original=np.concatenate(plan.a);target=np.concatenate(plan.b)
   u,_,vt=np.linalg.svd(original.T@target);rotation=u@vt
   scale=float(np.sum((original@rotation)*target)/np.sum(original*original))
   rigid=np.max(abs(scale*original@rotation-target))<.1 and np.linalg.det(rotation)>0
   angle=float(np.arctan2(rotation[0,1],rotation[0,0]))
   self.parts.append((plan,ca[i],cb[j],rigid,angle,scale))
  self.expected=(len(a),sum(len(x)-1 for x in a))
 def contours(self,t):
  v=clock(t);out=[]
  for plan,a,b,rigid,angle,scale in self.parts:
   theta=v*angle;rotation=np.array([[np.cos(theta),np.sin(theta)],[-np.sin(theta),np.cos(theta)]])
   loops=[p@rotation*((1-v)+v*scale) for p in plan.a] if rigid else plan.contours(t)
   out.append([p+(1-v)*a+v*b for p in loops])
  return out

def draw_scene(scene,ss=4):
 canvas=np.zeros((720,1280),np.uint8)
 for loops in scene:
  points=np.concatenate(loops)+[640,360];lo=np.floor(points.min(0)).astype(int)-3;hi=np.ceil(points.max(0)).astype(int)+4;w,h=hi-lo
  if np.any(lo<0) or hi[0]>1280 or hi[1]>720:raise ValueError('Scene outside frame')
  im=Image.new('L',(w*ss,h*ss));draw=ImageDraw.Draw(im)
  for i,p in enumerate(loops):draw.polygon([tuple(q) for q in (p+[640,360]-lo)*ss],fill=255 if i==0 else 0)
  mask=np.array(im.resize((w,h),Image.Resampling.LANCZOS));x,y=lo;old=canvas[y:y+h,x:x+w]
  if np.any((old>127)&(mask>127)):raise ValueError('Unrelated body overlap')
  np.maximum(old,mask,out=old)
 return canvas

def check(scene,expected):
 for body in scene:
  for i,p in enumerate(body):
   if crossings(p,p,True):raise ValueError('Self crossing')
   for q in body[:i]:
    if crossings(p,q):raise ValueError('Hole crossing')
 im=draw_scene(scene)
 if topology(im>127)!=expected:raise ValueError(('Topology changed',topology(im>127),expected))
 return im
