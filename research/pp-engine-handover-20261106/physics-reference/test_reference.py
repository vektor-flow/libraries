import unittest
import numpy as np
from ns_reference import Smoke, Config, project, divergence, viscous_force, strain_viscosity, advect_markers

class FluidTests(unittest.TestCase):
    def test_projection_removes_divergence_without_changing_mean_momentum(self):
        rng=np.random.default_rng(11); shape=(12,10,8); h=np.array([1/n for n in shape]); u=rng.normal(size=(3,*shape)); v,p=project(u,h,.01)
        self.assertLess(np.max(np.abs(divergence(v,h))),1e-11)
        np.testing.assert_allclose(v.mean(axis=(1,2,3)),u.mean(axis=(1,2,3)),atol=1e-14)

    def test_projection_honours_balanced_volume_ports(self):
        shape=(12,10,8);h=np.array([1/n for n in shape]);s=np.zeros(shape);s[2,3,2]=-2;s[8,6,6]=2
        v,p=project(np.zeros((3,*shape)),h,.01,s)
        np.testing.assert_allclose(divergence(v,h),s,atol=1e-12)
        with self.assertRaises(ValueError):project(v,h,.01,s+1)

    def test_viscous_stress_dissipates_energy_and_conserves_momentum(self):
        rng=np.random.default_rng(4);shape=(12,10,8);h=np.array([1/n for n in shape]);u,_=project(rng.normal(size=(3,*shape)),h,.01)
        nu=strain_viscosity(u,h,.001,.12);f=viscous_force(u,h,nu)
        self.assertGreater(nu.max(),.001)
        self.assertLess(np.sum(u*f),0)
        np.testing.assert_allclose(f.sum(axis=(1,2,3)),0,atol=1e-10)

    def test_taylor_green_velocity_converges_under_grid_refinement(self):
        errors=[]
        for n in [12,24]:
            cfg=Config(shape=(n,n,4),lengths=(2*np.pi,2*np.pi,1),nu=.05,cs=0,buoyancy=0,loading=0,diffusivity=.01,thermal_diffusivity=.01,cooling=0,max_dt=.01)
            s=Smoke(cfg);x=s.face_coordinates();s.u[0]=np.sin(x[0][0])*np.cos(x[0][1]);s.u[1]=-np.cos(x[1][0])*np.sin(x[1][1]);initial=s.u.copy();s.advance(.2)
            exact=initial*np.exp(-2*cfg.nu*.2);errors.append(np.sqrt(np.mean((s.u-exact)**2)))
        self.assertLess(errors[1],errors[0]/3)

    def test_species_diffusion_is_positive_conservative_and_convergent(self):
        errors=[]
        for n in [12,24]:
            cfg=Config(shape=(n,6,4),lengths=(2*np.pi,1,1),nu=.01,cs=0,buoyancy=0,loading=0,diffusivity=.02,thermal_diffusivity=.01,cooling=0,max_dt=.01)
            s=Smoke(cfg);x=s.centres[0];s.c[0]=1+.4*np.cos(2*x);initial=s.mass().copy();s.advance(.2)
            expected=1+.4*np.cos(2*x)*np.exp(-4*cfg.diffusivity*.2);errors.append(np.sqrt(np.mean((s.c[0]-expected)**2)));np.testing.assert_allclose(s.mass(),initial,atol=1e-11);self.assertGreaterEqual(s.c.min(),-1e-13)
        self.assertLess(errors[1],errors[0]/3)

    def test_capture_keeps_all_species_mass_in_gas_or_deposit(self):
        cfg=Config(shape=(12,10,8),lengths=(1.6,1,.4),max_dt=.01,collector_start=.2,collector_flux=.025)
        s=Smoke.plumes(cfg,seed=12);initial=s.mass().copy();s.advance(1)
        np.testing.assert_allclose(s.mass()+s.deposited,initial,rtol=1e-11,atol=1e-12)
        self.assertGreater(s.deposited.sum(),0);self.assertGreater(s.mass().sum(),0);self.assertGreaterEqual(s.c.min(),-1e-11)
        self.assertLess(s.last['divergenceResidualMax'],1e-10)

    def test_snapshot_replay_preserves_complete_fluid_state(self):
        cfg=Config(shape=(10,8,6),collector_start=.1,collector_flux=.02,max_dt=.01)
        a=Smoke.plumes(cfg,seed=5);a.advance(.2);b=Smoke.from_snapshot(a.snapshot());a.advance(.2);b.advance(.2)
        for key in ['u','c','temperature','pressure','deposited']:np.testing.assert_array_equal(getattr(a,key),getattr(b,key))
        self.assertEqual(a.time,b.time)
        fresh=Smoke.plumes(cfg,seed=6);self.assertFalse(np.array_equal(fresh.u,Smoke.plumes(cfg,seed=5).u))

    def test_marker_drag_has_correct_response_and_periodic_motion(self):
        shape=(8,8,8);h=np.array([1/n for n in shape]);u=np.zeros((3,*shape));u[0]=.5;x=np.array([[.1,.3,.5]]);v=np.zeros_like(x);dt=.1;tau=.02
        nx,nv=advect_markers(x,v,u,h,dt,tau)
        np.testing.assert_allclose(nv[0,0],.5*(1-np.exp(-dt/tau)),atol=1e-14)
        np.testing.assert_allclose(nx[0,0],.1+.5*dt-.5*tau*(1-np.exp(-dt/tau)),atol=1e-14)

    def test_collector_masks_are_explicit_validated_and_detached(self):
        cfg=Config(shape=(8,8,8),collector_start=0,collector_flux=.02)
        s=Smoke(cfg)
        with self.assertRaises(ValueError):s.advance(.05)
        good=np.ones(s.shape);s.set_collector(good,good);good[:]=0
        self.assertGreater(s.collector_mask.sum(),0)
        for bad in [np.zeros(s.shape),np.ones((4,4,4)),np.full(s.shape,-1),np.full(s.shape,np.nan)]:
            with self.assertRaises(ValueError):s.set_collector(bad,np.ones(s.shape))
        for dt in [-1,0,np.nan,1]:
            with self.assertRaises(ValueError):s.step(dt)

    def test_port_ramp_temporal_refinement_and_stage_constraints(self):
        errors=[]
        for dt in [.125,.0625,.03125]:
            cfg=Config(shape=(8,6,4),lengths=(1,1,1),nu=.001,cs=0,buoyancy=0,loading=0,diffusivity=0,thermal_diffusivity=0,cooling=0,max_dt=dt,collector_start=0,collector_flux=.02)
            s=Smoke(cfg);s.c[0]=1;s.set_collector(np.ones(s.shape),np.ones(s.shape));s.advance_to(.5)
            errors.append(abs(s.c[0].mean()-np.exp(-.02*.25)))
            self.assertLess(s.last['stageDivergenceResidualMax'],1e-11)
        self.assertLess(errors[1],errors[0]/6)
        self.assertLess(errors[2],errors[1]/6)

    def test_fixed_physics_ticks_are_independent_of_observation_cadence(self):
        cfg=Config(shape=(10,8,6),collector_start=.1,collector_flux=.02)
        worlds=[Smoke.plumes(cfg,seed=15) for _ in range(3)]
        worlds[0].advance(.3)
        for _ in range(30):worlds[1].advance(.01)
        for _ in range(10):worlds[2].advance(.013);worlds[2].advance(.017)
        for s in worlds[1:]:
            for name in ['u','c','temperature','pressure','deposited']:np.testing.assert_array_equal(getattr(worlds[0],name),getattr(s,name))
            self.assertEqual(s.steps,worlds[0].steps);self.assertEqual(s.ticks,18);self.assertEqual(s.observation_ns,300000000)

    def test_grid_scale_checkerboard_shear_is_not_invisible_to_sgs(self):
        shape=(8,8,8);h=np.full(3,1/8);u=np.zeros((3,*shape));u[0]=np.broadcast_to(((-1.)**np.arange(8))[None,:,None],shape)
        self.assertEqual(np.max(np.abs(divergence(u,h))),0)
        eddy=strain_viscosity(u,h,0,.12)
        self.assertGreater(eddy.min(),.003)
        self.assertLess(np.sum(u*viscous_force(u,h,eddy)),0)

    def test_tracer_handoff_velocity_is_terminal_not_midpoint(self):
        shape=(8,8,8);h=np.full(3,1/8);u=np.zeros((3,*shape));u[0]=.2;u[1]=np.broadcast_to(((np.arange(8)+.5)/8)[:,None,None],shape)
        x=np.array([[.2,.3,.4]]);nx,nv=advect_markers(x,np.array([[.2,.2,0]]),u,h,.1)
        np.testing.assert_allclose(nx,[ [.22,.321,.4] ],atol=1e-14)
        np.testing.assert_allclose(nv,[ [.2,.22,0] ],atol=1e-14)

    def test_anisotropic_strong_port_stages_and_rejected_step_rollback(self):
        cfg=Config(shape=(8,8,8),lengths=(2,.5,.25),nu=.0005,diffusivity=.001,max_dt=1/30,collector_start=.05,collector_flux=.1)
        s=Smoke.plumes(cfg,seed=8);s.c[:]=0;s.c[0,2:4,2:4,2:4]=1;initial=s.mass().copy();s.advance_to(.25)
        np.testing.assert_allclose(s.mass()+s.deposited,initial,rtol=1e-11,atol=1e-12)
        self.assertGreaterEqual(s.last['stageMinimum'],-1e-11);self.assertLessEqual(s.last['stageTransportCourant'],cfg.cfl*(1+1e-10));self.assertLess(s.last['stageDivergenceResidualMax'],1e-10)
        s.u[0]=100;before=s.snapshot()
        with self.assertRaises(FloatingPointError):s.step(cfg.max_dt)
        for name in ['u','c','temperature','pressure','deposited']:np.testing.assert_array_equal(getattr(s,name),before[name])
        self.assertEqual(s.time,before['time']);self.assertEqual(s.steps,before['steps'])

    def test_invalid_units_and_transport_coefficients_reject(self):
        for options in [dict(nu=np.nan),dict(lengths=(1,-1,1)),dict(lengths=(1,1)),dict(max_dt=0),dict(shape=(8,8,3)),dict(cfl=1),dict(prandtl=0),dict(cs=-1)]:
            with self.assertRaises(ValueError):Smoke(Config(**options))

    def test_moving_collector_keeps_pressure_constraints_mass_and_replay(self):
        cfg=Config(shape=(8,8,8),collector_start=0,collector_flux=.05)
        s=Smoke.plumes(cfg,seed=4);s.advance_to(.6);initial=s.mass()+s.deposited
        old=s.boundary(s.time)
        with self.assertRaises(ValueError):s.set_collector(np.ones(s.shape),np.ones(s.shape))
        collector=np.roll(s.collector_mask,2,axis=0);supply=s.supply_mask.copy();s.transition_collector(collector,supply,.5)
        np.testing.assert_array_equal(s.boundary(s.time)['lift'],old['lift'])
        early=s.boundary(s.time+1e-5)
        self.assertLess(np.max(np.abs(early['lift']-old['lift'])),1e-12)
        s.advance_to(.85);clone=Smoke.from_snapshot(s.snapshot());s.advance_to(1.2);clone.advance_to(1.2)
        for name in ['u','c','temperature','pressure','deposited']:np.testing.assert_array_equal(getattr(s,name),getattr(clone,name))
        np.testing.assert_allclose(s.mass()+s.deposited,initial,atol=1e-12)
        self.assertLess(s.last['stageDivergenceResidualMax'],1e-10)
        self.assertLessEqual(s.last['finalTransportCourant'],cfg.cfl*(1+1e-10))

if __name__=='__main__':unittest.main()
