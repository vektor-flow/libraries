"""Reproducible endpoint-only weight sweep. No still previews or semantic input."""
import sys,json,time,subprocess,argparse
from pathlib import Path
from dataclasses import asdict
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from lineage_transport import make_plan,frame,smooth_tracks,motion_quality,presentation_alpha
from weighted_transport import CONFIGURATIONS,configure,sequence_cost,rank

CASES=['03-factor','04-square','05-difference','06-cancel','07-collect','08-fraction']
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--frames',type=int,default=81);p.add_argument('--candidates',default='0,1,2,3,4');p.add_argument('--encode',action='store_true');args=p.parse_args()
out=args.folder/'weight-sweep';out.mkdir(exist_ok=True)
prior={r['case']:r for r in json.loads((args.folder/'lineage-verification.json').read_text())}
receipts=[];failures=[]
for candidate in map(int,args.candidates.split(',')):
    config=CONFIGURATIONS[candidate]
    for case in CASES:
        name=f'{candidate}-{case}-{args.frames}';receipt_path=out/(name+'.json');cache=out/(name+'.npz')
        if receipt_path.exists() and cache.exists():
            row=json.loads(receipt_path.read_text())
            images=np.load(cache)['frames']
            row['costs'],row['details']=sequence_cost(images,row['metrics'],row['details']['desired_areas'][0],row['details']['desired_areas'][-1],row['events'],3)
            receipt_path.write_text(json.dumps(row)+'\n');receipts.append(row);continue
        print(name,asdict(config),flush=True);started=time.time()
        try:
            a=np.asarray(Image.open(args.folder/(case+'-from.png')).convert('L'))/255
            b=np.asarray(Image.open(args.folder/(case+'-to.png')).convert('L'))/255
            plan=make_plan(a,b);configure(plan,config)
            old=prior[case]['metrics']
            if plan['reverse']:old=list(reversed(old))
            smooth_tracks(plan,old,sigma=max(config.temporal,1))
            # Restore interpolation of the original 252-sample tracks for any grid.
            passes=[]
            for attempt in range(10 if args.frames>=252 else 1):
                state={};images=[];metrics=[]
                for k in range(args.frames):
                    image,metric=frame(plan,k/(args.frames-1),state)
                    images.append(np.uint8(np.rint(image*255)));metrics.append(metric)
                quality=motion_quality(metrics);passes.append(quality)
                if args.frames<252 or (quality['max_step']<=15 and quality['max_acceleration']<=4):break
                print('  smooth',attempt,quality,flush=True)
                smooth_tracks(plan,metrics,sigma=8+attempt)
            else:raise ValueError(('Motion remains abrupt',quality))
            if plan['reverse']:images.reverse();metrics.reverse()
            counts=[r['count'] for r in metrics]
            assert np.all(np.diff(counts)>=0) if counts[-1]>=counts[0] else np.all(np.diff(counts)<=0)
            errors=[float(np.max(np.abs(images[i]/255-want[450:1170,800:2080]))) for i,want in [(0,a),(-1,b)]]
            assert max(errors)<=1/255+1e-9,errors
            events=plan['events'] if not plan['reverse'] else sorted(1-t for t in plan['events'])
            target=b[450:1170,800:2080]
            convergence={str(t):float(np.abs(images[round(t*(args.frames-1))]/255-target).sum()/max(target.sum(),1)) for t in [.95,.98,.99,1.]}
            if args.frames>=252:assert convergence['0.98']<.025 and convergence['0.99']<.006,('late convergence',convergence)
            costs,details=sequence_cost(images,metrics,a.sum(),b.sum(),events,3)
            row=dict(candidate=candidate,case=case,configuration=asdict(config),frames=args.frames,costs=costs,details=details,
                metrics=metrics,convergence=convergence,endpoint_errors=errors,counts=counts,quality=motion_quality(metrics),seconds=time.time()-started,
                overlap_pixels=0,events=events,motion_passes=passes)
            np.savez_compressed(cache,frames=np.stack(images));receipt_path.write_text(json.dumps(row)+'\n');receipts.append(row)
            print('  done',round(time.time()-started,1),costs,row['quality'],flush=True)
        except Exception as exc:
            failure=dict(candidate=candidate,case=case,error=str(exc));failures.append(failure)
            (out/(name+'-failure.json')).write_text(json.dumps(failure)+'\n');print('  REJECT',failure,flush=True)
complete=[c for c in map(int,args.candidates.split(',')) if len([r for r in receipts if r['candidate']==c])==len(CASES)]
ranking=rank([r for r in receipts if r['candidate'] in complete]) if complete else {}
(out/f'ranking-{args.frames}.json').write_text(json.dumps(dict(**ranking,failures=failures,complete=complete),indent=2)+'\n')
if args.encode:
    for candidate in complete:
        clips=[]
        for case in CASES:
            name=f'{candidate}-{case}-{args.frames}';images=np.load(out/(name+'.npz'))['frames']
            row=json.loads((out/(name+'.json')).read_text());video=out/(name+'.mp4');clips.append(video)
            ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','5','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
            sequence=[images[0]]*24+list(images)+[images[-1]]*24
            for index,image in enumerate(sequence):
                alpha=presentation_alpha(image/255,float(np.clip((index-24)/(args.frames-1),0,1)))
                rgb=np.array([16,25,25])+alpha[:,:,None]*np.array([221,218,212])
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
            mismatches=[i for i,(got,want) in enumerate(zip(counts,expected)) if got!=want]
            verification=dict(counts=counts,mismatches=mismatches,expected_frames=len(expected),actual_frames=len(counts))
            (out/(name+'-decoded.json')).write_text(json.dumps(verification)+'\n')
            assert len(counts)==len(expected) and not mismatches,(name,mismatches)
        listing=out/f'candidate-{candidate}-concat.txt';listing.write_text(''.join(f"file '{v.name}'\n" for v in clips))
        subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(out/f'candidate-{candidate}.mp4')],check=True)
        print('Verified movie',candidate,flush=True)
