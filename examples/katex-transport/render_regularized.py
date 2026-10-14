"""Generate regularized geometry before activity retiming; endpoint pixels only."""
import sys,json,argparse
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from lineage_transport import make_plan,frame,smooth_tracks,motion_quality
from continuous_transport import diagnostics
from regularized_transport import configure
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('cases',nargs='*');args=p.parse_args()
folder=args.folder;out=folder/'regularized';out.mkdir(exist_ok=True)
cases=args.cases or ['03-factor','04-square','05-difference','06-cancel','07-collect','08-fraction']

for case in cases:
    cache=out/(case+'-frames.npz');receipt=out/(case+'-verification.json')
    if cache.exists() and receipt.exists():continue
    a=np.asarray(Image.open(folder/(case+'-from.png')).convert('L'))/255
    b=np.asarray(Image.open(folder/(case+'-to.png')).convert('L'))/255
    previous=json.loads((folder/'continuity'/(case+'-verification.json')).read_text())
    trials=[]
    for scale in sorted(set([previous['lane_scale'],1.])):
        print(case,'lane',scale,flush=True)
        try:
            plan=make_plan(a,b);configure(plan,scale)
            warm=previous['metrics'][::-1] if plan['reverse'] else previous['metrics']
            smooth_tracks(plan,warm,4)
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
            oldimages=np.load(folder/'continuity'/(case+'-frames.npz'))['frames'];old_detail=diagnostics(oldimages)
            row=dict(case=case,lane_scale=scale,motion_passes=passes,metrics=metrics,counts=counts,convergence=convergence,diagnostics=detail,previous_diagnostics=old_detail,trials=trials,anticipate_contacts=plan.get('anticipate_contacts',False),projection_slack=plan.get('projection_slack',1))
            receipt.write_text(json.dumps(row)+'\n');np.savez_compressed(cache,frames=np.stack(images));break
        except Exception as exc:
            trials.append(dict(lane_scale=scale,error=str(exc)));print(' REJECT',trials[-1],flush=True)
    else:
        (out/(case+'-failure.json')).write_text(json.dumps(trials)+'\n');continue
