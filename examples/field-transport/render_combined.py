"""Verified combined foreground scenes, 3 seconds per example at 60 fps."""
import argparse,json,subprocess,hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw
from combined_transport import CombinedScene
from field_transport import topology,clock
from scene_transport import draw_scene

def linear(rgb):
 x=np.asarray(rgb,dtype=float)/255
 return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def srgb(x):return np.uint8(np.rint(np.clip(np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0)**(1/2.4)-.055)*255,0,255)))
p=argparse.ArgumentParser();p.add_argument('inputs',type=Path);p.add_argument('out',type=Path);p.add_argument('--cases',nargs='*');args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
palette=[(70,220,245),(255,150,85),(190,130,255),(120,235,140)];receipts=[]
for item in json.loads(args.inputs.read_text()):
 if args.cases and item['id'] not in args.cases:continue
 name=item['id'];a,b=[[[np.array(p) for p in body] for body in side] for side in item['geometry']];assert min(item['glyph_counts'])>=6
 plan=CombinedScene(a,b);background=Image.new('RGB',(1280,720),(16,25,25));draw=ImageDraw.Draw(background)
 for x,y,X,Y in item['background']:draw.line((x+640,y+360,X+640,Y+360),fill=(37,49,49),width=1)
 background=linear(np.array(background));video=args.out/(name+'.mp4');counts=[];holes=[];areas=[];changes=[];hashes=[];endpoint_iou=[]
 ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','60','-i','-','-an','-c:v','libx264rgb','-preset','fast','-crf','0','-pix_fmt','rgb24','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
 try:
  for k,t in enumerate(np.linspace(0,1,156)):
   ims,metrics=plan.images(float(t));coverage=np.max(ims,axis=0);n,h=topology(coverage>127)
   assert h==plan.expected_holes,(name,k,'holes',h)
   if counts:assert n>=counts[-1] if len(a)<len(b) else n<=counts[-1] if len(a)>len(b) else n==counts[-1],(name,k,'count',counts[-1],n)
   counts.append(n);holes.append(h);areas.append([m[2] for m in metrics])
   if k:changes.append(float(np.abs(coverage.astype(float)-previous).sum()/255))
   previous=coverage.copy()
   if k in [0,155]:
    truth=draw_scene(a if k==0 else b,ss=8)>127;actual=coverage>127
    assert not np.any(actual&~ndi.binary_dilation(truth)) and not np.any(ndi.binary_erosion(truth)&~actual),(name,k,'endpoint mismatch')
    endpoint_iou.append(float((actual&truth).sum()/(actual|truth).sum()))
   rgb=background.copy();v=clock(t)
   for j,im in enumerate(ims):
    color=(1-v)*linear(palette[j%4])+v*linear(palette[(j+1)%4]);yy,xx=np.nonzero(im);x,X=xx.min(),xx.max()+1;y,Y=yy.min(),yy.max()+1;alpha=im[y:Y,x:X,None]/255
    rgb[y:Y,x:X]=rgb[y:Y,x:X]*(1-alpha)+color*alpha
   rgb=srgb(rgb);raw=rgb.tobytes();repeat=13 if k in [0,155] else 1
   for _ in range(repeat):ff.stdin.write(raw);hashes.append(hashlib.sha256(raw).hexdigest())
   if k in [0,39,78,117,155]:Image.fromarray(rgb).save(args.out/f'{name}-{k:03}.png')
   if k%40==0:print(name,k,flush=True)
 finally:
  ff.stdin.close();status=ff.wait()
 assert status==0 and len(hashes)==180
 dec=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
 for k,want in enumerate(hashes):
  raw=dec.stdout.read(720*1280*3);assert hashlib.sha256(raw).hexdigest()==want,(name,k,'encoded pixels differ')
 assert not dec.stdout.read(1);assert dec.wait()==0
 receipt=dict(case=name,frames=180,fps=60,duration=3,glyph_counts=item['glyph_counts'],counts=counts,holes=holes,areas=areas,coverage_changes=changes,endpoint_iou=endpoint_iou,kinds=[k for k,p in plan.groups],sha256=hashlib.sha256(video.read_bytes()).hexdigest(),decoded_frames_exact=True)
 (args.out/(name+'-verification.json')).write_text(json.dumps(receipt,indent=2));receipts.append(receipt);print('PASS',name,flush=True)
(args.out/'verification.json').write_text(json.dumps(receipts,indent=2))
