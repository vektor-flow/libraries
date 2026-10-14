import unittest
import numpy as np
from coverage_transport import plan_coverage_pair,event_states,material_particles,splat_material
from pixel_transport import Region,rigid_fit,rotation,clock

class MaterialTransportTests(unittest.TestCase):
    def endpoints(self):
        a=np.zeros((80,140));b=a.copy()
        a[25:45,10:30]=.8
        b[15:25,95:107]=.6;b[45:55,108:120]=.9
        return a,b
    def test_one_to_many_reuses_material_instead_of_birth_and_death(self):
        a,b=self.endpoints();p=plan_coverage_pair(a,b)
        self.assertIsNotNone(p['material'])
        self.assertEqual([e['kind'] for e in event_states(p,.5)],['morph'])
        self.assertEqual(len(p['mapping']['unmatched_source']),1)
        self.assertEqual(len(p['mapping']['unmatched_target']),2)
    def test_exact_antialiased_endpoints(self):
        a,b=self.endpoints();p=plan_coverage_pair(a,b)
        for t,want in [(0,a),(1,b)]:
            got=splat_material(p['material'],t,(140,80),1,np.zeros(2))
            np.testing.assert_allclose(got,want,atol=1e-12)
    def test_reused_material_travels_and_total_mass_interpolates(self):
        a,b=self.endpoints();p=plan_coverage_pair(a,b);m=p['material']
        for t in np.linspace(0,1,17):
            groups=material_particles(m,t)
            mass=sum(w.sum() for _,w in groups)
            self.assertAlmostEqual(mass,(1-clock(t))*a.sum()+clock(t)*b.sum())
        groups=material_particles(m,.5)
        center=sum((x*w[:,None]).sum(axis=0) for x,w in groups)/sum(w.sum() for _,w in groups)
        self.assertGreater(center[0],40);self.assertLess(center[0],90)
        # There is material in transit, rather than two stationary fading shapes.
        raster=splat_material(m,.5,(140,80),1,np.zeros(2))
        self.assertGreater(raster[:,35:90].sum(),50)
    def test_many_to_one_reuses_material_too(self):
        a,b=self.endpoints();p=plan_coverage_pair(b,a)
        self.assertEqual([e['kind'] for e in event_states(p,.5)],['morph'])
    def test_material_motion_settles_at_both_ends(self):
        a,b=self.endpoints();m=plan_coverage_pair(a,b)['material'];h=1e-5
        # Track a source particle through the full interval, including its limit.
        f=lambda t:m['source_points'][0]+clock(t)*m['source_displacement'][0]
        for t,sign in [(0,1),(1,-1)]:
            self.assertLess(np.linalg.norm((f(t+sign*h)-f(t))/h),1e-5)
            self.assertLess(np.linalg.norm((f(t+2*sign*h)-2*f(t+sign*h)+f(t))/h**2),.1)
    def test_equal_mass_stays_conserved_before_raster_saturation(self):
        a,b=self.endpoints();a*=b.sum()/a.sum()
        material=plan_coverage_pair(a,b)['material']
        for t in np.linspace(0,1,21):
            self.assertAlmostEqual(sum(w.sum() for _,w in material_particles(material,t)),a.sum())
    def test_unchanged_geometry_keeps_independent_rigid_motion(self):
        a,b=self.endpoints();a[10:40,60:63]=1;b[10:40,65:68]=1
        p=plan_coverage_pair(a,b)
        events=event_states(p,.5,0,0)
        self.assertEqual([e['kind'] for e in events],['matched','morph'])
        retained=events[0]
        self.assertEqual(retained['source_angle'],0)
        self.assertEqual(retained['scale'],1)
        np.testing.assert_allclose(retained['center'],[63.5,24.5])
    def test_rotation_requires_geometric_evidence(self):
        rng=np.random.default_rng(42)
        p=rng.uniform([-15,-4],[15,4],size=(500,2));p-=p.mean(axis=0)
        a=Region(p,np.zeros(2),len(p))
        # A tiny raster perturbation must not introduce a tiny rotation.
        b=Region(p@rotation(.003).T,np.array([50.,20.]),len(p))
        angle,_=rigid_fit(a,b);self.assertEqual(angle,0)
        c=Region(p@rotation(.7).T,np.array([50.,20.]),len(p))
        angle,error=rigid_fit(a,c)
        self.assertLess(abs(angle-.7),.01);self.assertLess(error,.1)

if __name__=='__main__':unittest.main()
