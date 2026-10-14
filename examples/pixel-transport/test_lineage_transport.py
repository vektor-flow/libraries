import unittest
import numpy as np
from scipy import ndimage as ndi
from lineage_transport import make_plan,frame,bisect,active_nodes
from coverage_transport import coverage_parts

class LineageTests(unittest.TestCase):
    def endpoints(self,count=5):
        y,x=np.mgrid[:140,:220]
        a=(((x-100)**2+(y-70)**2)<18**2).astype(float)
        b=np.zeros_like(a)
        for cx in np.linspace(30,190,count):b[((x-cx)**2+(y-70)**2)<7**2]=1
        return a,b
    def sequence(self,a,b):
        plan=make_plan(a,b,1);state={};counts=[];images=[]
        for t in np.linspace(0,1,81):
            image,metric=frame(plan,float(t),state,size=(220,140),offset=np.zeros(2))
            self.assertEqual(ndi.label(image>.5)[1],metric['count'])
            counts.append(metric['count']);images.append(image)
        if plan['reverse']:counts.reverse();images.reverse()
        return plan,np.array(counts),images
    def test_one_to_five_has_no_extra_fragments_or_remerges(self):
        a,b=self.endpoints();plan,counts,images=self.sequence(a,b)
        self.assertEqual(counts[0],1);self.assertEqual(counts[-1],5)
        self.assertTrue(np.all(np.diff(counts)>=0))
        self.assertEqual(set(counts),{1,2,3,4,5})
        np.testing.assert_array_equal(images[0],a);np.testing.assert_array_equal(images[-1],b)
    def test_five_to_one_has_no_resplitting(self):
        a,b=self.endpoints();_,counts,_=self.sequence(b,a)
        self.assertEqual(counts[0],5);self.assertEqual(counts[-1],1)
        self.assertTrue(np.all(np.diff(counts)<=0))
    def test_one_split_prefers_middle_of_motion(self):
        a,b=self.endpoints(2);plan=make_plan(a,b,1)
        self.assertEqual(len(plan['events']),1)
        self.assertLess(abs(plan['events'][0]-.5),.08)
    def test_event_schedule_is_spread_and_parent_precedes_child(self):
        a,b=self.endpoints();plan=make_plan(a,b,1)
        self.assertTrue(np.all(np.diff(plan['events'])>.10))
        for node in plan['nodes']:
            if node.children:self.assertGreater(node.split,node.birth)
            for child in node.children:self.assertEqual(child.birth,node.split)
    def test_partition_keeps_material_and_connected_children(self):
        a,_=self.endpoints();part=coverage_parts(a)[0]
        children=bisect(part,np.array([1.,.3]),1)
        recovered=np.zeros_like(a)
        for child in children:
            self.assertEqual(ndi.label(child.patch>.5)[1],1)
            x,y=child.origin;h,w=child.patch.shape
            recovered[y:y+h,x:x+w]+=child.patch
        np.testing.assert_array_equal(recovered,a)
    def test_equal_counts_stay_constant_while_objects_swap(self):
        a=np.zeros((140,220));b=a.copy()
        a[55:75,35:50]=1;a[55:65,165:190]=1
        b[55:75,170:185]=1;b[55:65,30:55]=1
        _,counts,images=self.sequence(a,b)
        self.assertTrue(np.all(counts==2))
        np.testing.assert_array_equal(images[-1],b)
    def test_rigid_rotation_keeps_an_elongated_body_instead_of_morphing_to_a_square(self):
        from lineage_transport import patch_at
        a=np.zeros((140,220));b=a.copy();a[60:66,80:110]=1;b[50:80,90:96]=1
        plan=make_plan(a,b,1);root=plan['roots'][0]
        self.assertGreater(abs(root.rigid_angle),1)
        patch,_=patch_at(root,.5);y,x=np.nonzero(patch>.1)
        covariance=np.cov(np.column_stack((x,y)).T,aweights=patch[y,x])
        eigen=np.linalg.eigvalsh(covariance)
        self.assertGreater(eigen[-1]/eigen[0],10)
    def test_display_edge_guard_preserves_silhouette_and_eases_to_the_hold(self):
        from lineage_transport import presentation_alpha
        alpha=np.linspace(0,1,1001)
        for t in np.linspace(0,1,21):
            display=presentation_alpha(alpha,t)
            np.testing.assert_array_equal(display>.5,alpha>.5)
            self.assertEqual(display[0],0);self.assertEqual(display[-1],1)
        self.assertLess(np.max(np.abs(presentation_alpha(alpha,.999)-presentation_alpha(alpha,1))),1e-6)
    def test_blank_endpoint_is_not_silently_given_a_fake_lineage(self):
        a,b=self.endpoints()
        with self.assertRaises(ValueError):make_plan(np.zeros_like(a),b,1)

if __name__=='__main__':unittest.main()
