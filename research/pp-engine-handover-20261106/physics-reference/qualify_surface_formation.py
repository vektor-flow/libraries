"""Constitutive qualification on genuine VKF support; no fluid playback proof."""
from pathlib import Path
import hashlib,json
import numpy as np
from surface_formation_reference import reconstruct

root=Path(__file__).parent
metadata=json.loads((root/'glyph-mask-reference.json').read_text());data=(root/'glyph-mask-reference.bin').read_bytes()
assert hashlib.sha256(data).hexdigest()==metadata['dataSha256']
reports=[]
for case in metadata['cases']:
    mask=next(x for x in case['masks'] if x['kind']=='receiver')
    raw=data[mask['offsetBytes']:mask['offsetBytes']+mask['bytes']]
    assert hashlib.sha256(raw).hexdigest()==mask['sha256']
    full=np.frombuffer(raw,dtype=np.uint8);ids=np.flatnonzero(full);alpha=full[ids].astype(float)/255
    area=1.6/(metadata['width']*metadata['height']);sigma=1/area
    capacity=area*sigma*alpha
    fraction=(np.arange(len(ids))%7)/3
    mass=capacity*fraction
    moments=np.column_stack((.4*mass,.8*mass,.7*mass,mass,mass));before=moments.copy()
    state=reconstruct(moments,alpha,area,sigma)
    assert np.array_equal(before,moments)
    residual=float(np.max(np.abs(state.mass-state.layer_mass-state.excess_mass)))
    coverage_error=float(np.max(np.abs(state.coverage-alpha*np.minimum(fraction,1))))
    assert residual<1e-12 and coverage_error<1e-12
    assert np.all(state.pma[:,:3]<=state.pma[:,3,None]+1e-15)
    assert np.all(state.coverage<=alpha)
    # Accepted-front causality: hypothetical no captures right of a chosen front.
    front=ids%metadata['width']<120
    causal=moments.copy();causal[~front]=0
    visible=reconstruct(causal,alpha,area,sigma)
    assert np.all(visible.pma[~front]==0)
    reports.append({'view':case['view'],'nativeMaskSha256':mask['sha256'],'supportPixels':len(ids),
        'pixelAreaWorld':area,'arealMassDensity':sigma,'inputMass':float(mass.sum()),
        'firstLayerMass':float(state.layer_mass.sum()),'retainedExcessMass':float(state.excess_mass.sum()),
        'massPartitionMaxResidual':residual,'coverageMaxError':coverage_error,
        'coveredWorldArea':float(state.covered_area.sum()),'availableNativeWorldArea':float(alpha.sum()*area),
        'emptySupportPixels':int(np.count_nonzero(state.coverage==0)),
        'partialSupportPixels':int(np.count_nonzero((state.coverage>0)&(state.coverage<alpha-1e-14))),
        'fullSupportPixels':int(np.count_nonzero(state.coverage>=alpha-1e-14)),
        'frontCausalityPass':True,'stocksMutated':False})
report={'schema':'fine-surface-formation-reference/1','passed':True,'model':'declared opaque areal-fill mixed-surface closure',
    'scope':'Synthetic finite moments on genuine native glyph support; no air transport, full formation, GPU or Product proof',
    'reports':reports}
(root/'SURFACE_FORMATION_QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
