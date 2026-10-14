"""Matched-duration merge comparison, including the contact neighbourhood."""
import sys,json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
folder=Path(sys.argv[1]);results=[]
for case in (sys.argv[2:] or ['06-cancel','07-collect','08-fraction']):
    variants={}
    for variant in ['steady','joined']:
        row=json.loads((folder/variant/(case+'-verification.json')).read_text())
        frames=np.load(folder/variant/(case+'-frames.npz'))['frames'];counts=np.array(row['counts']);d=row['diagnostics']
        events=(np.flatnonzero(np.diff(counts)!=0)+1).tolist();changes=np.array(d['changed_coverage']);areas=np.array(d['areas']);norm=max(areas[0],areas[-1]);thin=[]
        for im in frames:
            mask=im>127;opened=ndi.binary_opening(mask,iterations=2)
            thin.append(float(np.count_nonzero(mask&~opened)/max(mask.sum(),1)))
        variants[variant]=dict(thickness_excess=d['excess_thickness'],mean_area=float(areas.mean()),peak_area=float(areas.max()),
            area_reversal=float((abs(np.diff(areas)).sum()-abs(areas[-1]-areas[0]))/norm),
            area_second_difference=float(abs(np.diff(areas,2)).max()/norm),
            thin_excess=float(np.maximum(0,np.array(thin)-np.linspace(thin[0],thin[-1],len(thin))).mean()),
            peak_changed_coverage=d['max_changed_coverage'],peak_boundary_second_difference=max(d['boundary_acceleration']),
            merge_times=[k/(len(frames)-1) for k in events],post_final_merge_fraction=1-events[-1]/(len(frames)-1),
            contact_change_peaks=[float(changes[max(0,k-7):min(len(changes),k+6)].max()) for k in events],
            last_fifth_peak_change=float(changes[int(.8*len(changes)):].max()))
    results.append(dict(case=case,variants=variants));print(results[-1],flush=True)
(folder/'joined'/'comparison.json').write_text(json.dumps(results,indent=2)+'\n')
