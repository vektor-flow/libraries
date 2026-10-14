"""Independent final-grid replay of accepted geometry/text research clips."""
import argparse,json,sys,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from coalescing_transport import make_plan
from lineage_transport import stamp,intersects
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('cases',nargs='+');p.add_argument('--output',default='expanded');args=p.parse_args();out=args.folder/args.output
for case in args.cases:
    row=json.loads((out/(case+'-verification.json')).read_text())
    frames=np.load(out/(case+'-frames.npz'))['frames']
    a,b=[np.asarray(Image.open(args.folder/(case+'-'+side+'.png')).convert('L'))/255 for side in ['from','to']]
    if row.get('reverse_playback'):a,b=b,a
    plan=make_plan(a,b,lane_scale=row['lane_scale'],neck_width=row['neck_width'],phase_guard=row.get('phase_guard',False))
    error=0.;previous=None
    for k,(t,metric) in enumerate(zip(row['times'],row['metrics'])):
        layers=[stamp(plan['surface'](plan['nodes'][i],t)[0],np.array(c),0) for i,c in zip(metric['ids'],metric['centers'])]
        groups=[ndi.label(s['alpha']>.5)[1] for s in layers]
        if previous is not None:assert all(n<=p for n,p in zip(groups,previous)),(case,k,'count reversal')
        previous=groups
        for i,s in enumerate(layers):
            for other in layers[:i]:assert not intersects(s,other),(case,k,'overlap')
        replay=np.zeros((720,1280))
        for s in layers:
            x,y=s['origin'];h,w=s['alpha'].shape;replay[y:y+h,x:x+w]+=s['alpha']
        delta=float(abs(replay-frames[k]/255).max());error=max(error,delta)
        assert delta<=1/255+1e-8,(case,k,delta)
    for im,want in [(frames[0],a),(frames[-1],b)]:assert abs(im/255-want[450:1170,800:2080]).max()<=1/255+1e-8
    decoded=json.loads((out/(case+'-decoded.json')).read_text());assert not decoded['mismatches']
    counts=np.array(decoded['counts']);assert np.all(np.diff(counts)>=0) if row.get('reverse_playback') else np.all(np.diff(counts)<=0)
    result=dict(case=case,frames_replayed=len(frames),max_error=error,unrelated_overlap_pixels=0,decoded_frames=len(counts),endpoint_iou=decoded['endpoint_iou'],sha256=hashlib.sha256((out/(case+'.mp4')).read_bytes()).hexdigest(),fps=60,duration_seconds=6)
    (out/(case+'-independent.json')).write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)
