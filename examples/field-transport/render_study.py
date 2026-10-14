"""Native scalar-field topology study; no KaTeX or raster-distance reconstruction."""
import argparse,json,subprocess,hashlib
from pathlib import Path
import numpy as np
from field_transport import Atlas,Transport,ring,raster,topology,area,crossings
p=argparse.ArgumentParser();p.add_argument('atlas',type=Path);p.add_argument('out',type=Path);args=p.parse_args();args.out.mkdir(parents=True,exist_ok=True)
atlas=Atlas(args.atlas);cases=[('01-ring-D',ring(),atlas.loops('display/D')),('02-O-D',atlas.loops('display/O'),atlas.loops('display/D')),('03-8-B',atlas.loops('display/8'),atlas.loops('display/B')),('04-0-D',atlas.loops('display/0'),atlas.loops('display/D'))];receipts=[]
for name,a,b in cases:
 plan=Transport(a,b);frames=[];rows=[];previous=None
 for k,t in enumerate(np.linspace(0,1,312)):
  loops=plan.contours(float(t))
  for i,x in enumerate(loops):
   assert not crossings(x,x,True),(name,k,'self intersection')
   for y in loops[:i]:assert not crossings(x,y),(name,k,'boundary crossing')
  alpha=raster(loops);assert topology(alpha>127)==plan.expected,(name,k,'hole/component change',topology(alpha>127))
  frames.append(alpha)
  rows.append(dict(t=float(t),areas=[float(area(x)) for x in loops],boundary_step=0 if previous is None else max(float(np.linalg.norm(x-y,axis=1).max()) for x,y in zip(loops,previous))))
  previous=loops
  if k%80==0:print(name,k,plan.expected,flush=True)
 video=args.out/(name+'.mp4');ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','60','-i','-','-an','-c:v','libx264','-preset','fast','-crf','3','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
 for im in [frames[0]]*24+frames+[frames[-1]]*24:
  rgb=np.empty((720,1280,3),np.uint8);rgb[:]=[16,25,25]
  rgb[104:616,384:896]=np.uint8(np.rint(np.array([16,25,25])+im[:,:,None]/255*np.array([221,218,212])))
  ff.stdin.write(rgb.tobytes())
 ff.stdin.close();assert ff.wait()==0
 decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE);topologies=[];ious={}
 for k in range(360):
  raw=decoder.stdout.read(720*1280*3);assert len(raw)==720*1280*3
  rgb=np.frombuffer(raw,np.uint8).reshape(720,1280,3);mask=rgb[104:616,384:896,0]>126
  got=topology(mask);assert got==plan.expected,(name,k,'encoded topology',got);topologies.append(got)
  if k in [0,24,335,359]:
   want=frames[0 if k<25 else -1]>127;iou=float((want&mask).sum()/(want|mask).sum());assert iou>.995,(name,k,'endpoint',iou);ious[k]=iou
 assert not decoder.stdout.read(1);assert decoder.wait()==0
 masses=np.array([r['areas'][0]-sum(r['areas'][1:]) for r in rows]);delta=np.diff(masses);assert np.all(delta>=-1e-7) or np.all(delta<=1e-7)
 receipt=dict(case=name,scalar_fields=atlas.provenance,topology=plan.expected,motion_frames=312,decoded_frames=360,topology_violations=0,boundary_crossings=0,endpoint_iou=ious,polygon_area_monotone=True,max_boundary_step=max(r['boundary_step'] for r in rows),sha256=hashlib.sha256(video.read_bytes()).hexdigest(),rows=rows)
 (args.out/(name+'-verification.json')).write_text(json.dumps(receipt,indent=2)+'\n');np.savez_compressed(args.out/(name+'-frames.npz'),frames=np.array(frames));receipts.append({k:v for k,v in receipt.items() if k!='rows'})
 print('PASS',name,receipt['max_boundary_step'],flush=True)
listing=args.out/'concat.txt';listing.write_text(''.join(f"file '{name}.mp4'\n" for name,_,_ in cases))
movie=args.out/'field-topology-2x.mp4';subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(movie)],check=True)
(args.out/'verification.json').write_text(json.dumps(dict(cases=receipts,sha256=hashlib.sha256(movie.read_bytes()).hexdigest(),seconds=24,fps=60,limitations=['Same topology, one exterior with holes only; no general branching solution','Quantized native scalar field contours, not exact analytic font curves','CPU transport and video; no new physical GPU or compiler integration']),indent=2)+'\n')
