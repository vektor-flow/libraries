"""Compare shape and timing proxies; these are not material-flow proofs."""
import sys,json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
folder=Path(sys.argv[1]);results=[]
cache_file=folder/'steady'/'comparison.json'
cached={r['case']:r['variants'] for r in json.loads(cache_file.read_text())} if cache_file.exists() else {}
for case in ['03-factor','04-square','05-difference','06-cancel','07-collect','08-fraction']:
    variants={}
    for variant in ['continuity','regularized','steady']:
        if variant in cached.get(case,{}):
            variants[variant]=cached[case][variant];continue
        path=folder/variant/(case+'-frames.npz')
        if not path.exists():continue
        frames=np.load(path)['frames'];thin=[];activity=[];previous=None
        for im in frames:
            mask=im>127;opened=ndi.binary_opening(mask,iterations=2)
            thin.append(float(np.count_nonzero(mask&~opened)/max(mask.sum(),1)))
            low=ndi.gaussian_filter(im.astype(np.float32)/255,2.)[::3,::3]
            if previous is not None:activity.append(float(abs(low-previous).sum()))
            previous=low
        activity=np.array(activity);middle=activity[int(.15*len(activity)):int(.85*len(activity))]
        row=json.loads((folder/variant/(case+'-verification.json')).read_text());d=row['diagnostics']
        variants[variant]=dict(thin_excess=float(np.maximum(0,np.array(thin)-np.linspace(thin[0],thin[-1],len(thin))).mean()),
            peak_thin=float(max(thin)),excess_thickness=d['excess_thickness'],peak_changed_coverage=d['max_changed_coverage'],
            peak_boundary_second_difference=max(d['boundary_acceleration']),activity_cv=float(middle.std()/max(middle.mean(),1e-9)),
            peak_activity_per_normalized_time=float(activity.max()*(len(frames)-1)),
            mean_activity_per_normalized_time=float(activity.sum()),motion_samples=len(frames))
    results.append(dict(case=case,variants=variants));print(case,variants,flush=True)
(folder/'steady'/'comparison.json').write_text(json.dumps(results,indent=2)+'\n')
