"""Render and verify distinct endpoint-only transport families; no semantic matching."""
import argparse,json,subprocess,hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from field_transport import clock,topology,crossings,Transport
from scene_transport import draw_scene
from replica_transport import ReplicaScene
from affine_transport import AffineTransport
from registered_transport import RegisteredTransport
from rigid_routes import RoutedScene
from plan_transport import plan_transport

def linear(rgb):
 x=np.asarray(rgb,dtype=float)/255
 return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def srgb(x):return np.clip(np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0)**(1/2.4)-.055)*255,0,255)
p=argparse.ArgumentParser();p.add_argument('inputs',type=Path);p.add_argument('out',type=Path);p.add_argument('--cases',nargs='*');args=p.parse_args();args.out.mkdir(exist_ok=True)
items=json.loads(args.inputs.read_text());bg=np.array([16,25,25]);back=linear(bg);receipts=[]
palettes=[([65,215,245],[255,110,130]),([243,108,203],[255,211,83]),([105,145,255],[138,238,107]),([182,123,255],[64,224,193])]
for index,item in enumerate(items):
 name=item['id']
 if args.cases and name not in args.cases:continue
 try:
  cache=args.out/(name+'-frames.npz');metrics=args.out/(name+'-geometry.json')
  if cache.exists() and metrics.exists():frames=np.load(cache)['frames'];geometry=json.loads(metrics.read_text())
  else:
   a,b=[[[np.asarray(p,dtype=float) for p in body] for body in side] for side in item['geometry']]
   mode,plan=plan_transport(a,b)
   frames=[];counts=[];holes=[];areas=[];changes=[]
   for k,t in enumerate(np.linspace(0,1,312)):
    if mode=='replica':im,mass=plan.image(float(t))
    else:
     bodies=plan.contours(float(t)) if mode=='route' else [plan.contours(float(t))]
     if mode!='route':
      for body in bodies:
       for j,p in enumerate(body):
        assert not crossings(p,p,True),(name,k,'self crossing')
        for q in body[:j]:assert not crossings(p,q),(name,k,'hole crossing')
     im=draw_scene(bodies,ss=8);mass=[float(im.sum()/255)]
    n,h=topology(im>127)
    if mode=='replica':
     assert h==0 and min(len(a),len(b))<=n<=max(len(a),len(b))
     if counts:assert n>=counts[-1] if len(a)<len(b) else n<=counts[-1]
    else:assert (n,h)==plan.expected,(name,k,(n,h),plan.expected)
    if frames:changes.append(float(np.abs(im.astype(float)-frames[-1]).sum()/255))
    frames.append(im);counts.append(n);holes.append(h);areas.append(mass)
    if k%100==0:print(name,k,flush=True)
   assert (counts[0],counts[-1])==(len(a),len(b))
   endpoint_ious=[]
   for actual,want in [(frames[0],draw_scene(a,ss=8)),(frames[-1],draw_scene(b,ss=8))]:
    mask=actual>127;truth=want>127
    assert not np.any(mask&~ndi.binary_dilation(truth)) and not np.any(ndi.binary_erosion(truth)&~mask),'Endpoint error beyond one pixel'
    endpoint_ious.append(float((mask&truth).sum()/(mask|truth).sum()))
   geometry=dict(counts=counts,holes=holes,areas=areas,coverage_changes=changes,endpoint_iou=endpoint_ious,scope=mode+' endpoint-inferred research candidate')
   frames=np.array(frames);np.savez_compressed(cache,frames=frames);metrics.write_text(json.dumps(geometry)+'\n')
  start,end=palettes[index%4];times=np.r_[np.zeros(24),np.linspace(0,1,312),np.ones(24)];indices=np.r_[np.zeros(24,dtype=int),np.arange(312),np.full(24,311,dtype=int)]
  colors=[(1-clock(t))*linear(start)+clock(t)*linear(end) for t in times];video=args.out/(name+'.mp4')
  ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','60','-i','-','-an','-c:v','libx264rgb','-preset','fast','-crf','0','-pix_fmt','rgb24','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
  for i,color in zip(indices,colors):
   im=frames[i];yy,xx=np.nonzero(im);lo=np.array([xx.min(),yy.min()]);hi=np.array([xx.max()+1,yy.max()+1]);x,y=lo;X,Y=hi
   rgb=np.empty((720,1280,3),np.uint8);rgb[:]=bg
   rgb[y:Y,x:X]=np.uint8(np.rint(srgb(back+im[y:Y,x:X,None]/255*(color-back))))
   ff.stdin.write(rgb.tobytes())
  ff.stdin.close();assert ff.wait()==0
  dec=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE);ious=[]
  for k,(i,color) in enumerate(zip(indices,colors)):
   raw=dec.stdout.read(720*1280*3);assert len(raw)==720*1280*3
   rgb=np.frombuffer(raw,np.uint8).reshape(720,1280,3);weights=np.array([.299,.587,.114]);mask=np.sum(rgb*weights,axis=2)>float(srgb((back+color)/2)@weights)
   assert topology(mask)==(geometry['counts'][i],geometry['holes'][i]),(name,k,'encoded topology',topology(mask))
   want=frames[i]>127;iou=float((want&mask).sum()/(want|mask).sum());ious.append(iou)
   assert not np.any(mask&~ndi.binary_dilation(want)) and not np.any(ndi.binary_erosion(want)&~mask),(name,k,'encoded displacement exceeds one boundary pixel')
  assert not dec.stdout.read(1);assert dec.wait()==0
  receipt=dict(case=name,frames=360,minimum_iou=min(ious),source_counts=[geometry['counts'][0],geometry['counts'][-1]],holes=[geometry['holes'][0],geometry['holes'][-1]],scope=geometry['scope'],sha256=hashlib.sha256(video.read_bytes()).hexdigest())
  (args.out/(name+'-verification.json')).write_text(json.dumps(receipt,indent=2)+'\n');receipts.append(receipt);print('PASS',receipt,flush=True)
 except Exception as exc:
  (args.out/(name+'-failure.json')).write_text(json.dumps(dict(error=repr(exc)))+'\n');print('FAIL',name,repr(exc),flush=True)

(args.out/'verification.json').write_text(json.dumps(dict(cases=receipts,input_sha256=hashlib.sha256(args.inputs.read_bytes()).hexdigest()),indent=2)+'\n')
expected=sum(1 for c in items if not args.cases or c['id'] in args.cases)
if len(receipts)!=expected:raise SystemExit('Some cases rejected; see failure receipts')
