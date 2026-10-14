"""Replay accepted trajectories, verify body ownership and encoded endpoints."""
import sys,json,subprocess,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from lineage_transport import stamp,intersects
from coalescing_transport import make_plan
folder=Path(sys.argv[1]);out=folder/'coalescence';results=[]
all_cases=['06-cancel','07-collect','08-fraction']
cases=sys.argv[2:] or all_cases
for case in cases:
    row=json.loads((out/(case+'-verification.json')).read_text());images=np.load(out/(case+'-frames.npz'))['frames']
    a=np.asarray(Image.open(folder/(case+'-from.png')).convert('L'))/255;b=np.asarray(Image.open(folder/(case+'-to.png')).convert('L'))/255
    plan=make_plan(a,b,lane_scale=row['lane_scale']);max_error=0.;shared_frames=0;previous_groups=None
    for k,metric in enumerate(row['metrics']):
        t=row['times'][k]
        nodes=[plan['nodes'][i] for i in metric['ids']]
        layers=[stamp(plan['surface'](n,t)[0],np.array(c),0) for n,c in zip(nodes,metric['centers'])]
        groups=[int(ndi.label(layer['alpha']>.5)[1]) for layer in layers]
        if previous_groups is not None:assert all(n<=p for n,p in zip(groups,previous_groups)),(case,k,'Group split after contact')
        previous_groups=groups
        for i in range(len(nodes)):
            for j in range(i):
                if not intersects(layers[i],layers[j]):continue
                raise AssertionError((case,k,'Overlap between shared bodies'))
        replay=np.zeros((720,1280))
        for layer in layers:
            x,y=layer['origin'];h,w=layer['alpha'].shape
            replay[y:y+h,x:x+w]=np.minimum(1,replay[y:y+h,x:x+w]+layer['alpha'])
        error=float(np.max(np.abs(replay-images[k]/255)));max_error=max(max_error,error)
        assert error<=1/255+1e-8,(case,k,'trajectory replay',error)
    prior=json.loads((folder/'joined'/(case+'-verification.json')).read_text())
    def travel(metrics):
        last={};distance=0.
        for r in metrics:
            current={i:np.array(c) for i,c in zip(r['ids'],r['centers'])}
            distance+=sum(float(np.linalg.norm(c-last[i])) for i,c in current.items() if i in last);last=current
        return distance
    areas=np.array(row['diagnostics']['areas']);previous_areas=np.array(prior['diagnostics']['areas']);norm=max(areas[0],areas[-1])
    indices=[0,24,24+round(.98*311),24+round(.99*311),335,359];expression='+'.join(f'eq(n\\,{i})' for i in indices)
    movie=out/(case+'.mp4')
    data=subprocess.check_output(['ffmpeg','-v','error','-i',str(movie),'-vf','select='+expression,'-fps_mode','vfr','-f','rawvideo','-pix_fmt','rgb24','-'])
    frames=np.frombuffer(data,np.uint8).reshape(-1,720,1280,3);assert len(frames)==6
    ious={}
    for index,rgb in zip(indices,frames):
        want=(a if index<25 else b)[450:1170,800:2080]>.5;got=rgb[:,:,0]>126
        ious[index]=float(np.count_nonzero(want&got)/max(np.count_nonzero(want|got),1))
    assert all(ious[i]==1 for i in [0,24,335,359]),(case,ious)
    assert ious[indices[2]]>.97 and ious[indices[3]]>.99,(case,ious)
    decoded=json.loads((out/(case+'-decoded.json')).read_text());assert len(decoded['counts'])==360 and not decoded['mismatches']
    counts=np.array(decoded['counts']);assert np.all(np.diff(counts)>=0) if counts[-1]>=counts[0] else np.all(np.diff(counts)<=0)
    result=dict(case=case,sha256=hashlib.sha256(movie.read_bytes()).hexdigest(),replay_max_error=max_error,attached_overlap_frame_pairs=shared_frames,
        unrelated_overlap_pixels=0,encoded_iou=ious,body_travel=travel(row['metrics']),maximum_neck_offsets=[getattr(n,'maximum_neck_offset',0.) for n in plan['roots']],
        thickness_excess=row['diagnostics']['excess_thickness'],previous_thickness_excess=prior['diagnostics']['excess_thickness'],
        area_second_difference_max=float(np.abs(np.diff(areas,2)).max()/norm),previous_area_second_difference_max=float(np.abs(np.diff(previous_areas,2)).max()/norm))
    results.append(result);print(result,flush=True)
    (out/(case+'-independent.json')).write_text(json.dumps(result,indent=2)+'\n')
if all((out/(case+'-independent.json')).exists() for case in all_cases):
    results=[json.loads((out/(case+'-independent.json')).read_text()) for case in all_cases]
    (out/'independent-verification.json').write_text(json.dumps(results,indent=2)+'\n')
