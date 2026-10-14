import unittest
import numpy as np
from scipy import ndimage as ndi
from lineage_transport import make_plan,frame
from continuous_transport import configure,presentation_alpha

class ContinuousTransportTests(unittest.TestCase):
    def fixture(self):
        y,x=np.mgrid[:160,:260]
        a=np.zeros((160,260));a[65:95,70:110]=1
        b=(((x-130)**2+(y-80)**2<12**2)|((x-200)**2+(y-80)**2<12**2)).astype(float)
        plan=make_plan(a,b,1);configure(plan,.5)
        return a,b,plan
    def test_split_handoff_has_no_finite_jump_as_time_interval_shrinks(self):
        a,b,plan=self.fixture();t=plan['events'][0]
        def difference(eps):
            left,_=frame(plan,t-eps,{},size=(260,160),offset=np.zeros(2))
            right,_=frame(plan,t+eps,{},size=(260,160),offset=np.zeros(2))
            return np.abs(left-right).sum()/a.sum()
        coarse=difference(.001);fine=difference(.0001)
        self.assertLess(fine,coarse*.15)
        self.assertLess(difference(.000001),.0001)
    def test_smaller_intervals_contract_mid_morph_changes(self):
        a,b,plan=self.fixture()
        for t in [.65,.75,.85,.95]:
            left,_=frame(plan,t-.000001,{},size=(260,160),offset=np.zeros(2))
            right,_=frame(plan,t+.000001,{},size=(260,160),offset=np.zeros(2))
            self.assertLess(np.abs(left-right).sum()/a.sum(),.001)
    def test_attached_parts_separate_once_with_exact_endpoints(self):
        a,b,plan=self.fixture();state={};counts=[];images=[]
        for t in np.linspace(0,1,81):
            image,metric=frame(plan,float(t),state,size=(260,160),offset=np.zeros(2))
            counts.append(metric['count']);images.append(image)
        self.assertEqual(set(counts),{1,2});self.assertTrue(np.all(np.diff(counts)>=0))
        np.testing.assert_array_equal(images[0],a);np.testing.assert_array_equal(images[-1],b)
    def test_display_transfer_has_no_half_coverage_step(self):
        alpha=np.linspace(0,1,10001);result=presentation_alpha(alpha)
        self.assertTrue(np.all(np.diff(result)>0))
        np.testing.assert_array_equal(result>.5,alpha>.5)
        self.assertEqual(result[0],0);self.assertEqual(result[-1],1)
        self.assertLess(presentation_alpha(.500001)-presentation_alpha(.499999),.0001)

    def test_subframe_tracks_are_continuous_and_reproduce_rendered_samples(self):
        from lineage_transport import smooth_tracks
        a,b,plan=self.fixture();metrics=[];state={}
        for t in np.linspace(0,1,81):
            _,metric=frame(plan,float(t),state,size=(260,160),offset=np.zeros(2));metrics.append(metric)
        smooth_tracks(plan,metrics,4)
        times=np.linspace(0,1,81)
        for i,curve in plan['track_splines'].items():
            np.testing.assert_allclose(curve(times),plan['tracks'][i],atol=1e-12)
            self.assertLess(np.linalg.norm(curve(.500001)-curve(.499999)),.01)
            np.testing.assert_allclose(curve(0,1),0,atol=1e-9)
            np.testing.assert_allclose(curve(1,1),0,atol=1e-9)

    def test_contact_anticipation_starts_avoidance_before_the_peak(self):
        from lineage_transport import smooth_tracks,desired_center
        _,_,plan=self.fixture();root=plan['roots'][0];rows=[]
        for k,t in enumerate(np.linspace(0,1,101)):
            base=desired_center(root,float(t),1)+np.array([-800.,-450.])
            rows.append(dict(ids=[root.id],centers=[(base+[0,10 if 48<=k<=52 else 0]).tolist()]))
        smooth_tracks(plan,rows,3);ordinary=plan['tracks'][root.id].copy()
        plan['anticipate_contacts']=True;smooth_tracks(plan,rows,3);anticipated=plan['tracks'][root.id]
        self.assertGreater(anticipated[42,1],ordinary[42,1])
        self.assertGreater(anticipated[50,1],ordinary[50,1])
        self.assertLessEqual(anticipated[:,1].max(),10.000001)

if __name__=='__main__':unittest.main()
