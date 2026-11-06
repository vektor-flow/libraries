from pathlib import Path
import hashlib,json
import numpy as np
from glyph_grid_reference import extrude,frozen_reaction
root=Path(__file__).parent;meta=json.loads((root/'glyph-mask-reference.json').read_text());raw=(root/'glyph-mask-reference.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['dataSha256'];rows=[]
for case in meta['cases']:
 masks={m['kind']:np.frombuffer(raw,dtype=np.uint8,count=m['bytes'],offset=m['offsetBytes']).reshape(meta['height'],meta['width']).astype(float)/255 for m in case['masks']}
 for shape in [(24,16,8),(48,32,8),(96,64,8)]:
  lengths=(meta['width']/meta['height'],1,.4);volume=np.prod(lengths);receiver=masks['receiver'];coarse=extrude(receiver,shape,lengths);relative=abs(float(coarse.mean()-receiver.mean()))/receiver.mean();assert relative<1e-12
  rates=[]
  for flow in [.001,.01,.06]:
   r=frozen_reaction(receiver,shape,lengths,flow,1.25);r.update(flowRate=flow,sinkOnlyCflAt60Hz=r['coarseMaximumRate']/60,sinkOnlyDtBound=.3/r['coarseMaximumRate'],captureBias=(r['coarseCaptured']/r['fineCaptured']-1));rates.append(r)
  rows.append({'view':case['view'],'grid':shape,'sourceAreaPx2':float(masks['source'].sum()),'receiverAreaPx2':float(receiver.sum()),'coarseMappingMassRelativeError':relative,'rates':rates})
result={'schema':'native-glyph-grid-qualification/1','nativeMaskDataSha256':meta['dataSha256'],'geometryMapping':'PASS: finite native-raster area preserved exactly to floating precision, including nondivisible grids and upward y','subgridReceiverModel':'RED: homogeneous coarse-cell reaction is not equivalent to capture on the native glyph footprint','scope':'Exact isolated frozen-position reaction operator, no transport; NOT a full fluid/first-wave capture proof','rows':rows,'nextRequired':'A qualified fine-mask particle interception or resolved subgrid transport law; avoid absorbing gas outside native receiver strokes merely because a coarse cell overlaps them','sourceHashes':{name:hashlib.sha256((root/name).read_bytes()).hexdigest()for name in ['glyph_grid_reference.py','qualify_glyph_grid.py','test_glyph_grid.py']}}
(root/'GLYPH_GRID_QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n')
for r in rows:
 k=r['rates'][1];print(r['view'],r['grid'],'areaErr',r['coarseMappingMassRelativeError'],'biasQ.01',round(k['captureBias'],3),'sinkCfl60',round(k['sinkOnlyCflAt60Hz'],3))
