"""Re-evaluate geometry on an activity-based clock; never interpolate video frames."""
import sys,json,argparse,subprocess
from pathlib import Path
import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy import ndimage as ndi
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from lineage_transport import make_plan,frame,desired_center,motion_quality
from regularized_transport import configure,activity_clock
from continuous_transport import diagnostics,presentation_alpha
from pixel_transport import clock
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('cases',nargs='*');p.add_argument('--concat-only',action='store_true');p.add_argument('--join',action='store_true');args=p.parse_args()
if args.join:
    from join_transport import configure
folder=args.folder;out=folder/('joined' if args.join else 'steady');out.mkdir(exist_ok=True)
source_folder='join' if args.join else 'regularized'
cases=args.cases or (['06-cancel','07-collect','08-fraction'] if args.join else ['03-factor','04-square','05-difference','06-cancel','07-collect','08-fraction'])
for case in cases:
    if args.concat_only:continue
    target=out/(case+'-verification.json')
    if not target.exists():
        prior=json.loads((folder/source_folder/(case+'-verification.json')).read_text())
        images=np.load(folder/source_folder/(case+'-frames.npz'))['frames']
        a=np.asarray(Image.open(folder/(case+'-from.png')).convert('L'))/255
        b=np.asarray(Image.open(folder/(case+'-to.png')).convert('L'))/255
        plan=make_plan(a,b);configure(plan,prior['lane_scale'])
        metrics=prior['metrics'][::-1] if plan['reverse'] else prior['metrics']
        reference=images[::-1] if plan['reverse'] else images
        times=np.linspace(0,1,len(metrics));recorded=[dict(zip(r['ids'],r['centers'])) for r in metrics]
        offsets={};plan['track_splines']={}
        for node in plan['nodes']:
            values=[];last=np.zeros(2)
            for t,r,k in zip(times,recorded,range(len(metrics))):
                if node.id in r:last=np.array(r[node.id])-plan.get('desired_center',desired_center)(node,t,3)*3-np.array([-800.,-450.])
                elif t<=node.birth and node.parent is not None:last=offsets[node.parent.id][k]
                values.append(last.copy())
            values=np.array(values)
            if args.join:
                envelope=np.array([clock(min(t/.1,1))*clock(min((1-t)/.1,1)) for t in times])
                values+=envelope[:,None]*(ndi.gaussian_filter1d(values,3,axis=0,mode='nearest')-values)
            offsets[node.id]=values
            plan['track_splines'][node.id]=CubicSpline(times,values,bc_type=((1,np.zeros(2)),(1,np.zeros(2))))
        schedule=times if args.join else activity_clock(reference)
        schedule=PchipInterpolator(times,schedule)(np.linspace(0,1,312))
        attempts=[]
        for attempt in range(4):
            state={};frames=[];rows=[]
            for t in schedule:
                image,row=frame(plan,float(t),state);frames.append(np.uint8(np.rint(image*255)));rows.append(row)
            quality=motion_quality(rows);attempts.append(quality);print(case,attempt,quality,flush=True)
            if quality['max_step']<=10 and quality['max_acceleration']<=2.5:break
            # Newly sampled contacts can expose projection bumps. Anticipate only
            # their residual correction, leaving the accepted route in place.
            (out/(case+'-retime-trial-'+str(attempt)+'.json')).write_text(json.dumps(dict(quality=quality,times=schedule.tolist(),metrics=rows))+'\n')
            recorded=[dict(zip(r['ids'],r['centers'])) for r in rows]
            old_curves=plan['track_splines'].copy();corrections={}
            for node in plan['nodes']:
                extra=[]
                for k,(t,r) in enumerate(zip(schedule,recorded)):
                    want=plan.get('desired_center',desired_center)(node,t,3)*3+np.array([-800.,-450.])+old_curves[node.id](t)
                    value=np.array(r[node.id])-want if node.id in r else np.zeros(2)
                    if t<=node.birth and node.parent is not None:value=corrections[node.parent.id][k]
                    extra.append(value)
                extra=np.array(extra)
                positive=ndi.maximum_filter1d(np.maximum(extra,0),9,axis=0,mode='nearest')
                negative=ndi.maximum_filter1d(np.maximum(-extra,0),9,axis=0,mode='nearest')
                extra=ndi.gaussian_filter1d(positive-negative,4,axis=0,mode='nearest')
                envelope=np.array([clock(min(t/.1,1))*clock(min((1-t)/.1,1)) for t in schedule])
                extra*=envelope[:,None];corrections[node.id]=extra
                existing=old_curves[node.id](schedule)
                smoothed=ndi.gaussian_filter1d(existing,1.5,axis=0,mode='nearest')
                existing+=envelope[:,None]*(smoothed-existing)
                plan['track_splines'][node.id]=CubicSpline(schedule,existing+extra,bc_type=((1,np.zeros(2)),(1,np.zeros(2))))
        else:raise ValueError((case,'retimed contact did not settle',attempts))
        if plan['reverse']:frames.reverse();rows.reverse();schedule=schedule[::-1]
        counts=[r['count'] for r in rows]
        assert np.all(np.diff(counts)>=0) if counts[-1]>=counts[0] else np.all(np.diff(counts)<=0)
        for im,want in [(frames[0],a),(frames[-1],b)]:assert np.max(abs(im/255-want[450:1170,800:2080]))<=1/255+1e-9
        baseline=json.loads((folder/('steady' if args.join else 'continuity')/(case+'-verification.json')).read_text())
        row=dict(case=case,branch_power=plan.get('branch_power',1.),area_power=plan.get('area_power',1.),gentle_sibling_release=plan.get('gentle_sibling_release',False),clock='uniform' if args.join else 'activity',lane_scale=prior['lane_scale'],times=schedule.tolist(),metrics=rows,counts=counts,motion_quality=quality,retime_attempts=attempts,diagnostics=diagnostics(frames),previous_diagnostics=baseline['diagnostics'])
        np.savez_compressed(out/(case+'-frames.npz'),frames=np.array(frames));target.write_text(json.dumps(row)+'\n')
    row=json.loads(target.read_text());frames=np.load(out/(case+'-frames.npz'))['frames'];video=out/(case+'.mp4')
    ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','3','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
    for im in [frames[0]]*24+list(frames)+[frames[-1]]*24:
        alpha=presentation_alpha(im.astype(np.float32)/255)
        rgb=np.array([16,25,25],np.float32)+alpha[:,:,None]*np.array([221,218,212],np.float32)
        ff.stdin.write(np.uint8(np.clip(rgb,0,255)).tobytes())
    ff.stdin.close();assert ff.wait()==0
    decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE);counts=[]
    endpoint_iou={}
    for k in range(len(frames)+48):
        data=decoder.stdout.read(720*1280*3);assert len(data)==720*1280*3
        mask=np.frombuffer(data,np.uint8).reshape(720,1280,3)[:,:,0]>126
        counts.append(int(ndi.label(mask)[1]))
        if k in [0,24,len(frames)+23,len(frames)+47]:
            want=frames[0 if k<25 else -1]>127
            endpoint_iou[k]=float(np.count_nonzero(mask&want)/np.count_nonzero(mask|want))
    assert not decoder.stdout.read(1);assert decoder.wait()==0
    expected=[row['counts'][0]]*24+row['counts']+[row['counts'][-1]]*24
    mismatch=[i for i,(x,y) in enumerate(zip(counts,expected)) if x!=y]
    (out/(case+'-decoded.json')).write_text(json.dumps(dict(counts=counts,mismatches=mismatch,endpoint_iou=endpoint_iou))+'\n')
    assert not mismatch and all(x==1 for x in endpoint_iou.values()),(case,mismatch,endpoint_iou)
    print('Verified',case,flush=True)
if len(cases)==(3 if args.join else 6):
    for case in cases:
        decoded=json.loads((out/(case+'-decoded.json')).read_text())
        assert len(decoded['counts'])==360 and not decoded['mismatches']
    listing=out/'concat.txt';listing.write_text(''.join(f"file '{case}.mp4'\n" for case in cases))
    subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(out/('joined-katex-animations.mp4' if args.join else 'steady-katex-animations.mp4'))],check=True)
