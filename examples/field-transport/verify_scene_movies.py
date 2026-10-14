"""Decoded topology and resolution-aware one-pixel boundary displacement check."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from field_transport import clock,topology
p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('cases',nargs='*');args=p.parse_args()
all_cases=['sentence','powers','fraction','mixed','division','fusion']
palettes=[([65,215,245],[255,110,130]),([243,108,203],[255,211,83]),([105,145,255],[138,238,107]),([182,123,255],[64,224,193])]
def linear(rgb):
 x=np.asarray(rgb,dtype=float)/255;return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def srgb(x):return np.clip(np.where(x<=.0031308,12.92*x,1.055*np.maximum(x,0)**(1/2.4)-.055)*255,0,255)
back=linear([16,25,25]);receipts=[]
for name in args.cases or all_cases:
 index=all_cases.index(name);start,end=palettes[index%4];frames=np.load(args.out/(name+'-frames.npz'))['frames'];geometry=json.loads((args.out/(name+'-geometry.json')).read_text());video=args.out/(name+'.mp4')
 times=np.r_[np.zeros(24),np.linspace(0,1,312),np.ones(24)];indices=np.r_[np.zeros(24,dtype=int),np.arange(312),np.full(24,311,dtype=int)]
 dec=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE);ious=[]
 for k,(t,i) in enumerate(zip(times,indices)):
  raw=dec.stdout.read(720*1280*3);assert len(raw)==720*1280*3
  rgb=np.frombuffer(raw,np.uint8).reshape(720,1280,3);color=(1-clock(t))*linear(start)+clock(t)*linear(end);weights=np.array([.299,.587,.114]);mask=np.sum(rgb*weights,axis=2)>float(srgb((back+color)/2)@weights)
  assert topology(mask)==(geometry['counts'][i],geometry['holes'][i]),(name,k,'topology',topology(mask))
  want=frames[i]>127;ious.append(float((want&mask).sum()/(want|mask).sum()))
  assert not np.any(mask&~ndi.binary_dilation(want)) and not np.any(ndi.binary_erosion(want)&~mask),(name,k,'more than one pixel boundary displacement')
 assert not dec.stdout.read(1);assert dec.wait()==0
 receipt=dict(case=name,frames=360,minimum_iou=min(ious),boundary_displacement_limit_pixels=1,source_counts=[geometry['counts'][0],geometry['counts'][-1]],holes=[geometry['holes'][0],geometry['holes'][-1]],scope=geometry['scope'],sha256=hashlib.sha256(video.read_bytes()).hexdigest())
 (args.out/(name+'-verification.json')).write_text(json.dumps(receipt,indent=2)+'\n');print('PASS',receipt,flush=True)
