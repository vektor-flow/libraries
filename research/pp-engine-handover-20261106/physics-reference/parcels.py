"""Fine dilute smoke probes of the SAME Navier–Stokes field.
The finite-volume concentrations remain the continuum loading/reference.
These probes independently approximate its advection/diffusion/capture law;
never add probe mass to continuum mass. No independent vortex trajectories.
"""
import copy
import numpy as np
from scipy.ndimage import map_coordinates
from ns_reference import Smoke,strain_viscosity,sample_velocity

def scalar_at(field,h,positions):
    return map_coordinates(field,(positions/np.asarray(h)-.5).T,order=1,mode='grid-wrap',prefilter=False)

def diffusion_displacement(field,h,positions,dt,rng):
    if np.max(field)==0:return np.zeros_like(positions)
    coefficient=scalar_at(field,h,positions)
    gradient=np.array([scalar_at((np.roll(field,-1,axis=j)-np.roll(field,1,axis=j))/(2*h[j]),h,positions) for j in range(3)]).T
    return gradient*dt+np.sqrt(2*coefficient*dt)[:,None]*rng.normal(size=positions.shape)

class ParcelSmoke(Smoke):
    def __init__(self,cfg):
        super().__init__(cfg);self.positions=np.empty((0,3));self.velocities=np.empty((0,3));self.species=np.empty(0,dtype=np.int16);self.weights=np.empty(0);self.alive=np.empty(0,dtype=bool);self.parcel_deposited=np.zeros(3);self.capture_exposure=np.empty(0);self.capture_threshold=np.empty(0);self.rng=None

    @classmethod
    def from_fluid(cls,fluid,count=16384,seed=702):
        s=cls.from_snapshot(fluid.snapshot());s.initialise(count,seed);return s

    def initialise(self,count,seed):
        if not isinstance(count,int) or count<1 or count>131072:raise ValueError('Bounded fine-probe count1..131072 required')
        masses=self.mass();total=float(masses.sum())
        if total<=0 or self.c.min()<0:raise ValueError('Nonnegative source material is required for probes')
        self.rng=np.random.default_rng(seed);counts=np.floor(count*masses/total).astype(int)
        for k in np.argsort(count*masses/total-counts)[::-1][:count-int(counts.sum())]:counts[k]+=1
        positions=[];species=[];weights=[]
        for k,n in enumerate(counts):
            if n==0:continue
            selected=self.rng.choice(np.prod(self.shape),size=n,p=(self.c[k]/self.c[k].sum()).ravel())
            cells=np.array(np.unravel_index(selected,self.shape)).T
            positions.append((cells+self.rng.random((n,3)))*self.h);species.extend([k]*n);weights.extend([masses[k]/n]*n)
        self.positions=np.concatenate(positions);self.species=np.asarray(species,dtype=np.int16);self.weights=np.asarray(weights);self.alive=np.ones(count,dtype=bool);self.velocities=sample_velocity(self.u,self.h,self.positions);self.parcel_deposited=np.zeros(3);self.capture_exposure=np.zeros(count);self.capture_threshold=self.rng.exponential(size=count)

    def step(self,dt):
        old_u=self.u.copy();old_time=self.time
        super().step(dt) # No RNG or probe mutation until a fluid step is accepted.
        if self.rng is None or not self.alive.any():return
        ids=np.flatnonzero(self.alive);x=self.positions[ids];umid=(old_u+self.u)/2
        predict=x+sample_velocity(old_u,self.h,x)*(.5*dt)
        advect=sample_velocity(umid,self.h,predict)*dt
        diffusivity=self.cfg.diffusivity+(strain_viscosity(old_u,self.h,self.cfg.nu,self.cfg.cs)-self.cfg.nu)/self.cfg.schmidt
        # Ito drift grad(K) is required for Fickian div(K grad(c)); otherwise
        # variable turbulent diffusivity creates spurious particle piling.
        delta=advect+diffusion_displacement(diffusivity,self.h,x,dt,self.rng)
        middle=x+.5*delta;end=np.mod(x+delta,np.asarray(self.cfg.lengths))
        self.positions[ids]=end;self.velocities[ids]=sample_velocity(self.u,self.h,end)
        sink,_=self.ports(old_time+dt/2);rate=scalar_at(sink,self.h,middle)
        self.capture_exposure[ids]+=rate*dt
        captured=self.capture_exposure[ids]>=self.capture_threshold[ids]
        chosen=ids[captured];self.alive[chosen]=False
        self.parcel_deposited+=np.bincount(self.species[chosen],weights=self.weights[chosen],minlength=3)

    def parcel_mass(self):return np.bincount(self.species[self.alive],weights=self.weights[self.alive],minlength=3)

    def snapshot(self):
        value=super().snapshot()
        if self.rng is not None:value['probes']={'positions':self.positions.copy(),'velocities':self.velocities.copy(),'species':self.species.copy(),'weights':self.weights.copy(),'alive':self.alive.copy(),'capture_exposure':self.capture_exposure.copy(),'capture_threshold':self.capture_threshold.copy(),'deposited':self.parcel_deposited.copy(),'rng':copy.deepcopy(self.rng.bit_generator.state)}
        return value

    @classmethod
    def from_snapshot(cls,snapshot):
        s=super().from_snapshot(snapshot)
        if 'probes' in snapshot:
            p=snapshot['probes']
            for name in ['positions','velocities','species','weights','alive','capture_exposure','capture_threshold']:setattr(s,name,p[name].copy())
            s.parcel_deposited=p['deposited'].copy();s.rng=np.random.default_rng();s.rng.bit_generator.state=copy.deepcopy(p['rng'])
        return s
