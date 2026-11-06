from pathlib import Path
import hashlib,json,time
import numpy as np
from fine_receiver_reference import capture_segments
root=Path(__file__).parent;meta=json.loads((root/'glyph-mask-reference.json').read_text());raw=(root/'glyph-mask-reference.bin').read_bytes();assert hashlib.sha256(raw).hexdigest()==meta['dataSha256'];rng=np.random.default_rng(712);lengths=np.array([meta['width']/meta['height'],1,.4]);rows=[]
for case in meta['cases']:
 masks={m['kind']:np.frombuffer(raw,dtype=np.uint8,count=m['bytes'],offset=m['offsetBytes']).reshape(meta['height'],meta['width']).astype(float)/255 for m in case['masks']};source,receiver=masks['source'],masks['receiver'];h,w=source.shape;n=2048
 chosen=rng.choice(h*w,size=n,p=(source/source.sum()).ravel());y,x=np.unravel_index(chosen,source.shape);starts=np.column_stack([(x+rng.random(n))*lengths[0]/w,(h-y-1+rng.random(n))*lengths[1]/h,rng.random(n)*lengths[2]])
 # A uniform velocity is an exact unforced periodic NS solution. This isolates
 # interception; this is NOT the actual full presentation's turbulent fluid run.
 velocity=np.array([.12,.04,.005]);dt=1.;ends=starts+velocity*dt;threshold=rng.exponential(size=n);flow=.01;rate=flow/(receiver.mean()*np.prod(lengths))
 receiver_meta=next(m for m in case['masks']if m['kind']=='receiver');left,_,right,_=receiver_meta['bounds'];wave=(left*lengths[0]/w,right*lengths[0]/w,3*lengths[0]/w)
 for mode,front in [('static',None),('linear-wave-front',wave)]:
  started=time.perf_counter();r=capture_segments(receiver,starts,ends,threshold,rate,dt,lengths,front=front);elapsed=time.perf_counter()-started
  captured=r['captured'];gas=~captured;assert captured.any() and gas.any()
  if front is not None:
   active_front=front[0]+(front[1]-front[0])*r['fractions'][captured];assert np.all(abs(r['positions'][captured,0]-active_front)<=front[2]/2+1e-12)
  assert np.all(receiver[r['pixels'][captured,0],r['pixels'][captured,1]]>0)
  np.testing.assert_allclose(r['positions'][gas],np.mod(ends[gas],lengths),atol=1e-15,rtol=0)
  assert np.all(np.linalg.norm(r['positions'][gas]-starts[gas],axis=1)>0)
  # Same trajectories, split at two observation/view boundaries. No source reset.
  remaining=threshold.copy();positions=starts.copy();live=np.ones(n,dtype=bool)
  for step in range(4):
   ids=np.flatnonzero(live);partial_front=None if front is None else (front[0]+(front[1]-front[0])*step/4,front[0]+(front[1]-front[0])*(step+1)/4,front[2]);part=capture_segments(receiver,positions[ids],positions[ids]+velocity*.25,remaining[ids],rate,.25,lengths,front=partial_front);positions[ids]=part['positions'];remaining[ids]-=part['exposure'];live[ids[part['captured']]]=False
  np.testing.assert_array_equal(live,gas);np.testing.assert_allclose(positions,r['positions'],atol=2e-13,rtol=0)
  weight=1/n;gas_mass=float(gas.sum()*weight);received=float(captured.sum()*weight);assert abs(gas_mass+received-1)<1e-15
  rows.append({'mode':mode,'front':front,'view':case['view'],'count':n,'captured':int(captured.sum()),'gas':int(gas.sum()),'massRemaining':gas_mass,'massReceived':received,'massResidual':abs(gas_mass+received-1),'gasStillMoving':True,'allCapturedPixelsInsideNativeOccupancy':True,'partitionExactCaptureIds':True,'partitionPositionMaxError':float(np.max(abs(positions-r['positions']))),'pythonSeconds':elapsed,'normalizationFlowRateForFullMask':flow,'frontFluxVariesWithOccupiedBand':front is not None,'normalizedFineMaximumRate':float(rate*receiver.max())})
result={'schema':'fine-native-receiver-qualification/1','status':'PASS native-mask interception with static or affine moving-front gate; full native glyph/fluid/first-wave formation unavailable','nativeMaskDataSha256':meta['dataSha256'],'maskAccuracy':'Actual native VKF8bitalpha occupancy per1CSSpixel, not exact continuous-curve containment or an SDF','velocity':[.12,.04,.005],'seed':712,'rows':rows,'limitations':['Uniform-flow exact-NS test isolates interception; not turbulent full presentation','Fine air-pressure/velocity near glyphs unqualified','Only affine finite-width front qualified; nonlinear/shape-changing front remains unqualified','Native GPU kernel and native authoritative particle ledger not integrated','Captured mass to native stroke formation unqualified'],'sourceHashes':{name:hashlib.sha256((root/name).read_bytes()).hexdigest()for name in ['fine_receiver_reference.py','test_fine_receiver.py','qualify_fine_receiver.py']}}
(root/'FINE_RECEIVER_QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(rows,indent=2))
