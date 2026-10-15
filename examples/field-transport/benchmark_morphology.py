"""Reproducible CPU morphology audit; failures stay in the denominator.

Generated geometry tests affine inference without symbol IDs. Optional native
combined inputs and real algebra layouts retain their original source hashes.
Timing is host CPU wall time, never GPU or phone performance.
"""
import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
import numpy as np


def generated_cases():
    angle=np.linspace(0,2*np.pi,64,endpoint=False)
    circle=np.c_[np.cos(angle),np.sin(angle)]
    outer=120*circle
    # The outer boundary is rotationally symmetric; the holes disambiguate it.
    for holes in [1,2]:
        a=[outer,18*circle+[48,12]]
        if holes==2:a.append(12*circle+[-40,-22])
        for turn in [0,.5*np.pi,np.pi,1.5*np.pi]:
            c,s=np.cos(turn),np.sin(turn)
            matrix=np.array([[c,-s],[s,c]])@np.array([[1.1,.15],[0,.85]])
            b=[p@matrix.T+[30,-20] for p in a]
            # Neither winding, cyclic phase nor hole-list order is correspondence.
            b=[np.roll(p[::-1],7+3*i,axis=0) for i,p in enumerate(b)]
            if holes==2:b=[b[0],b[2],b[1]]
            name=f'affine-{holes}-holes-turn-{round(turn/np.pi,2)}'
            yield dict(id=name,family='generated-affine',geometry=[[a],[b]],affine_expected=True)
    # Non-affine ribbons, replica split/merge, and an explicitly unsupported hole event.
    x=np.linspace(-180,180,128)
    def ribbon(y):return [np.vstack([np.c_[x,y-4],np.c_[x[::-1],(y+4)[::-1]]])]
    yield dict(id='ribbon-quadratic-cubic',family='profile',geometry=[[ribbon(x*x/500)],[ribbon(x**3/100000)]])
    p=55*(1+.12*np.cos(3*angle)+.08*np.sin(2*angle))[:,None]*circle
    a=[[p]];b=[[p*.65+[-100,-20]],[p*.65+[100,20]]]
    for name,sides in [('split',[a,b]),('merge',[b,a])]:
        yield dict(id=name,family='replica',geometry=sides)
    yield dict(id='hole-creation',family='unsupported-topology',geometry=[[[outer]],[[outer,40*circle]]])
    angle=np.linspace(0,2*np.pi,128,endpoint=False);unit=np.c_[np.cos(angle),np.sin(angle)]
    def star(radius,lobes,phase=0):return radius*(1+.16*np.cos(lobes*angle+phase))[:,None]*unit
    left=np.array([-100.,0]);right=-left
    a=[[star(42,3)+left,10*unit+left],[star(34,5,.3)+right]]
    b=[[star(38,4,.2)+right,12*unit+right],[star(36,6,.6)+left]]
    yield dict(id='nonrigid-hole-crossing',family='generated-nonrigid-routing',geometry=[a,b])



def audit(item,samples,planner="combined"):
    from combined_transport import CombinedScene,topology
    if planner=="validated":
        from validated_transport import ValidatedCombinedScene as CombinedScene
    from affine_transport import AffineTransport
    from scene_transport import draw_scene
    from scipy import ndimage as ndi
    a,b=[[[np.asarray(p,dtype=float) for p in body] for body in side] for side in item['geometry']]
    result=dict(case=item['id'],family=item['family'],planner=planner,bodies=[len(a),len(b)],passed=False)
    if item.get('affine_expected'):
        start=time.perf_counter()
        try:
            AffineTransport(a[0],b[0]);result['affine_recognized']=True
        except ValueError as exc:
            result['affine_recognized']=False;result['affine_error']=str(exc)
        result['affine_inference_ms']=(time.perf_counter()-start)*1000
    start=time.perf_counter();frame_times=[];counts=[];ious=[];hashes=[];masses=[]
    try:
        plan=CombinedScene(a,b)
        result['prepare_ms']=(time.perf_counter()-start)*1000
        result['kinds']=[kind for kind,_ in plan.groups]
        result['cohort_routed']=getattr(plan,'cohort_route',None) is not None
        result['plan_parameters']=[dict(kind=kind,frame_weight=getattr(getattr(part,'plan',None),'frame_weight',None),rejected=getattr(part,'rejected_candidates',[])) for kind,part in plan.groups]
        for t in np.linspace(0,1,samples):
            start=time.perf_counter();ims,metrics=plan.images(float(t))
            frame_times.append((time.perf_counter()-start)*1000)
            image=np.max(ims,axis=0);n,h=topology(image>127)
            if h!=plan.expected_holes:raise ValueError(('Scene hole count',float(t),h))
            if counts:
                direction=np.sign(len(b)-len(a));delta=n-counts[-1]
                if direction*delta<0 or (direction==0 and delta!=0):raise ValueError(('Count reversal',float(t),counts[-1],n))
            counts.append(n);masses.append(sum(m[2] for m in metrics))
            hashes.append(hashlib.sha256(image.tobytes()).hexdigest())
            if t in [0,1]:
                truth=draw_scene(a if t==0 else b,ss=8)>127;actual=image>127
                if np.any(actual&~ndi.binary_dilation(truth)) or np.any(ndi.binary_erosion(truth)&~actual):
                    raise ValueError(('Endpoint exceeds one boundary pixel',float(t)))
                ious.append(float((actual&truth).sum()/(actual|truth).sum()))
        if counts[0]!=len(a) or counts[-1]!=len(b):raise ValueError('Endpoint body count mismatch')
        result['passed']=True
    except ValueError as exc:
        result['error']=str(exc)
        if 'prepare_ms' not in result:result['failed_prepare_ms']=(time.perf_counter()-start)*1000
    result.update(sampled_states=len(counts),counts=counts,masses=masses,endpoint_iou=ious,frame_sha256=hashes)
    if frame_times:
        result['image_ms']=dict(median=float(np.median(frame_times)),p95=float(np.percentile(frame_times,95)),maximum=max(frame_times),samples=len(frame_times))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path);p.add_argument('--solver-dir',type=Path)
    p.add_argument('--combined',type=Path);p.add_argument('--atlas',type=Path);p.add_argument('--math-layouts',type=Path)
    p.add_argument('--samples',type=int,default=33);p.add_argument('--cases',nargs='+')
    p.add_argument('--planner',choices=['combined','validated'],default='combined')
    p.add_argument('--inputs',type=Path,help='Replay a complete anonymous geometry corpus')
    args=p.parse_args()
    if args.samples<3:p.error('--samples must be at least 3')
    if bool(args.atlas)!=bool(args.math_layouts):p.error('--atlas and --math-layouts must be supplied together')
    if args.solver_dir:sys.path.insert(0,str(args.solver_dir.resolve()))
    if args.inputs and (args.combined or args.atlas or args.math_layouts):p.error('--inputs replaces generated/native inputs')
    cases=json.loads(args.inputs.read_text()) if args.inputs else list(generated_cases());sources={}
    if args.inputs:sources['input_file_sha256']=hashlib.sha256(args.inputs.read_bytes()).hexdigest()
    if args.combined:
        sources['combined_sha256']=hashlib.sha256(args.combined.read_bytes()).hexdigest()
        cases.extend(dict(item,family='native-combined') for item in json.loads(args.combined.read_text()))
    if args.atlas:
        from field_transport import Atlas
        from scene_transport import endpoint,fit
        atlas=Atlas(args.atlas);sources['atlas']=atlas.provenance
        sources['math_layouts_sha256']=hashlib.sha256(args.math_layouts.read_bytes()).hexdigest()
        for item in json.loads(args.math_layouts.read_text()):
            a,b=fit(endpoint(atlas,item['from']),endpoint(atlas,item['to']))
            cases.append(dict(id='algebra-'+item['id'],family='native-algebra',geometry=[a,b]))
    if args.cases:
        names={item['id'] for item in cases}
        if set(args.cases)-names:p.error('Unknown case selection')
        cases=[item for item in cases if item['id'] in args.cases]
    args.output.mkdir(parents=True,exist_ok=False)
    serial=lambda value:value.tolist() if isinstance(value,np.ndarray) else value
    inputs=json.dumps(cases,default=serial,separators=(',',':'))+'\n'
    (args.output/'inputs.json').write_text(inputs)
    results=[];start=time.perf_counter()
    solver=Path(sys.path[0])
    sources['solver_files']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(solver.glob('*.py'))}
    sources['benchmark_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report=dict(scope='CPU wall time and sampled raster correctness; no continuous collision proof, GPU or phone timing',platform=platform.platform(),python=sys.version,numpy=np.__version__,sources=sources,inputs_sha256=hashlib.sha256(inputs.encode()).hexdigest(),samples_per_case=args.samples,cases=results)
    for item in cases:
        result=audit(item,args.samples,args.planner);results.append(result)
        report.update(total=len(results),passed=sum(r['passed'] for r in results),elapsed_seconds=time.perf_counter()-start)
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(result['case'],result['passed'],result.get('kinds'),result.get('error',''),flush=True)
    # Audit completion is successful even with rejected candidates. Every failure
    # remains explicit in report.json; this is not a pass-only release gate.


if __name__=='__main__':main()
