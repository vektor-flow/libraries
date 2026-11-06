import unittest,numpy as np
from ns_reference import Smoke,Config
from parcels import ParcelSmoke,diffusion_displacement

class ProbeTests(unittest.TestCase):
    def test_physical_diffusion_has_einstein_variance_and_no_spurious_drift(self):
        cfg=Config(shape=(8,8,8),lengths=(1,1,1),cs=0,buoyancy=0,loading=0,diffusivity=.003,cooling=0,collector_flux=0)
        fluid=Smoke(cfg);fluid.c[0]=1;s=ParcelSmoke.from_fluid(fluid,count=20000,seed=19);s.positions[:]=.5;s.velocities[:]=0;s.advance_to(.25)
        displacement=s.positions-.5
        np.testing.assert_allclose(displacement.mean(axis=0),0,atol=.001)
        np.testing.assert_allclose(displacement.var(axis=0),2*cfg.diffusivity*.25,rtol=.04)
        np.testing.assert_allclose(s.parcel_mass(),[1,0,0],atol=1e-12)

    def test_snapshot_and_observer_cadence_preserve_particle_rng_and_velocity(self):
        f=Smoke.plumes(Config(shape=(8,8,8),collector_start=.1,collector_flux=.02),seed=9)
        a=ParcelSmoke.from_fluid(f,count=2048,seed=12);b=ParcelSmoke.from_snapshot(a.snapshot());c=ParcelSmoke.from_snapshot(a.snapshot());a.advance_to(.3)
        for _ in range(30):b.advance(.01)
        c.advance_to(.15);c=ParcelSmoke.from_snapshot(c.snapshot());c.advance_to(.3)
        for p in [b,c]:
            for name in ['positions','velocities','species','weights','alive','parcel_deposited','u','c']:np.testing.assert_array_equal(getattr(a,name),getattr(p,name))
            self.assertEqual(a.rng.bit_generator.state,p.rng.bit_generator.state)

    def test_collector_and_finite_parcels_conserve_mass_without_teleporting_residual(self):
        cfg=Config(shape=(8,8,8),lengths=(1,1,1),cs=0,buoyancy=0,loading=0,diffusivity=0,cooling=0,collector_start=0,collector_flux=1)
        fluid=Smoke(cfg);fluid.c[0]=1;fluid.set_collector(np.ones(fluid.shape),np.ones(fluid.shape));s=ParcelSmoke.from_fluid(fluid,count=10000,seed=24);initial=s.parcel_mass().copy();s.advance_to(.5)
        np.testing.assert_allclose(s.parcel_mass()+s.parcel_deposited,initial,atol=2e-12)
        expected=np.exp(-.25);self.assertLess(abs(s.parcel_mass()[0]-expected),.02)
        self.assertGreater(s.parcel_deposited[0],0);self.assertGreater(s.parcel_mass()[0],0)
        self.assertGreater(s.mass()[0],0)

    def test_variable_diffusivity_preserves_a_well_mixed_distribution(self):
        shape=(32,4,4);h=np.array([1/n for n in shape]);k=np.broadcast_to((.03*(1+.8*np.sin(2*np.pi*(np.arange(32)+.5)/32)))[:,None,None],shape).copy()
        rng=np.random.default_rng(43);x=rng.random((16384,3))
        for _ in range(200):x=np.mod(x+diffusion_displacement(k,h,x,.01,rng),1)
        for mode in [np.sin,np.cos]:self.assertLess(abs(mode(2*np.pi*x[:,0]).mean()),.03)

    def test_spatial_capture_converges_to_integrated_physical_hazard(self):
        from scipy.special import i0
        from parcels import scalar_at
        Q=3.;T=.35;a=T/.5;integral=Q*.5*(2.5*a**4-3*a**5+a**6);exact=np.exp(-integral)*i0(.8*integral)
        spatial_errors=[]
        for nx in [8,32]:
            cfg=Config(shape=(nx,4,4),lengths=(1,1,1),cs=0,buoyancy=0,loading=0,diffusivity=0,cooling=0,collector_start=0,collector_flux=Q,max_dt=.005)
            f=Smoke(cfg);mask=np.broadcast_to((1+.8*np.cos(2*np.pi*(np.arange(nx)+.5)/nx))[:,None,None],f.shape).copy();f.set_collector(mask,mask)
            x=np.zeros((32768,3));x[:,0]=(np.arange(len(x))+.5)/len(x);x[:,1:]=.5
            hazard=np.zeros(len(x))
            for step in range(70):hazard+=scalar_at(f.ports((step+.5)*.005)[0],f.h,x)*.005
            spatial_errors.append(abs(np.exp(-hazard).mean()-exact))
        self.assertLess(spatial_errors[1],spatial_errors[0]/8)
        # Coupled parcel/continuum uptake at spatially varying rate, with an
        # explicit Monte Carlo confidence bound rather than exact equality.
        f.c[0]=1;s=ParcelSmoke.from_fluid(f,count=20000,seed=44);s.advance_to(T)
        p=float(s.mass()[0]);sigma=np.sqrt(p*(1-p)/len(s.positions))
        self.assertLess(abs(s.parcel_mass()[0]-p),5*sigma+.004)

    def test_particle_capture_hazard_refines_in_physical_time(self):
        from parcels import scalar_at
        Q=3.;T=.35;a=T/.5;integral=Q*.5*(2.5*a**4-3*a**5+a**6);errors=[]
        for dt in [.05,.025,.0125]:
            cfg=Config(shape=(32,4,4),lengths=(1,1,1),nu=0,cs=0,buoyancy=0,loading=0,diffusivity=0,thermal_diffusivity=0,cooling=0,collector_start=0,collector_flux=Q,max_dt=dt)
            f=Smoke(cfg);mask=np.broadcast_to((1+.8*np.cos(2*np.pi*(np.arange(32)+.5)/32))[:,None,None],f.shape).copy();f.set_collector(mask,mask);f.c[0]=1
            s=ParcelSmoke.from_fluid(f,count=4096,seed=71);s.advance_to(T);ids=s.alive
            expected=scalar_at(f.collector_mask,f.h,s.positions[ids])*integral
            errors.append(np.sqrt(np.mean((s.capture_exposure[ids]-expected)**2)))
        self.assertLess(errors[1],errors[0]/3.5);self.assertLess(errors[2],errors[1]/3.5)

if __name__=='__main__':unittest.main()
