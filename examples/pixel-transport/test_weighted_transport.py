import unittest
import numpy as np
from scipy import ndimage as ndi
from weighted_transport import calibrate,rounded_connect,rank,configure,Configuration,sequence_cost
from lineage_transport import distance_field,make_plan,patch_at

class WeightSweepTests(unittest.TestCase):
    def test_contour_offset_reaches_requested_area_without_fading_interiors(self):
        y,x=np.mgrid[:70,:90];alpha=(((x-45)/20)**2+((y-35)/15)**2<1).astype(float)
        result=calibrate(distance_field(alpha),alpha.sum()*1.13)
        self.assertAlmostEqual(result.sum(),alpha.sum()*1.13,places=4)
        self.assertEqual(result[35,45],1)
        self.assertEqual(result[0,0],0)
    def test_rounded_join_has_finite_width_not_a_one_pixel_strand(self):
        y,x=np.mgrid[:60,:90]
        alpha=(((x-25)**2+(y-30)**2<12**2)|((x-65)**2+(y-30)**2<12**2)).astype(float)
        result,_=rounded_connect(alpha,4.)
        self.assertEqual(ndi.label(result>.5)[1],1)
        self.assertGreaterEqual(np.count_nonzero(result[:,45]>.5),7)
    def test_rigid_match_is_unchanged_by_style_weights(self):
        a=np.zeros((120,160));b=a.copy();a[35:55,30:60]=1;b[65:85,90:120]=1
        plan=make_plan(a,b,1);node=plan['roots'][0]
        configure(plan,Configuration(.2,1,.2,8))
        for t in [.1,.5,.9]:np.testing.assert_array_equal(plan['surface'](node,t)[0],patch_at(node,t)[0])
    def test_ranking_uses_one_configuration_across_all_cases(self):
        keys=['area','reversal','vibration','thin','perimeter','transport','event','topology','boundary']
        rows=[dict(candidate=c,case=case,costs=dict.fromkeys(keys,value)) for c,values in [(0,[1.,9.]),(1,[3.,3.])] for case,value in zip(['a','b'],values)]
        ranking=rank(rows)
        for entries in ranking['rankings'].values():self.assertEqual(entries[0]['candidate'],1)
    def test_area_reversal_cost_distinguishes_swelling_from_constant_area(self):
        def costs(widths):
            images=[];metrics=[]
            for w in widths:
                im=np.zeros((40,40),np.uint8);im[15:25,10:10+w]=255;images.append(im)
                metrics.append(dict(ids=[0],centers=[[20.,20.]]))
            return sequence_cost(images,metrics,100,100,[],1)[0]
        constant=costs([10]*5);swelling=costs([10,12,15,12,10])
        self.assertEqual(constant['reversal'],0)
        self.assertGreater(swelling['reversal'],.9)
        self.assertGreater(swelling['vibration'],constant['vibration'])

    def test_transient_hole_is_penalized_even_when_object_count_is_constant(self):
        full=np.zeros((30,30),np.uint8);full[5:25,5:25]=255
        hole=full.copy();hole[12:18,12:18]=0
        metrics=[dict(ids=[0],centers=[[15.,15.]])]*3
        costs,details=sequence_cost([full,hole,full],metrics,400,400,[],1)
        self.assertEqual(details['holes'],[0,1,0])
        self.assertEqual(costs['topology'],2)

    def test_weighted_surface_keeps_split_count_and_exact_endpoints(self):
        from lineage_transport import frame
        y,x=np.mgrid[:160,:240]
        a=(((x-120)**2+(y-80)**2)<18**2).astype(float)
        b=(((x-65)**2+(y-80)**2<10**2)|((x-175)**2+(y-80)**2<10**2)).astype(float)
        plan=make_plan(a,b,1);configure(plan,Configuration(.14,1,.18,12))
        counts=[];images=[];state={}
        for t in np.linspace(0,1,41):
            image,metric=frame(plan,float(t),state,size=(240,160),offset=np.zeros(2))
            counts.append(metric['count']);images.append(image)
        self.assertEqual(set(counts),{1,2})
        self.assertTrue(np.all(np.diff(counts)>=0))
        np.testing.assert_array_equal(images[0],a)
        np.testing.assert_array_equal(images[-1],b)

    def test_sparse_topology_penalty_has_finite_useful_normalization(self):
        from weighted_transport import WEIGHTS
        keys=list(next(iter(WEIGHTS.values())))
        rows=[dict(candidate=c,case=str(c),costs=dict.fromkeys(keys,0.)) for c in range(5)]
        rows[-1]['costs']['topology']=2.
        result=rank(rows)
        self.assertEqual(result['normalization']['topology'],2.)
        self.assertLess(result['rankings']['B-balanced'][-1]['score'],1.)

if __name__=='__main__':unittest.main()
