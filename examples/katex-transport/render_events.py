"""Clean image-only budding/absorption movies. No state overlays or still previews."""
import json,sys,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from coverage_transport import plan_coverage_pair,event_states,related_events
from pixel_transport import rotation

folder=Path(sys.argv[1]);W,H=1280,720;pixel_scale=3
cases=sys.argv[2:] or ['03-factor','04-square','05-difference','06-cancel','07-collect','08-fraction']

def warp(part,center,angle,scale,size,factor):
    R=rotation(angle);K=center-R@(factor*part.region.center)*scale
    inverse=R.T/(scale*factor/pixel_scale);v=-inverse@K-part.origin
    coefficients=(*inverse[0],v[0],*inverse[1],v[1])
    return np.asarray(part.bitmap.transform(size,Image.Transform.AFFINE,coefficients,resample=Image.Resampling.BICUBIC))/255

def layers(plan,t,route,size=(W,H),factor=3,offset=None):
    if offset is None:offset=np.array([W/2-480*factor,H/2-270*factor])
    result=[]
    for e in event_states(plan,t,route['detour'],route['event_lift']):
        if e['opacity']<=0:continue
        center=e['center']*factor+offset
        if e['kind']=='matched':
            left=warp(plan['source'][e['source']],center,e['source_angle'],1,size,factor)
            right=warp(plan['target'][e['target']],center,e['target_angle'],1,size,factor)
            coverage=(1-e['blend'])*left+e['blend']*right
        else:
            part=plan['target'][e['target']] if e['kind']=='birth' else plan['source'][e['source']]
            coverage=warp(part,center,0,e['scale'],size,factor)*e['opacity']
        result.append((e,coverage))
    return result

def path_score(plan,route):
    overlap=0.;clipping=0.
    for t in np.linspace(.04,.96,13):
        active=layers(plan,float(t),route,(320,180),1/3,np.array([0.,0.]))
        for i,(event,coverage) in enumerate(active):
            # Visible crop in the final 1280x720 movie, in preview coordinates.
            clipping+=coverage.sum()-coverage[50:130,89:231].sum()
            for other,mask in active[:i]:
                if not related_events(event,other):overlap+=float((coverage*mask).sum())
    return dict(overlap=overlap,clipping=clipping,cost=overlap+100*clipping+.0005*(route['detour']**2+route['event_lift']**2))

def choose_route(plan):
    best=None;baseline=None
    for detour in [0,16,-16,32,-32]:
        for lift in [0,16,-16,32,-32]:
            route=dict(detour=detour,event_lift=lift);score=path_score(plan,route)
            if detour==lift==0:baseline=score
            if best is None or score['cost']<best[1]['cost']:best=(route,score)
    return best[0],dict(baseline=baseline,selected=best[1],samples=13,candidates=25)

receipts=[]
for name in cases:
    source=np.array(Image.open(folder/(name+'-from.png')).convert('L'))/255
    target=np.array(Image.open(folder/(name+'-to.png')).convert('L'))/255
    plan=plan_coverage_pair(source,target,pixel_scale)
    for part in plan['source']+plan['target']:part.bitmap=Image.fromarray(np.uint8(np.round(part.patch*255)))
    route,search=choose_route(plan)
    print(name,route,'unrelated overlap score',round(search['baseline']['overlap'],2),'->',round(search['selected']['overlap'],2),flush=True)
    ff=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(folder/(name+'-budding.mp4'))],stdin=subprocess.PIPE)
    endpoint_errors=[];max_overlap=0;mass=[];max_unrelated=0
    for frame in range(180):
        t=max(0,min(1,(frame-15)/149));total=np.zeros((H,W),float);occupied=np.zeros((H,W),int)
        active=layers(plan,t,route)
        for i,(event,coverage) in enumerate(active):
            for other,mask in active[:i]:
                if not related_events(event,other):max_unrelated=max(max_unrelated,int(np.count_nonzero((coverage>.1)&(mask>.1))))
            occupied+=(coverage>.1);total=1-(1-total)*(1-coverage)
        max_overlap=max(max_overlap,int(np.count_nonzero(occupied>1)));mass.append(float(total.sum()/pixel_scale**2))
        rgb=np.array([16,25,25])[None,None,:]+total[:,:,None]*np.array([221,218,212])[None,None,:]
        image=Image.fromarray(np.uint8(np.clip(rgb,0,255)))
        if frame in [0,179]:
            original=source if frame==0 else target
            crop=original[810-H//2:810+H//2,1440-W//2:1440+W//2]
            error=float(np.max(np.abs(total-crop)));endpoint_errors.append(error)
            assert error<=1/255+1e-9,(name,'endpoint mismatch',error)
        ff.stdin.write(image.tobytes())
    ff.stdin.close();assert ff.wait()==0
    receipts.append(dict(case=name,route=route,search=search,matches=plan['mapping']['matches'],birth_parents=plan['birth_parents'],death_parents=plan['death_parents'],endpoint_max_errors=endpoint_errors,observed_total_overlap_pixels=max_overlap,observed_unrelated_pair_overlap_pixels=max_unrelated,rendered_coverage_range=[min(mass),max(mass)],policy='Fade, scale and move together; image-inferred budding/absorption parents; contact permitted inside event families; sampled overlap minimization, not collision-free or conservative transport',duration=6))
    (folder/'budding-verification.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('Rendered',name,'unrelated overlap pixels',max_unrelated,flush=True)
(folder/'budding-concat.txt').write_text(''.join("file '%s-budding.mp4'\n"%name for name in cases))
