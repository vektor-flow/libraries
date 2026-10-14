import argparse,json,subprocess,hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from field_transport import Atlas,clock,topology,crossings,ring
from scene_transport import endpoint,fit,Scene,draw_scene
from division_field import division

def linear(rgb):
 x=np.asarray(rgb,dtype=float)/255
 return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def srgb(x):return np.clip(np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0)**(1/2.4)-.055)*255,0,255)
p=argparse.ArgumentParser();p.add_argument('atlas',type=Path);p.add_argument('layouts',type=Path);p.add_argument('out',type=Path);p.add_argument('--cases',nargs='*');args=p.parse_args();args.out.mkdir(exist_ok=True)
atlas=Atlas(args.atlas);layouts=json.loads(args.layouts.read_text());bg=np.array([16,25,25]);back=linear(bg);receipts=[]
palettes=[([65,215,245],[255,110,130]),([243,108,203],[255,211,83]),([105,145,255],[138,238,107]),([182,123,255],[64,224,193])]
all_cases=['sentence','powers','fraction','mixed','division','fusion']
for index,name in enumerate(all_cases):
 if args.cases and name not in args.cases:continue
 try:
  cache=args.out/(name+'-frames.npz');metrics=args.out/(name+'-geometry.json')
  if cache.exists() and metrics.exists():frames=np.load(cache)['frames'];geometry=json.loads(metrics.read_text())
  else:
   frames=[];counts=[];holes=[];areas=[]
   if name not in ['division','fusion']:
    item=next(c for c in layouts if c['id']==name)
    a,b=fit(endpoint(atlas,item['from']),endpoint(atlas,item['to']))
    if name=='sentence':
     a,_=fit(endpoint(atlas,item['from']),endpoint(atlas,item['from']));b=[]
     for body in a:
      cloud=np.concatenate(body);center=(cloud.min(0)+cloud.max(0))/2
      b.append([q+[0,65*np.cos(center[0]/500*np.pi)] for q in body])
    if name=='mixed':
     # Replace only the source annulus geometry with an analytic ring.
     hole=next(i for i,body in enumerate(a) if len(body)==2);cloud=np.concatenate(a[hole]);center=(cloud.min(0)+cloud.max(0))/2;radius=(cloud.max(0)-cloud.min(0))[1]/2
     a[hole]=[q+center for q in ring(radius,radius*.18)]
    scene=Scene(a,b)
   previous=None
   for k,t in enumerate(np.linspace(0,1,312)):
    if name in ['division','fusion']:
     im,mass=division(float(t if name=='division' else 1-t));areas.append(mass)
    else:
     bodies=scene.contours(float(t))
     for i,body in enumerate(bodies):
      if scene.parts[i][3] and k not in [0,311]:continue
      for j,p in enumerate(body):
       assert not crossings(p,p,True),(name,k,'self crossing')
       for q in body[:j]:assert not crossings(p,q),(name,k,'hole crossing')
     im=draw_scene(bodies)
    count,hole_count=topology(im>127)
    if name in ['division','fusion']:
     assert hole_count==0
     if previous is not None:assert count>=previous if name=='division' else count<=previous
     assert count in [1,2]
    else:assert (count,hole_count)==scene.expected,(name,k,(count,hole_count),scene.expected)
    previous=count;frames.append(im);counts.append(count);holes.append(hole_count)
    if k%100==0:print(name,k,flush=True)
   geometry=dict(counts=counts,holes=holes,areas=areas,scope='analytic two-disc fixture' if name in ['division','fusion'] else 'geometry-only same-topology body matching',rigid_bodies=None if name in ['division','fusion'] else int(sum(x[3] for x in scene.parts)))
   if name in ['division','fusion']:assert counts[0]!=counts[-1]
   frames=np.array(frames);np.savez_compressed(cache,frames=frames);metrics.write_text(json.dumps(geometry)+'\n')
  start,end=palettes[index%4];times=np.r_[np.zeros(24),np.linspace(0,1,312),np.ones(24)];indices=np.r_[np.zeros(24,dtype=int),np.arange(312),np.full(24,311,dtype=int)]
  colors=[(1-clock(t))*linear(start)+clock(t)*linear(end) for t in times];video=args.out/(name+'.mp4')
  ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','60','-i','-','-an','-c:v','libx264','-preset','fast','-crf','3','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
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
receipts=[json.loads((args.out/(name+'-verification.json')).read_text()) for name in all_cases if (args.out/(name+'-verification.json')).exists()]
listing=args.out/'concat.txt';listing.write_text(''.join(f"file '{r['case']}.mp4'\n" for r in receipts))
if receipts:
 movie=args.out/'more-field-examples-2x.mp4';subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(movie)],check=True)
 (args.out/'verification.json').write_text(json.dumps(dict(cases=receipts,seconds=len(receipts)*6,fps=60,atlas=atlas.provenance,sha256=hashlib.sha256(movie.read_bytes()).hexdigest()),indent=2)+'\n')
if len(receipts)!=6:raise SystemExit('Some cases rejected; see failure receipts')
