import unittest
import numpy as np
from scipy import ndimage as ndi
from coverage_transport import plan_coverage_pair,solid_material,splat_material
from pixel_transport import clock

class SolidTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        y,x=np.mgrid[:140,:200]
        cls.a=(((x-45)**2+(y-70)**2)<15**2).astype(float)
        cls.b=((((x-125)**2+(y-45)**2)<11**2)|(((x-125)**2+(y-95)**2)<11**2)).astype(float)
        cls.material=plan_coverage_pair(cls.a,cls.b)['material']
    def draw(self,t):return solid_material(self.material,t,(200,140),1,np.zeros(2))
    def test_split_stays_connected_then_pinches_into_two(self):
        self.assertEqual(len(self.material['necks']),1)
        for t in [.1,.15,.2]:self.assertEqual(ndi.label(self.draw(t)>.5)[1],1)
        for t in [.3,.4,.5,.7,.8,.9]:self.assertEqual(ndi.label(self.draw(t)>.5)[1],2)
    def test_separating_bodies_leave_a_clear_gap_instead_of_a_strand(self):
        for t in [.35,.45,.55]:
            image=self.draw(t)
            # The known split axis crosses the midpoint between the two bodies.
            self.assertLess(float(image[69:72,:].max()),.01)
    def test_forced_necks_cannot_span_distant_bodies(self):
        from coverage_transport import neck_profile
        neck=dict(start=np.array([[0.,0.],[40.,0.]]),end=np.array([[0.,0.],[80.,0.]]),radius=2.,reverse=False)
        for u in np.linspace(0,1,25):self.assertEqual(neck_profile(neck,u)[3],0)
    def test_release_settles_smoothly_without_a_binary_cut(self):
        from coverage_transport import neck_profile
        neck=dict(start=np.array([[0.,0.],[2.,0.]]),end=np.array([[0.,0.],[2.,0.]]),radius=2.,reverse=False)
        f=lambda u:neck_profile(neck,u)[3]
        h=1e-5;end=.32
        self.assertEqual(f(end),0)
        self.assertLess(abs((f(end)-f(end-h))/h),1e-6)
        self.assertLess(abs((f(end)-2*f(end-h)+f(end-2*h))/h**2),.03)
    def test_reverse_merge_forms_one_cohesive_body(self):
        material=plan_coverage_pair(self.b,self.a)['material']
        early=solid_material(material,.2,(200,140),1,np.zeros(2))
        late=solid_material(material,.8,(200,140),1,np.zeros(2))
        self.assertEqual(ndi.label(early>.5)[1],2)
        self.assertEqual(ndi.label(late>.5)[1],1)
    def test_surface_removes_grain_and_keeps_interior_opaque(self):
        for t in [.25,.5,.75]:
            raw=splat_material(self.material,t,(200,140),1,np.zeros(2));solid=self.draw(t)
            def opacity(a):return (a>.98).sum()/max((a>.02).sum(),1)
            self.assertGreater(opacity(solid),.8)
            self.assertGreater(opacity(solid),opacity(raw)+.15)
            interior=ndi.binary_erosion(solid>.5,iterations=2)
            self.assertTrue(np.all(solid[interior]>.98))
    def test_surface_area_tracks_smooth_target_without_inflation(self):
        for t in np.linspace(.12,.88,15):
            wanted=(1-clock(t))*self.a.sum()+clock(t)*self.b.sum()
            self.assertLess(abs(self.draw(t).sum()-wanted),.01)
    def test_original_antialiased_endpoints_are_unchanged(self):
        a=self.a*.7;b=self.b*.8;material=plan_coverage_pair(a,b)['material']
        for t,want in [(0,a),(1,b)]:
            np.testing.assert_allclose(solid_material(material,t,(200,140),1,np.zeros(2)),want,atol=1e-12)

if __name__=='__main__':unittest.main()
