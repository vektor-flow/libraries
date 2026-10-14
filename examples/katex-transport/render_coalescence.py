"""Render forward coalescence directly, with no pre-fitted child target pieces."""
import sys,json,argparse
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from coalescing_transport import make_plan
from lineage_transport import frame,smooth_tracks,motion_quality
from continuous_transport import diagnostics
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('cases',nargs='*');args=p.parse_args()
folder=args.folder;out=folder/'coalescence';out.mkdir(exist_ok=True)
cases=args.cases or ['06-cancel','07-collect','08-fraction']
for case in cases:
    if (out/(case+'-verification.json')).exists():continue
    a=np.array(Image.open(folder/(case+'-from.png')).convert('L'))/255;b=np.array(Image.open(folder/(case+'-to.png')).convert('L'))/255
    trials=[]
    for lane in [.35,.6,1.]:
        try:
            plan=make_plan(a,b,lane_scale=lane);print(case,lane,'contact',[n.contact_time for n in plan['roots']],flush=True)
            passes=[]
            for attempt in range(7):
                images=[];rows=[];state={}
                for k in range(312):
                    try:im,row=frame(plan,k/311,state)
                    except Exception as exc:raise ValueError((k,k/311,str(exc))) from exc
                    images.append(np.uint8(np.rint(im*255)));rows.append(row)
                quality=motion_quality(rows);passes.append(quality);print('pass',attempt,quality,flush=True)
                if quality['max_step']<=10 and quality['max_acceleration']<=2.5:break
                plan['anticipate_contacts']=True;smooth_tracks(plan,rows,6+2*attempt)
            else:raise ValueError(('Motion not settled',passes))
            assert np.all(np.diff([r['count'] for r in rows])<=0)
            for im,want in [(images[0],a),(images[-1],b)]:assert np.max(abs(im/255-want[450:1170,800:2080]))<=1/255+1e-9
            result=dict(case=case,lane_scale=lane,metrics=rows,counts=[r['count'] for r in rows],times=np.linspace(0,1,312).tolist(),motion_quality=quality,motion_passes=passes,contacts=[n.contact_time for n in plan['roots']],diagnostics=diagnostics(images),trials=trials)
            np.savez_compressed(out/(case+'-frames.npz'),frames=np.array(images));(out/(case+'-verification.json')).write_text(json.dumps(result)+'\n');break
        except Exception as exc:
            trials.append(dict(lane_scale=lane,error=str(exc)));print('REJECT',trials[-1],flush=True)
    else:(out/(case+'-failure.json')).write_text(json.dumps(trials)+'\n')

if any(not (out/(case+'-verification.json')).exists() for case in cases):raise SystemExit('Some shared-body cases were rejected; see failure receipts')
