import sys,json,numpy as np
from pathlib import Path
from field_transport import Atlas,ring,resample
from scene_transport import endpoint
from registered_transport import rotation
root=Path(sys.argv[1]);atlas=Atlas(Path(sys.argv[2]));cases=[]
T=np.linspace(0,2*np.pi,128,endpoint=False);unit=np.c_[np.cos(T),np.sin(T)]
def blob(r=65):return [unit*(r*(1+.12*np.cos(3*T)+.07*np.sin(2*T)))[:,None]]
def at(body,c):return [p+np.array(c) for p in body]
def matrix(body,m):return [p@m.T for p in body]
def roundrect(r=95):
 p=np.c_[np.sign(np.cos(T))*abs(np.cos(T))**.5,np.sign(np.sin(T))*abs(np.sin(T))**.5]*r
 return [p,p*.68]
def band(f,xmax=1.5,yscale=45):
 x=np.linspace(-xmax,xmax,512);p=np.c_[x/xmax*430,80-yscale*f(x)]
 return [np.vstack([p+[0,-4],(p+[0,4])[::-1]])]
for item in json.loads((root/'layouts.json').read_text()):
 raw=[endpoint(atlas,item[s]) for s in ['from','to']];clouds=[np.concatenate([p for body in scene for p in body]) for scene in raw];bounds=[(p.min(0),p.max(0)) for p in clouds];scale=min(900/max((b-a)[0] for a,b in bounds),100/max((b-a)[1] for a,b in bounds));a,b=[[[resample((p-(lo+hi)/2)*scale)+[0,-235] for p in body] for body in scene] for scene,(lo,hi) in zip(raw,bounds)]
 name=item['id'];background=[]
 if name in ['power-graph','cubic-quintic','scale-shift']:
  background=[[-480,80,480,80],[0,-155,0,265]]
  for x in [-430,-215,215,430]:background.append([x,-155,x,265])
  for y in [-100,-10,170,260]:background.append([-480,y,480,y])
  if name=='power-graph':
   a.append(band(lambda x:x*x));b.append(band(lambda x:x**3))
   shape=blob(35);a.append(at(shape,[350,270]));b.append(at(matrix(shape,rotation(1.1)),[350,270]))
  elif name=='cubic-quintic':
   a.append(band(lambda x:x**3-x,1.2));b.append(band(lambda x:x**5+x,1.2))
   a.append(at(ring(33,9),[0,280]));b.append(at(roundrect(31),[0,280]))
  else:
   a.append(band(lambda x:2*x*x+1,1.5,37));b.append(band(lambda x:3*x*x-1,1.5,37))
   shape=blob(40);a.append(at(shape,[-300,255]));b.append(at(matrix(shape,np.array([[1.2,.4],[0,.75]])),[300,255]))
 elif name=='mixed-split':
  a.append(at(ring(100,27),[-330,70]));b.append(at(roundrect(91),[-330,70]))
  shape=blob(70);a.append(at(shape,[0,65]));b.extend([at(matrix(shape,np.eye(2)*.65),[-65,90]),at(matrix(shape,np.eye(2)*.65),[65,90])])
  square=[np.array([[-68,-68],[68,-68],[68,68],[-68,68]])];a.append(at(square,[350,70]));b.append(at(matrix(square,rotation(.9)@np.diag([1.1,.8])),[350,70]))
 elif name=='mixed-merge':
  shape=blob(62);a.extend([at(shape,[-390,25]),at(shape,[-230,120])]);b.append(at(matrix(shape,np.eye(2)*1.3),[-310,80]))
  shape=ring(95,24);a.append(at(matrix(shape,np.diag([1.2,.8])),[280,70]));b.append(at(matrix(shape,rotation(.8)@np.diag([1.1,.9])),[280,70]))
 else:
  a.append(at(ring(96,24),[-320,70]));b.append(at(roundrect(88),[-320,70]))
  shape=blob(66);a.append(at(shape,[280,65]));b.extend([at(matrix(shape,np.eye(2)*.65),[220,90]),at(matrix(shape,np.eye(2)*.65),[350,90])])
  shape=blob(37);a.append(at(shape,[0,245]));b.append(at(matrix(shape,rotation(-1.2)),[0,245]))
 cases.append(dict(id=name,source=item['source'],target=item['target'],glyph_counts=[sum(x['kind']=='glyph' for x in item[s]['items']) for s in ['from','to']],geometry=[a,b],background=background))
(root/'inputs.json').write_text(json.dumps(cases,default=lambda a:a.tolist(),indent=2));print([(c['id'],len(c['geometry'][0]),len(c['geometry'][1])) for c in cases])
