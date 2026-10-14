import unittest
import numpy as np
from lineage_transport import frame
from coalescing_transport import make_plan,CoalescingPatch

class CoalescingTests(unittest.TestCase):
    def fixture(self):
        y,x=np.mgrid[:180,:300]
        a=(((x-70)**2+(y-75)**2<16**2)|((x-140)**2+(y-110)**2<18**2)).astype(float)
        b=np.zeros_like(a);b[60:120,205:215]=1;b[110:120,205:245]=1
        return a,b,make_plan(a,b,1)
    def test_merges_before_reforming_and_preserves_endpoints(self):
        a,b,plan=self.fixture();state={};counts=[];offset=np.zeros(2);images=[]
        for t in np.linspace(0,1,121):
            im,row=frame(plan,float(t),state,size=(300,180),offset=offset);images.append(im);counts.append(row['count'])
        np.testing.assert_array_equal(images[0],a);np.testing.assert_array_equal(images[-1],b)
        self.assertTrue(np.all(np.diff(counts)<=0));self.assertEqual(set(counts),{1,2})
        self.assertLess(next(k for k,n in enumerate(counts) if n==1),60)
        node=plan['roots'][0]
        early=CoalescingPatch(node,node.contact_time+.04).field_on_grid()
        late=CoalescingPatch(node,.85).field_on_grid()
        self.assertGreater(abs(np.clip(early+.5,0,1)-np.clip(late+.5,0,1)).sum(),100)
    def test_equal_count_morph_preserves_direction_and_endpoints(self):
        y,x=np.mgrid[:180,:300]
        a=(((x-70)**2+(y-75)**2)<16**2).astype(float)
        b=np.zeros_like(a);b[60:120,205:225]=1
        plan=make_plan(a,b,1);state={};images=[]
        for t in np.linspace(0,1,61):
            im,row=frame(plan,float(t),state,size=(300,180),offset=np.zeros(2))
            self.assertEqual(row['count'],1);images.append(im)
        np.testing.assert_array_equal(images[0],a)
        np.testing.assert_array_equal(images[-1],b)

    def test_contact_surface_has_no_finite_handoff_jump(self):
        _,_,p=self.fixture();n=p['roots'][0];t=n.contact_time
        def delta(eps):
            a=CoalescingPatch(n,t-eps).field_on_grid();b=CoalescingPatch(n,t+eps).field_on_grid()
            return abs(np.clip(a+.5,0,1)-np.clip(b+.5,0,1)).sum()
        self.assertLess(delta(1e-5),.02*delta(1e-3))
    def test_no_precontact_target_shaping(self):
        _,_,p=self.fixture();n=p['roots'][0];t=n.contact_time*.7
        before=CoalescingPatch(n,t).field_on_grid().copy();n.target_field[:]=100
        np.testing.assert_array_equal(CoalescingPatch(n,t).field_on_grid(),before)

if __name__=='__main__':unittest.main()
