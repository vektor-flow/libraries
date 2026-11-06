"""Numerically generated data for VKF native point-cloud rendering only."""
import json,time,hashlib,sys
from pathlib import Path
import numpy as np
from demo_case import make_demo
from ns_reference import Smoke,Config,project,sample_velocity
from parcels import ParcelSmoke

root=Path(__file__).parent;fluid_only='--fluid-only' in sys.argv;name='fluid-only' if fluid_only else 'visual-proof';fps=30;duration=12 if fluid_only else 6
if fluid_only:
    cfg=Config(shape=(24,16,8),nu=.0004,cs=0,diffusivity=0,buoyancy=0,loading=0,cooling=0,collector_flux=0)
    fluid=Smoke(cfg);X=fluid.centres;L=np.array(cfg.lengths)
    for k,centre in enumerate([[.28,.28,.5],[.54,.50,.5],[.28,.72,.5]]):
        mask=np.ones(fluid.shape,dtype=bool)
        for j in range(3):mask &= abs(X[j]-centre[j]*L[j])<([.075,.075,.16][j]*L[j])
        fluid.c[k]=mask*.001/(mask.sum()*fluid.dv)
    rng=np.random.default_rng(881);faces=fluid.face_coordinates()
    for mode in range(10):
        wave=rng.integers(-2,3,size=3);wave[2]=rng.integers(-1,2)
        if not wave.any():wave[0]=1
        kphys=2*np.pi*wave/L;amplitude=rng.normal(size=3);amplitude-=kphys*np.dot(amplitude,kphys)/np.dot(kphys,kphys);phase=rng.uniform(0,2*np.pi)
        for j in range(3):fluid.u[j]+=amplitude[j]*np.cos(sum(kphys[d]*faces[j][d] for d in range(3))+phase)
    fluid.u,fluid.pressure=project(fluid.u,fluid.h,cfg.max_dt);fluid.u*=.055/np.sqrt(np.mean(np.sum(fluid.u**2,axis=0)))
    s=ParcelSmoke.from_fluid(fluid,count=8192,seed=882)
else:s=make_demo(count=8192)
initial=s.mass().copy();initial_parcels=s.parcel_mass().copy();frames=[];offset=0;times=[]
# These are the authored semantic source colours (gold, mint, white). Display
# optics are separate from conserved species composition and fluid evolution.
palette=np.array([[.9137254901960784,.7686274509803922,.41568627450980394],[.47058823529411764,.8274509803921568,.7764705882352941],[.9647058823529412,.9725490196078431,.9764705882352941]])
with (root/(name+'.bin')).open('wb') as file:
    for frame in range(duration*fps+1):
        started=time.perf_counter();s.advance_to(frame/fps);times.append((time.perf_counter()-started)*1000)
        ids=np.flatnonzero(s.alive);positions=s.positions[ids];data=np.empty((len(ids),7),dtype='<f4');data[:,0]=180+positions[:,0]*540;data[:,1]=640-positions[:,1]*540;data[:,2]=.7;data[:,3:6]=palette[s.species[ids]];data[:,6]=.9
        file.write(data.tobytes());mass=s.mass();parcels=s.parcel_mass()
        assert np.max(np.abs(mass+s.deposited-initial))<1e-11
        assert np.max(np.abs(parcels+s.parcel_deposited-initial_parcels))<1e-11
        frames.append({'offsetFloats':offset,'count':len(ids),'time':s.time,'physicsTicks':s.ticks,'physicsSteps':s.steps,'parcelGasMass':parcels.tolist(),'parcelCapturedMass':s.parcel_deposited.tolist(),'continuumGasMass':mass.tolist(),'continuumCapturedMass':s.deposited.tolist(),'capturedFraction':float(s.parcel_deposited.sum()/initial_parcels.sum()),'divergenceResidual':s.last.get('divergenceResidualMax',0),'stageResidual':s.last.get('stageDivergenceResidualMax',0)})
        offset+=data.size
        if frame%30==0:print('VISUAL',frame,'alive',len(ids),'captured',frames[-1]['capturedFraction'],'simulationMs',round(times[-1],2),flush=True)
sources={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['ns_reference.py','parcels.py','demo_case.py']}
r={'schema':'ns-smoke-native-visual-data/1','frameRate':fps,'width':1280,'height':720,'duration':duration,'sourceHashes':sources,'backend':'CPU float64 fluid/probes, VKF native rendering; not a client GPU fluid implementation','particleVelocityMeaning':'resolved air velocity; not Brownian derivative','units':'nondimensional reference','collectorActive':not fluid_only,'collector':'none: unforced fluid-only test' if fluid_only else 'balanced return-air supply; smoothly moving mask; residual remains live','palette':palette.tolist(),'config':__import__('dataclasses').asdict(s.cfg),'initialKineticEnergy':float(.5*np.sum(fluid.u**2)*fluid.dv) if fluid_only else None,'initialContinuumMass':initial.tolist(),'initialProbeMass':initial_parcels.tolist(),'simulationMsP50':float(np.percentile(times[1:],50)),'simulationMsP95':float(np.percentile(times[1:],95)),'simulationRealTimeRatio':duration/(sum(times)/1000),'frames':frames,'dataBytes':(root/(name+'.bin')).stat().st_size,'dataSha256':hashlib.sha256((root/(name+'.bin')).read_bytes()).hexdigest()}
(root/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');print('DATA READY',r['simulationMsP50'],r['simulationMsP95'],r['simulationRealTimeRatio'],flush=True)
