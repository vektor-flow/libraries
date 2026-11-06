"""Declared recorded-reference case; uses the existing solver unchanged."""
from pathlib import Path
import dataclasses,hashlib,json,time
import numpy as np
from ns_reference import Config,Smoke
from parcels import ParcelSmoke
root=Path(__file__).parent
cfg=Config(shape=(24,16,8),nu=.0004,cs=0,diffusivity=0,thermal_diffusivity=0,buoyancy=0,loading=0,cooling=0,collector_start=6,collector_flux=.06)
fluid=Smoke.plumes(cfg,seed=701);X=fluid.centres;L=np.array(cfg.lengths)
def collector(x):
 centre=L*np.array([x,.55,.5]);width=L*np.array([.16,.17,.40])
 return np.exp(-sum(((X[i]-centre[i])/width[i])**2 for i in range(3))/2)
supply=np.exp(-((X[0]-.08*L[0])/(.05*L[0]))**2/2)*np.ones(fluid.shape)
fluid.set_collector(collector(.70),supply);fluid.transition_collector(collector(.80),supply,1.,start_time=12.)
s=ParcelSmoke.from_fluid(fluid,count=16384,seed=702);initial=s.parcel_mass().copy();initial_continuum=s.mass().copy()
palette=np.array([[.9137254901960784,.7686274509803922,.41568627450980394],[.47058823529411764,.8274509803921568,.7764705882352941],[.9647058823529412,.9725490196078431,.9764705882352941]])
frames=[];offset=0;timings=[];name='presentation-reference';fps=24;duration=18
with (root/(name+'.bin')).open('wb') as f:
 for i in range(duration*fps+1):
  start=time.perf_counter();s.advance_to(i/fps);timings.append((time.perf_counter()-start)*1000)
  ids=np.flatnonzero(s.alive);p=s.positions[ids];data=np.empty((len(ids),7),dtype='<f4')
  data[:,0]=700+520*p[:,0]/L[0];data[:,1]=610-430*p[:,1]/L[1];data[:,2]=.45;data[:,3:6]=palette[s.species[ids]];data[:,6]=.85
  f.write(data.tobytes());gas=s.parcel_mass();captured=s.parcel_deposited;res=float(np.max(np.abs(gas+captured-initial)));cres=float(np.max(np.abs(s.mass()+s.deposited-initial_continuum)))
  assert res<1e-11 and cres<1e-11
  frames.append({'offsetFloats':offset,'count':len(ids),'gasCount':int(s.alive.sum()),'capturedCount':int((~s.alive).sum()),'time':s.time,'viewIndex':min(2,int(i/fps//6)),'viewTime':min(6.,i/fps%6) if i<duration*fps else 6.,'gasMass':gas.tolist(),'capturedMass':captured.tolist(),'probeMassResidual':res,'continuumMassResidual':cres,'divergenceResidual':s.last.get('divergenceResidualMax',0),'stageResidual':s.last.get('stageDivergenceResidualMax',0),'physicsTicks':s.ticks,'flowRate':s.flow_rate(s.time)[0]});offset+=data.size
  if i%24==0:print('FLUID',i,frames[-1]['gasCount'],round(float(captured.sum()/initial.sum()),4),flush=True)
meta={'schema':'ns-smoke-native-visual-data/1','backend':'CPU float64 Navier-Stokes reference; native VKF points/text, NOT an installed VKF GPU fluid solver','width':1280,'height':720,'frameRate':fps,'duration':duration,'config':dataclasses.asdict(cfg),'seeds':{'fluid':701,'probes':702},'initialProbeMass':initial.tolist(),'initialContinuumMass':initial_continuum.tolist(),'projection':{'x':[700,1220],'y':[180,610],'particleFootprintPx':.45},'frames':frames,'sourceHashes':{n:hashlib.sha256((root/n).read_bytes()).hexdigest()for n in ['ns_reference.py','parcels.py','make_presentation.py']},'dataSha256':hashlib.sha256((root/(name+'.bin')).read_bytes()).hexdigest(),'dataBytes':(root/(name+'.bin')).stat().st_size,'simulationMsP50':float(np.percentile(timings[1:],50)),'simulationMsP95':float(np.percentile(timings[1:],95)),'collector':'balanced porous collector starts6s; moves12–13s; residual retained','depositionDisplay':'Only live gas probes are rendered; absorbed material is accounted in the collector reservoir and is not shown as frozen smoke. This reference has no glyph reconstruction.'}
(root/(name+'.json')).write_text(json.dumps(meta,indent=2)+'\n');print('READY',meta['dataBytes'],meta['simulationMsP50'],flush=True)
