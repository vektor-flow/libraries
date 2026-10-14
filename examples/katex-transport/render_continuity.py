"""Compact-route, continuous-handoff research movies; endpoint pixels only."""
import sys,json,subprocess,argparse
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from lineage_transport import make_plan,frame,smooth_tracks,motion_quality,desired_center
from continuous_transport import configure,diagnostics,presentation_alpha
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('cases',nargs='*');p.add_argument('--encode',action='store_true');args=p.parse_args()
folder=args.folder;out=folder/'continuity';out.mkdir(exist_ok=True)
cases=args.cases or ['03-factor','04-square','05-difference','06-cancel','07-collect','08-fraction']

def warm_start(plan,old,scale):
    import copy
    old=copy.deepcopy(old)
    if plan['reverse']:old.reverse()
    lanes=[r.lane for r in plan['roots']]
    for root in plan['roots']:root.lane=0
    for k,row in enumerate(old):
        for j,i in enumerate(row['ids']):
            base=desired_center(plan['nodes'][i],k/(len(old)-1),3)*3+np.array([-800.,-450.])
            row['centers'][j]=(base+scale*(np.array(row['centers'][j])-base)).tolist()
    for root,lane in zip(plan['roots'],lanes):root.lane=lane
    smooth_tracks(plan,old,8)

for case in cases:
    cache=out/(case+'-frames.npz');receipt=out/(case+'-verification.json')
    if cache.exists() and receipt.exists():continue
    a=np.asarray(Image.open(folder/(case+'-from.png')).convert('L'))/255
    b=np.asarray(Image.open(folder/(case+'-to.png')).convert('L'))/255
    previous=json.loads((folder/'weight-sweep'/('3-'+case+'-252.json')).read_text())
    trials=[]
    for scale in [.5,.65,.8,1.]:
        print(case,'lane',scale,flush=True)
        try:
            plan=make_plan(a,b);configure(plan,scale);warm_start(plan,previous['metrics'],scale)
            passes=[]
            for attempt in range(8):
                state={};images=[];metrics=[]
                for k in range(252):
                    image,metric=frame(plan,k/251,state)
                    images.append(np.uint8(np.rint(image*255)));metrics.append(metric)
                quality=motion_quality(metrics);passes.append(quality)
                print('  pass',attempt,quality,flush=True)
                if quality['max_step']<=10 and quality['max_acceleration']<=2.5:break
                if attempt>=2 and quality['max_step']>20 and quality['max_step']>.8*passes[0]['max_step']:raise ValueError(('route remains obstructed',quality))
                plan['anticipate_contacts']=True
                smooth_tracks(plan,metrics,8+attempt*2)
            else:raise ValueError(('abrupt route',quality))
            if plan['reverse']:images.reverse();metrics.reverse()
            counts=[r['count'] for r in metrics]
            assert np.all(np.diff(counts)>=0) if counts[-1]>=counts[0] else np.all(np.diff(counts)<=0)
            for got,want in [(images[0],a),(images[-1],b)]:assert np.max(np.abs(got/255-want[450:1170,800:2080]))<1/255+1e-9
            target=b[450:1170,800:2080]
            convergence={str(t):float(np.abs(images[round(t*251)]/255-target).sum()/max(target.sum(),1)) for t in [.95,.98,.99,1.]}
            assert convergence['0.98']<.025 and convergence['0.99']<.006,('late convergence',convergence)
            detail=diagnostics(images)
            oldimages=np.load(folder/'weight-sweep'/('3-'+case+'-252.npz'))['frames'];old_detail=diagnostics(oldimages)
            row=dict(case=case,lane_scale=scale,motion_passes=passes,metrics=metrics,counts=counts,convergence=convergence,diagnostics=detail,previous_diagnostics=old_detail,trials=trials,anticipate_contacts=plan.get('anticipate_contacts',False),projection_slack=plan.get('projection_slack',1))
            receipt.write_text(json.dumps(row)+'\n');np.savez_compressed(cache,frames=np.stack(images));break
        except Exception as exc:
            trials.append(dict(lane_scale=scale,error=str(exc)));print(' REJECT',trials[-1],flush=True)
    else:
        (out/(case+'-failure.json')).write_text(json.dumps(trials)+'\n');continue
if args.encode:
    for case in cases:
        receipt=out/(case+'-verification.json');cache=out/(case+'-frames.npz')
        if not receipt.exists():continue
        images=np.load(cache)['frames'];row=json.loads(receipt.read_text());video=out/(case+'.mp4')
        ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','3','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
        for im in [images[0]]*24+list(images)+[images[-1]]*24:
            alpha=im.astype(np.float32)/255
            # Continuous monotone contrast transfer; no threshold jump at alpha=.5.
            alpha=presentation_alpha(alpha)
            rgb=np.array([16,25,25],np.float32)+alpha[:,:,None]*np.array([221,218,212],np.float32)
            ff.stdin.write(np.uint8(np.clip(rgb,0,255)).tobytes())
        ff.stdin.close();assert ff.wait()==0
        decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
        counts=[]
        while True:
            data=decoder.stdout.read(720*1280*3)
            if not data:break
            rgb=np.frombuffer(data,np.uint8).reshape(720,1280,3);counts.append(int(ndi.label(rgb[:,:,0]>126)[1]))
        assert decoder.wait()==0
        expected=[row['counts'][0]]*24+row['counts']+[row['counts'][-1]]*24
        mismatch=[i for i,(x,y) in enumerate(zip(counts,expected)) if x!=y]
        (out/(case+'-decoded.json')).write_text(json.dumps(dict(counts=counts,mismatches=mismatch))+'\n')
        assert len(counts)==300 and not mismatch,(case,mismatch)
        print('Verified movie',case,flush=True)
    if all((out/(case+'-decoded.json')).exists() for case in cases):
        listing=out/'concat.txt';listing.write_text(''.join(f"file '{case}.mp4'\n" for case in cases))
        subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(out/'continuity-katex-animations.mp4')],check=True)
