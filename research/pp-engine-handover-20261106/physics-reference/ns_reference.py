"""Verification prototype, not imported by Platonic Play.
3D staggered incompressible Navier–Stokes/Boussinesq with conservative pigments.
Periodic reference domain; declared balanced porous collector/return-air ports.
All viscosity, scalar diffusion and capture have explicit units/configuration.
"""
from dataclasses import dataclass, asdict
import copy
import math
import numpy as np
from scipy.fft import rfftn, irfftn
from scipy.ndimage import map_coordinates, gaussian_filter

@dataclass(frozen=True)
class Config:
    shape: tuple = (24, 16, 8)
    lengths: tuple = (1.6, 1., .4)
    nu: float = .001
    cs: float = .12
    diffusivity: float = .00005
    thermal_diffusivity: float = .0002
    schmidt: float = .7
    prandtl: float = .7
    buoyancy: float = .3
    loading: float = .025
    cooling: float = .25
    max_dt: float = 1/60
    cfl: float = .3
    collector_start: float = 3.
    collector_flux: float = .05


def divergence(u, h):
    return sum((np.roll(u[i], -1, axis=i)-u[i])/h[i] for i in range(3))


def project(u, h, dt, volume_source=None):
    shape=u.shape[1:]; rhs=divergence(u,h)
    if volume_source is not None:
        if abs(float(np.mean(volume_source)))>1e-11*max(1,float(np.max(np.abs(volume_source)))):
            raise ValueError('Incompressible volume ports must have zero net volume flux')
        rhs=rhs-volume_source
    eigen=np.zeros((shape[0],shape[1],shape[2]//2+1))
    for i,n in enumerate(shape):
        k=np.arange(n if i<2 else n//2+1)
        term=-4*np.sin(np.pi*k/n)**2/h[i]**2
        dims=[1,1,1];dims[i]=len(k);eigen+=term.reshape(dims)
    ph=rfftn(rhs/dt,workers=1);eigen[0,0,0]=1;ph/=eigen;ph[0,0,0]=0
    p=irfftn(ph,s=shape,workers=1)
    corrected=np.array([u[i]-dt*(p-np.roll(p,1,axis=i))/h[i] for i in range(3)])
    return corrected,p


def shear(u,h,i,j):
    return (u[i]-np.roll(u[i],1,axis=j))/h[j]+(u[j]-np.roll(u[j],1,axis=i))/h[i]


def strain_viscosity(u,h,nu,cs):
    if cs==0:return np.full(u.shape[1:],nu)
    square=sum(((np.roll(u[i],-1,axis=i)-u[i])/h[i])**2 for i in range(3))
    for i in range(3):
        for j in range(i+1,3):
            sij=shear(u,h,i,j)/2
            # Filter strain ENERGY, not signed shear: opposing unresolved
            # shears must not cancel before the SGS dissipation is estimated.
            energy=sij*sij
            square+=2*(energy+np.roll(energy,-1,axis=i)+np.roll(energy,-1,axis=j)+np.roll(np.roll(energy,-1,axis=i),-1,axis=j))/4
    return nu+(cs*np.prod(h)**(1/3))**2*np.sqrt(2*square)


def viscous_force(u,h,nu):
    out=np.zeros_like(u)
    for i in range(3):
        diagonal=2*nu*(np.roll(u[i],-1,axis=i)-u[i])/h[i]
        out[i]+=(diagonal-np.roll(diagonal,1,axis=i))/h[i]
        for j in range(3):
            if i==j:continue
            edge_nu=(nu+np.roll(nu,1,axis=i)+np.roll(nu,1,axis=j)+np.roll(np.roll(nu,1,axis=i),1,axis=j))/4
            stress=edge_nu*shear(u,h,i,j)
            out[i]+=(np.roll(stress,-1,axis=j)-stress)/h[j]
    return out


def momentum_advection(u,h):
    out=np.zeros_like(u)
    for i in range(3):
        for j in range(3):
            right=np.roll(u[j],-1,axis=j)
            transport=(u[i]+right)/2 if i==j else (right+np.roll(right,1,axis=i))/2
            flux=transport*(u[i]+np.roll(u[i],-1,axis=j))/2
            out[i]-=(flux-np.roll(flux,1,axis=j))/h[j]
    return out


def scalar_rhs(q,u,h,kappa):
    out=np.zeros_like(q)
    for axis in range(3):
        left=q-np.roll(q,1,axis=axis);right=np.roll(q,-1,axis=axis)-q
        slope=np.where(left*right>0,np.sign(left)*np.minimum(np.abs(left),np.abs(right)),0)
        ql=q+.5*slope;qr=np.roll(q-.5*slope,-1,axis=axis);velocity=np.roll(u[axis],-1,axis=axis)
        kface=(kappa+np.roll(kappa,-1,axis=axis))/2
        flux=velocity*np.where(velocity>=0,ql,qr)-kface*(np.roll(q,-1,axis=axis)-q)/h[axis]
        out-=(flux-np.roll(flux,1,axis=axis))/h[axis]
    return out


def sample_velocity(u,h,positions):
    result=[]
    for i in range(3):
        offset=np.full(3,.5);offset[i]=0
        coords=(positions/np.asarray(h)-offset).T
        result.append(map_coordinates(u[i],coords,order=1,mode='grid-wrap',prefilter=False))
    return np.array(result).T


def advect_markers(x,v,u,h,dt,tau=0):
    # Small-Stokes-number tracers share resolved air motion. Optional finite
    # response integrates linear Stokes drag exactly for frozen sampled air.
    air=sample_velocity(u,h,x)
    if tau>0:
        decay=np.exp(-dt/tau);nv=air+(v-air)*decay
        nx=x+air*dt+(v-air)*tau*(1-decay)
    else:
        mid=x+air*(dt/2);nv=sample_velocity(u,h,mid);nx=x+nv*dt
    nx=np.mod(nx,np.asarray(u.shape[1:])*h)
    if tau==0:nv=sample_velocity(u,h,nx)
    return nx,nv


class Smoke:
    def __init__(self,cfg=Config()):
        if len(cfg.shape)!=3 or any(isinstance(n,bool) or not isinstance(n,(int,np.integer)) or n<4 for n in cfg.shape):raise ValueError('Three positive integer grid dimensions of at least4 are required')
        if len(cfg.lengths)!=3 or not all(np.isfinite(n) and n>0 for n in cfg.lengths):raise ValueError('Three finite positive domain lengths are required')
        coefficients=[cfg.nu,cfg.cs,cfg.diffusivity,cfg.thermal_diffusivity,cfg.schmidt,cfg.prandtl,cfg.buoyancy,cfg.loading,cfg.cooling,cfg.max_dt,cfg.cfl,cfg.collector_start,cfg.collector_flux]
        if not all(np.isfinite(n) for n in coefficients):raise ValueError('All physical coefficients must be finite')
        if not 0<cfg.cfl<=.5:raise ValueError('The configured transport CFL bound must lie in (0,.5]')
        self.cfg=cfg;self.shape=tuple(cfg.shape);self.h=np.array(cfg.lengths)/self.shape;self.dv=float(np.prod(self.h))
        if len(self.shape)!=3 or min(self.shape)<4:raise ValueError('A three-dimensional grid of at least4 cells per axis is required')
        if min(cfg.nu,cfg.cs,cfg.diffusivity,cfg.thermal_diffusivity,cfg.cooling,cfg.collector_flux)<0:raise ValueError('Negative transport coefficients are unsupported')
        if min(cfg.max_dt,cfg.schmidt,cfg.prandtl,cfg.cfl)<=0:raise ValueError('Positive time/transport bounds required')
        self.centres=np.meshgrid(*[(np.arange(n)+.5)*d for n,d in zip(self.shape,self.h)],indexing='ij')
        self.u=np.zeros((3,*self.shape));self.c=np.zeros((3,*self.shape));self.temperature=np.zeros(self.shape);self.pressure=np.zeros(self.shape);self.deposited=np.zeros(3)
        self.time=0.;self.steps=0;self.last={};self.seed=None;self.collector_mask=None;self.supply_mask=None;self.port_lift=None;self.port_pressure=None;self.ticks=0;self.observation_ns=0;self.next_ports=None;self.mask_start=0.;self.mask_duration=0.

    def face_coordinates(self):
        result=[]
        for i in range(3):
            result.append(np.meshgrid(*[(np.arange(n)+(0 if i==j else .5))*d for j,(n,d) in enumerate(zip(self.shape,self.h))],indexing='ij'))
        return result

    @classmethod
    def plumes(cls,cfg=Config(),seed=1):
        s=cls(cfg);s.seed=seed;rng=np.random.default_rng(seed)
        X=s.centres;L=np.array(cfg.lengths)
        for k in range(3):
            centre=L*np.array([.28,.23+.19*k,.5]);width=L*np.array([.07,.05,.17])
            g=np.exp(-sum(((X[i]-centre[i])/width[i])**2 for i in range(3))/2)
            s.c[k]=.001*g/(g.sum()*s.dv);s.temperature+=.4*g
            s.u[1]+=.12*(g+np.roll(g,1,axis=1))/2
        for i in range(3):s.u[i]+=gaussian_filter(rng.normal(size=s.shape),1.0,mode='wrap')*.035
        s.u,s.pressure=project(s.u,s.h,cfg.max_dt)
        # Demonstration conditions only. The solver accepts any native mask.
        centre=L*np.array([.72,.58,.30]);width=L*np.array([.10,.13,.14])
        collector=np.exp(-sum(((X[i]-centre[i])/width[i])**2 for i in range(3))/2)
        supply=np.exp(-((X[2]-.80*L[2])/(.10*L[2]))**2/2)*np.ones(s.shape)
        s.set_collector(collector,supply)
        return s

    def normalised_ports(self,collector,supply):
        masks=[]
        for value in [collector,supply]:
            value=np.asarray(value,dtype=np.float64)
            if value.shape!=self.shape or not np.all(np.isfinite(value)) or value.min()<0 or value.sum()<=0:
                raise ValueError('Collector and return-air masks require finite nonnegative nonempty grid fields')
            masks.append(value.copy()/(value.sum()*self.dv))
        lift,potential=project(np.zeros_like(self.u),self.h,1,masks[1]-masks[0])
        return (*masks,lift,potential)

    def set_collector(self, collector, supply):
        if self.flow_rate(self.time)[0]>0:raise ValueError('An active collector must use a smooth mask transition')
        self.collector_mask,self.supply_mask,self.port_lift,self.port_pressure=self.normalised_ports(collector,supply)
        self.next_ports=None

    def transition_collector(self,collector,supply,duration,start_time=None):
        start=self.time if start_time is None else start_time
        if not np.isfinite(duration) or duration<=0 or not np.isfinite(start) or start<self.time:raise ValueError('A finite positive future mask-transition interval is required')
        if self.collector_mask is None:raise ValueError('An initial collector must be supplied')
        prepared=self.normalised_ports(collector,supply)
        if self.next_ports is not None:
            if self.time<self.mask_start+self.mask_duration:raise ValueError('The previous mask transition is still active')
            self.collector_mask,self.supply_mask,self.port_lift,self.port_pressure=self.next_ports
        self.next_ports=prepared;self.mask_start=start;self.mask_duration=duration

    def flow_rate(self,time):
        elapsed=time-self.cfg.collector_start
        if elapsed<=0:return 0.,0.
        a=min(1,elapsed/.5);ramp=a*a*a*(10+a*(-15+6*a))
        derivative=0 if a>=1 else 30*a*a*(1-a)**2/.5
        return self.cfg.collector_flux*ramp,self.cfg.collector_flux*derivative

    def boundary(self,time):
        q,qd=self.flow_rate(time)
        if q==0:
            return {'sink':np.zeros(self.shape),'source':np.zeros(self.shape),'lift':np.zeros_like(self.u),'pressureRate':np.zeros(self.shape)}
        if self.collector_mask is None or self.supply_mask is None:raise ValueError('An active collector requires explicit collector and return-air masks')
        old=(self.collector_mask,self.supply_mask,self.port_lift,self.port_pressure);values=old;derivative=np.zeros(self.shape)
        if self.next_ports is not None:
            a=np.clip((time-self.mask_start)/self.mask_duration,0,1);mix=a*a*a*(10+a*(-15+6*a));dmix=30*a*a*(1-a)**2/self.mask_duration if 0<a<1 else 0
            values=tuple((1-mix)*u+mix*v for u,v in zip(old,self.next_ports));derivative=q*dmix*(self.next_ports[3]-old[3])
        collect,supply,lift,potential=values
        return {'sink':q*collect,'source':q*(supply-collect),'lift':q*lift,'pressureRate':qd*potential+derivative}

    def ports(self,time=None):
        value=self.boundary(self.time if time is None else time)
        return value['sink'],value['source']

    def rhs(self,state,sink):
        u,T,c,_=state;cfg=self.cfg;nu=strain_viscosity(u,self.h,cfg.nu,cfg.cs);eddy=nu-cfg.nu
        du=momentum_advection(u,self.h)+viscous_force(u,self.h,nu)
        b=cfg.buoyancy*(T-T.mean())-cfg.loading*(c.sum(axis=0)-c.sum(axis=0).mean())
        du[1]+=(b+np.roll(b,1,axis=1))/2
        for i in range(3):du[i]-=(sink+np.roll(sink,1,axis=i))/2*u[i]
        dT=scalar_rhs(T,u,self.h,cfg.thermal_diffusivity+eddy/cfg.prandtl)-(cfg.cooling+sink)*T
        dc=np.array([scalar_rhs(q,u,self.h,cfg.diffusivity+eddy/cfg.schmidt)-sink*q for q in c])
        deposit=np.sum(sink*c,axis=(1,2,3))*self.dv
        return du,dT,dc,deposit

    def transport_rate(self,u,time,boundary=None):
        sink=(self.boundary(time) if boundary is None else boundary)['sink'];nu=strain_viscosity(u,self.h,self.cfg.nu,self.cfg.cs);eddy=nu-self.cfg.nu
        largest=max(float(nu.max()),float((self.cfg.diffusivity+eddy/self.cfg.schmidt).max()),float((self.cfg.thermal_diffusivity+eddy/self.cfg.prandtl).max()))
        return sum(float(np.max(np.abs(u[i])))/self.h[i] for i in range(3))+4*largest*sum(1/self.h**2)+float(sink.max())+self.cfg.cooling

    def step(self,dt):
        if not np.isfinite(dt) or dt<=0 or dt>self.cfg.max_dt+1e-12:raise ValueError('Timestep must be finite, positive and within the configured bound')
        t=self.time;boundaries={}
        def boundary(when):
            if when not in boundaries:boundaries[when]=self.boundary(when)
            return boundaries[when]
        lift=lambda when:boundary(when)['lift']
        # u=w+L(t), D w=0, D L=s(t). L is a gradient, so P(dL/dt)=0.
        # Evolve w with Leray-projected RHS; reconstruct the actual velocity at
        # each SSPRK3 stage time. Affine constraints survive EVERY combination.
        initial=(self.u-lift(t),self.temperature,self.c,self.deposited);stages=[];pressure=None
        def evaluate(state,when):
            nonlocal pressure
            actual=(state[0]+lift(when),*state[1:]);b=boundary(when);sink,source=b['sink'],b['source']
            if not all(np.all(np.isfinite(a)) for a in actual):raise FloatingPointError('Nonfinite RK stage')
            minimum=min(float(actual[1].min()),float(actual[2].min()))
            if minimum < -1e-11:raise FloatingPointError('RK stage transport positivity failed')
            residual=float(np.max(np.abs(divergence(actual[0],self.h)-source)))
            courant=float(dt*self.transport_rate(actual[0],when,b))
            if courant>self.cfg.cfl*(1+1e-10):raise FloatingPointError('RK stage exceeds the transport CFL bound')
            stages.append({'time':when,'divergenceResidualMax':residual,'minimum':minimum,'transportCourant':courant})
            if residual>1e-9:raise FloatingPointError('RK stage violates its incompressible port constraint')
            rhs=self.rhs(actual,sink);dw,pressure=project(rhs[0],self.h,1)
            return (dw,*rhs[1:])
        def forward(state,when):return tuple(a+dt*b for a,b in zip(state,evaluate(state,when)))
        one=forward(initial,t)
        two=forward(one,t+dt);two=tuple(.75*a+.25*b for a,b in zip(initial,two))
        three=forward(two,t+.5*dt);three=tuple(a/3+2*b/3 for a,b in zip(initial,three))
        actual=(three[0]+lift(t+dt),*three[1:]);b=boundary(t+dt);sink,source=b['sink'],b['source']
        if not all(np.all(np.isfinite(a)) for a in actual) or min(float(actual[1].min()),float(actual[2].min())) < -1e-11:raise FloatingPointError('Invalid final transport state')
        final_residual=float(np.max(np.abs(divergence(actual[0],self.h)-source)))
        if final_residual>1e-9:raise FloatingPointError('Final port constraint failed')
        final_courant=float(dt*self.transport_rate(actual[0],t+dt,b))
        if final_courant>self.cfg.cfl*(1+1e-10):raise FloatingPointError('Final state exceeds the transport CFL bound')
        self.u,self.temperature,self.c,self.deposited=actual
        # Pressure from the final RHS plus the known time-dependent lift term.
        self.pressure=pressure+boundary(t+.5*dt)['pressureRate']
        self.time=t+dt;self.steps+=1
        self.last={'dt':dt,'divergenceResidualMax':final_residual,'stageDivergenceResidualMax':max(x['divergenceResidualMax'] for x in stages),'stageMinimum':min(x['minimum'] for x in stages),'stageTransportCourant':max(x['transportCourant'] for x in stages),'finalTransportCourant':final_courant,'stages':stages,'volumePortBalance':float(source.sum()*self.dv),'kineticEnergy':float(.5*np.sum(self.u**2)*self.dv),'minConcentration':float(self.c.min()),'gasMass':self.mass().tolist(),'depositedMass':self.deposited.tolist()}

    def advance_to(self,seconds):
        if not np.isfinite(seconds) or seconds<0:raise ValueError('Observation time must be finite and nonnegative')
        target_ns=int(round(seconds*1e9))
        if target_ns<self.observation_ns:raise ValueError('Rewind requires a complete fluid checkpoint')
        if seconds>self.cfg.collector_start and self.cfg.collector_flux>0 and (self.collector_mask is None or self.supply_mask is None):raise ValueError('An active collector requires explicit collector and return-air masks')
        target_ticks=math.floor(((target_ns+.5)/1e9)/self.cfg.max_dt);budget=100000
        while self.ticks<target_ticks:
            end=(self.ticks+1)*self.cfg.max_dt
            while end-self.time>1e-12:
                if budget<=0:raise RuntimeError('Bounded step budget exhausted')
                rate=self.transport_rate(self.u,self.time)
                dt=min(self.cfg.max_dt,self.cfg.cfl/max(rate,1e-12),end-self.time)
                for attempt in range(12):
                    try:self.step(dt);break
                    except FloatingPointError:
                        dt/=2
                        if attempt==11:raise
                budget-=1
            self.ticks+=1;self.time=self.ticks*self.cfg.max_dt
        self.observation_ns=target_ns
        return self.last

    def advance(self,seconds):
        if not np.isfinite(seconds) or seconds<0:raise ValueError('Advance time must be finite and nonnegative')
        return self.advance_to((self.observation_ns+int(round(seconds*1e9)))/1e9)

    def mass(self):return self.c.sum(axis=(1,2,3))*self.dv

    def snapshot(self):
        return {'schema':'ns-smoke-reference/1','config':asdict(self.cfg),'time':self.time,'steps':self.steps,'ticks':self.ticks,'observationNs':self.observation_ns,'seed':self.seed,'last':copy.deepcopy(self.last),'collectorMask':None if self.collector_mask is None else self.collector_mask.copy(),'supplyMask':None if self.supply_mask is None else self.supply_mask.copy(),'portLift':None if self.port_lift is None else self.port_lift.copy(),'portPressure':None if self.port_pressure is None else self.port_pressure.copy(),'nextPorts':None if self.next_ports is None else tuple(v.copy() for v in self.next_ports),'maskStart':self.mask_start,'maskDuration':self.mask_duration,**{k:getattr(self,k).copy() for k in ['u','temperature','c','pressure','deposited']}}

    @classmethod
    def from_snapshot(cls,snapshot):
        if snapshot['schema']!='ns-smoke-reference/1':raise ValueError('Unknown fluid snapshot')
        s=cls(Config(**snapshot['config']));s.time=snapshot['time'];s.steps=snapshot['steps'];s.ticks=snapshot['ticks'];s.observation_ns=snapshot['observationNs'];s.seed=snapshot['seed'];s.last=copy.deepcopy(snapshot['last'])
        for k in ['u','temperature','c','pressure','deposited']:setattr(s,k,snapshot[k].copy())
        if snapshot['collectorMask'] is not None:
            # Restore already-normalized ports bit-for-bit; do not normalize twice.
            s.collector_mask=snapshot['collectorMask'].copy();s.supply_mask=snapshot['supplyMask'].copy();s.port_lift=snapshot['portLift'].copy();s.port_pressure=snapshot['portPressure'].copy()
        s.next_ports=None if snapshot['nextPorts'] is None else tuple(v.copy() for v in snapshot['nextPorts']);s.mask_start=snapshot['maskStart'];s.mask_duration=snapshot['maskDuration']
        return s
