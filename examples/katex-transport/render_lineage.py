"""Monotone lineage movies with hard per-frame count and overlap checks."""
import sys,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from lineage_transport import make_plan,frame,motion_quality,smooth_tracks,presentation_alpha
folder=Path(sys.argv[1]);cases=sys.argv[2:] or ['03-factor','04-square','05-difference','06-cancel','07-collect','08-fraction']
receipts=[]
for case in cases:
    a=np.asarray(Image.open(folder/(case+'-from.png')).convert('L'))/255
    b=np.asarray(Image.open(folder/(case+'-to.png')).convert('L'))/255
    plan=make_plan(a,b);state={};images=[];metrics=[]
    print(case,'events',plan['events'],'reverse',plan['reverse'],flush=True)
    passes=[]
    for attempt in range(10):
        state={};images=[];metrics=[]
        for k in range(252):
            t=k/251
            image,metric=frame(plan,t,state);images.append(np.uint8(np.round(image*255)));metrics.append(metric)
        quality=motion_quality(metrics);passes.append(quality)
        if attempt==0:(folder/(case+'-trajectory-initial.json')).write_text(json.dumps(metrics))
        print('  trajectory pass',attempt,quality,flush=True)
        if quality['max_acceleration']<=4 and quality['max_step']<=15:break
        smooth_tracks(plan,metrics,sigma=8+attempt)
    else:raise ValueError((case,'trajectory remains too abrupt',quality))
    if plan['reverse']:images.reverse();metrics.reverse()
    counts=[r['count'] for r in metrics];differences=np.diff(counts)
    assert np.all(differences>=0) if counts[-1]>=counts[0] else np.all(differences<=0)
    endpoints=[]
    for got,want in [(images[0],a),(images[-1],b)]:
        error=float(np.max(np.abs(got/255-want[450:1170,800:2080])));endpoints.append(error)
        assert error<=1/255+1e-9,(case,'endpoint',error)
    target=b[450:1170,800:2080];convergence={str(t):float(np.abs(images[round(t*251)]/255-target).sum()/max(target.sum(),1)) for t in [.9,.95,.98,.99,1.]}
    assert convergence['0.98']<.025 and convergence['0.99']<.006,(case,'late convergence',convergence)
    np.savez_compressed(folder/(case+'-lineage-frames.npz'),frames=np.stack(images),counts=np.array(counts))
    ff=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','5','-pix_fmt','yuv420p','-movflags','+faststart',str(folder/(case+'-lineage.mp4'))],stdin=subprocess.PIPE)
    for index,image in enumerate([images[0]]*24+images+[images[-1]]*24):
        alpha=presentation_alpha(image/255,float(np.clip((index-24)/251,0,1)))
        rgb=np.array([16,25,25])[None,None,:]+alpha[:,:,None]*np.array([221,218,212])[None,None,:]
        ff.stdin.write(np.uint8(np.clip(rgb,0,255)).tobytes())
    ff.stdin.close();assert ff.wait()==0
    from scipy import ndimage as ndi
    decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(folder/(case+'-lineage.mp4')),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    decoded_counts=[]
    while True:
        data=decoder.stdout.read(720*1280*3)
        if not data:break
        rgb=np.frombuffer(data,np.uint8).reshape(720,1280,3)
        decoded_counts.append(int(ndi.label(rgb[:,:,0]>126)[1]))
    assert decoder.wait()==0
    expected=[counts[0]]*24+counts+[counts[-1]]*24
    mismatches=[i for i,(actual,want) in enumerate(zip(decoded_counts,expected)) if actual!=want]
    assert len(decoded_counts)==300 and not mismatches,(case,'decoded topology mismatch',mismatches[:20])
    receipts.append(dict(case=case,motion_passes=passes,decoded_counts=decoded_counts,counts=counts,events=plan['events'],reverse=plan['reverse'],overlap_pixels=0,endpoint_errors=endpoints,convergence=convergence,max_repairs=max(r['repairs'] for r in metrics),max_offset=max(r['max_offset'] for r in metrics),metrics=metrics))
    (folder/'lineage-verification.json').write_text(json.dumps(receipts,indent=2)+'\n')
    print('Rendered',case,'convergence',convergence,'repairs',max(r['repairs'] for r in metrics),flush=True)
(folder/'lineage-concat.txt').write_text(''.join("file '%s-lineage.mp4'\n"%case for case in cases))
