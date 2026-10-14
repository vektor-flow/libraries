"""Color-blend preview using the verified, unchanged native-field silhouettes."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import numpy as np
from field_transport import clock,topology

def linear(rgb):
 x=np.asarray(rgb,dtype=float)/255
 return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def srgb(x):
 return np.clip(np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0)**(1/2.4)-.055)*255,0,255)

p=argparse.ArgumentParser();p.add_argument('verified',type=Path);p.add_argument('out',type=Path);args=p.parse_args();args.out.mkdir(parents=True,exist_ok=False)
cases=[('01-ring-D',[65,215,245],[255,110,130]),('02-O-D',[243,108,203],[255,211,83]),('03-8-B',[105,145,255],[138,238,107]),('04-0-D',[182,123,255],[64,224,193])]
bg=np.array([16,25,25]);background=linear(bg);receipts=[]
for name,start,end in cases:
 source=args.verified/(name+'-frames.npz');frames=np.load(source)['frames'];prior=json.loads((args.verified/(name+'-verification.json')).read_text())
 times=np.r_[np.zeros(24),np.linspace(0,1,len(frames)),np.ones(24)]
 indices=np.r_[np.zeros(24,dtype=int),np.arange(len(frames)),np.full(24,len(frames)-1,dtype=int)]
 colors=np.array([(1-clock(t))*linear(start)+clock(t)*linear(end) for t in times])
 video=args.out/(name+'.mp4')
 ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','60','-i','-','-an','-c:v','libx264','-preset','fast','-crf','3','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
 for index,color in zip(indices,colors):
  alpha=frames[index].astype(float)[:,:,None]/255
  rgb=np.empty((720,1280,3),np.uint8);rgb[:]=bg
  rgb[104:616,384:896]=np.uint8(np.rint(srgb(background+alpha*(color-background))))
  ff.stdin.write(rgb.tobytes())
 ff.stdin.close();assert ff.wait()==0
 decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
 ious=[];errors=[]
 for k,(index,color) in enumerate(zip(indices,colors)):
  raw=decoder.stdout.read(720*1280*3);assert len(raw)==720*1280*3
  rgb=np.frombuffer(raw,np.uint8).reshape(720,1280,3)[104:616,384:896]
  weights=np.array([.299,.587,.114])
  threshold=float(np.dot(srgb((background+color)/2),weights))
  mask=np.sum(rgb*weights,axis=2)>threshold;assert topology(mask)==tuple(prior['topology']),(name,k,topology(mask))
  want=frames[index]>127;iou=float((want&mask).sum()/(want|mask).sum());ious.append(iou)
  solid=frames[index]==255;error=float(np.max(abs(np.median(rgb[solid],axis=0)-srgb(color))));errors.append(error)
  assert iou>.99,(name,k,'silhouette',iou)
  assert error<4,(name,k,'color',error)
 assert not decoder.stdout.read(1);assert decoder.wait()==0
 receipt=dict(case=name,start_srgb=start,end_srgb=end,interpolation='linear-light RGB, quintic eased; linear-light coverage compositing',unchanged_geometry_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),topology=prior['topology'],decoded_frames=len(times),minimum_silhouette_iou=min(ious),maximum_interior_color_error_srgb=max(errors),sha256=hashlib.sha256(video.read_bytes()).hexdigest())
 receipts.append(receipt);(args.out/(name+'-verification.json')).write_text(json.dumps(receipt,indent=2)+'\n');print('PASS',receipt,flush=True)
listing=args.out/'concat.txt';listing.write_text(''.join(f"file '{name}.mp4'\n" for name,_,_ in cases))
movie=args.out/'field-color-blends-2x.mp4';subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(movie)],check=True)
(args.out/'verification.json').write_text(json.dumps(dict(cases=receipts,seconds=24,fps=60,sha256=hashlib.sha256(movie.read_bytes()).hexdigest(),scope='Color interpolation on unchanged verified silhouettes; not spatial pigment or material mixing'),indent=2)+'\n')
