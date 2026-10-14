"""Render endpoint-only event plans as one visible KaTeX expression per frame."""
import json,sys,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from coverage_transport import plan_coverage_pair,event_states
from pixel_transport import rotation

folder=Path(sys.argv[1]);W,H=1280,720;pixel_scale=3
cases=sys.argv[2:] or ['03-factor','04-square','05-difference','06-cancel','07-collect','08-fraction']

def warp(part,center,angle,scale):
    if scale<=1e-8:return np.zeros((H,W),float)
    patch=Image.fromarray(np.uint8(np.round(part.patch*255)))
    R=rotation(angle);K=center-R@(pixel_scale*part.region.center)*scale
    inverse=R.T/scale;v=-inverse@K-part.origin
    coefficients=(*inverse[0],v[0],*inverse[1],v[1])
    return np.asarray(patch.transform((W,H),Image.Transform.AFFINE,coefficients,resample=Image.Resampling.BICUBIC))/255

receipts=[]
for name in cases:
    source=np.array(Image.open(folder/(name+'-from.png')).convert('L'))/255
    target=np.array(Image.open(folder/(name+'-to.png')).convert('L'))/255
    plan=plan_coverage_pair(source,target,pixel_scale)
    route=dict(detour=0,event_lift=0)
    print(name,'matched',len(plan['mapping']['matches']),'births',len(plan['mapping']['unmatched_target']),'deaths',len(plan['mapping']['unmatched_source']),flush=True)
    ff=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(folder/(name+'-events.mp4'))],stdin=subprocess.PIPE)
    endpoint_errors=[];max_overlap=0;mass=[]
    for frame in range(180):
        t=max(0,min(1,(frame-15)/149));total=np.zeros((H,W),float);occupied=np.zeros((H,W),int)
        for e in event_states(plan,t,route['detour'],route['event_lift']):
            center=e['center']*pixel_scale+np.array([W/2-480*pixel_scale,H/2-270*pixel_scale])
            if e['kind']=='matched':
                left=warp(plan['source'][e['source']],center,e['source_angle'],1)
                right=warp(plan['target'][e['target']],center,e['target_angle'],1)
                coverage=(1-e['blend'])*left+e['blend']*right
            elif e['kind']=='birth':coverage=warp(plan['target'][e['target']],center,0,e['scale'])
            else:coverage=warp(plan['source'][e['source']],center,0,e['scale'])
            occupied+=(coverage>.5);total=1-(1-total)*(1-coverage)
        max_overlap=max(max_overlap,int(np.count_nonzero(occupied>1)));mass.append(float(total.sum()/pixel_scale**2))
        rgb=np.array([16,25,25])[None,None,:]+total[:,:,None]*np.array([221,218,212])[None,None,:]
        image=Image.fromarray(np.uint8(np.clip(rgb,0,255)))
        if frame in [0,60,90,179]:image.save(folder/(name+f'-events-check-{frame}.png'))
        if frame in [0,179]:
            original=source if frame==0 else target
            crop=original[810-H//2:810+H//2,1440-W//2:1440+W//2]
            error=float(np.max(np.abs(total-crop)));endpoint_errors.append(error)
            assert error<=1/255+1e-9,(name,'endpoint mismatch',error)
        ff.stdin.write(image.tobytes())
    ff.stdin.close();assert ff.wait()==0
    receipts.append(dict(case=name,route=route,matches=plan['mapping']['matches'],births=plan['mapping']['unmatched_target'],deaths=plan['mapping']['unmatched_source'],endpoint_max_errors=endpoint_errors,observed_overlap_pixels=max_overlap,rendered_coverage_range=[min(mass),max(mass)],policy='Explicit appearance/removal: quintic scale for unmatched regions, aligned coverage interpolation for matched residuals; no mass-conservation or collision-free claim',duration=6))
    (folder/'event-verification.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('Rendered',name,'overlap',max_overlap,flush=True)
(folder/'event-concat.txt').write_text(''.join("file '%s-events.mp4'\n"%name for name in cases))
