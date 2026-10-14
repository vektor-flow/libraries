import unittest
import numpy as np
from lineage_transport import make_plan,desired_center,center,frame
from join_transport import configure

class JoinTimingTests(unittest.TestCase):
    def test_area_regularizer_is_bounded_monotone_and_below_linear(self):
        from types import SimpleNamespace
        from regularized_transport import area_target
        for a,b in [(20,80),(80,20),(40,40)]:
            node=SimpleNamespace(part=SimpleNamespace(patch=np.ones(a)),final=SimpleNamespace(patch=np.ones(b)),area_power=1.5)
            times=np.linspace(0,1,101);areas=np.array([area_target(node,t) for t in times])
            self.assertEqual(areas[0],a);self.assertEqual(areas[-1],b)
            self.assertTrue(np.all(areas>=min(a,b)-1e-10));self.assertTrue(np.all(areas<=max(a,b)+1e-10))
            self.assertTrue(np.all(areas<=a+(b-a)*times+1e-10))
            self.assertTrue(np.all(np.diff(areas)*(1 if b>=a else -1)>=-1e-10))
    def test_edge_sharing_cannot_hide_opaque_overlap(self):
        from lineage_transport import compatible_edge_coverage
        def layer(a):return dict(origin=np.array([0,0]),alpha=np.array([[a]]))
        self.assertTrue(compatible_edge_coverage(layer(.4),layer(.4)))
        self.assertTrue(compatible_edge_coverage(layer(.7),layer(.3)))
        self.assertFalse(compatible_edge_coverage(layer(.7),layer(.4)))
        self.assertFalse(compatible_edge_coverage(layer(.6),layer(.6)))
    def fixture(self):
        y,x=np.mgrid[:180,:300]
        a=np.zeros((180,300));a[60:120,45:65]=1
        b=(((x-160)**2+(y-65)**2<15**2)|((x-210)**2+(y-120)**2<18**2)).astype(float)
        plan=make_plan(a,b,1);configure(plan)
        return a,b,plan
    def test_branch_positions_have_exact_endpoints_and_smooth_birth(self):
        _,_,plan=self.fixture();child=plan['roots'][0].children[0];fn=plan['desired_center']
        np.testing.assert_allclose(fn(child,child.birth,1),desired_center(child,child.birth,1))
        np.testing.assert_allclose(fn(child,1,1),child.goal)
        def residual(t):return fn(child,t,1)-fn(child.parent,t,1)-(center(child.part,1)-center(child.parent.part,1))
        self.assertLess(np.linalg.norm(residual(child.birth+1e-4)),1e-9)
    def test_morph_progress_precedes_branch_departure(self):
        from pixel_transport import clock
        _,_,plan=self.fixture();child=plan['roots'][0].children[0];t=(1+child.birth)/2
        parent=plan['desired_center'](child.parent,t,1)
        start=center(child.part,1)-center(child.parent.part,1);end=child.goal-child.parent.goal
        expected=parent+.75*start+.25*end
        np.testing.assert_allclose(plan['desired_center'](child,t,1),expected)
        self.assertEqual(clock(.5),.5)
    def test_sampled_split_is_monotone_and_exact(self):
        a,b,plan=self.fixture();state={};counts=[];offsets=[]
        for t in np.linspace(0,1,101):
            im,row=frame(plan,float(t),state,size=(300,180),offset=np.zeros(2));counts.append(row['count']);offsets.append(row['max_offset'])
            if t==0:np.testing.assert_array_equal(im,a)
            if t==1:np.testing.assert_array_equal(im,b)
        self.assertTrue(np.all(np.diff(counts)>=0));self.assertEqual(counts[0],1);self.assertEqual(counts[-1],2)
        self.assertEqual(max(offsets),0.,'Sibling release inserted a collision gap')

if __name__=='__main__':unittest.main()
