import unittest
import numpy as np
from coverage_transport import plan_coverage_pair,event_states

class CoverageEventTests(unittest.TestCase):
    def test_new_shape_has_zero_initial_and_full_final_extent(self):
        a=np.zeros((50,70));b=a.copy();b[10:25,30:40]=.7
        plan=plan_coverage_pair(a,b)
        self.assertEqual(len(plan['mapping']['unmatched_target']),1)
        self.assertEqual(event_states(plan,0)[0]['opacity'],0)
        self.assertEqual(event_states(plan,1)[0]['scale'],1)
        self.assertAlmostEqual(event_states(plan,.5)[0]['opacity'],.5)
    def test_removed_shape_contracts_and_retained_part_moves(self):
        a=np.zeros((80,160));a[10:30,10:25]=1;a[50:65,80:115]=1
        b=np.zeros_like(a);b[50:70,135:150]=1
        plan=plan_coverage_pair(a,b)
        self.assertEqual(len(plan['mapping']['matches']),1)
        self.assertEqual(len(plan['mapping']['unmatched_source']),1)
        self.assertEqual(len(plan['mapping']['unmatched_target']),0)
        end=event_states(plan,1)
        self.assertEqual(next(e for e in end if e['kind']=='death')['opacity'],0)
        retained=next(e for e in end if e['kind']=='matched')
        np.testing.assert_allclose(retained['center'],[142,59.5])
    def test_coverage_is_preserved_instead_of_binary_thresholding(self):
        a=np.zeros((30,30));a[10:20,10:20]=.25
        plan=plan_coverage_pair(a,a)
        self.assertEqual(plan['source'][0].region.mass,25)
        np.testing.assert_array_equal(plan['source'][0].patch,np.full((10,10),.25))
    def test_endpoint_birth_and_death_rates_settle(self):
        a=np.zeros((30,30));b=a.copy();b[10:20,10:20]=1
        plan=plan_coverage_pair(a,b);h=1e-4
        f=lambda t:event_states(plan,t)[0]['opacity']
        self.assertLess(abs((f(h)-f(0))/h),1e-6)
        self.assertLess(abs((f(1)-f(1-h))/h),1e-6)
        self.assertLess(abs((f(2*h)-2*f(h)+f(0))/h**2),.01)
        self.assertLess(abs((f(1)-2*f(1-h)+f(1-2*h))/h**2),.01)
    def test_invalid_coverage_and_time_rejected(self):
        a=np.zeros((30,30));b=a.copy();b[10:20,10:20]=1
        with self.assertRaises(ValueError):plan_coverage_pair(a-1,b)
        with self.assertRaises(ValueError):event_states(plan_coverage_pair(a,b),1.1)

class BuddingTests(unittest.TestCase):
    def test_duplicate_buds_from_an_inferred_existing_part(self):
        a=np.zeros((80,160));a[20:40,20:35]=1
        b=a.copy();b[20:40,100:115]=1
        plan=plan_coverage_pair(a,b)
        j=plan['mapping']['unmatched_target'][0]
        self.assertEqual(plan['birth_parents'][j],0)
        start=next(e for e in event_states(plan,0) if e['kind']=='birth')
        middle=next(e for e in event_states(plan,.5) if e['kind']=='birth')
        end=next(e for e in event_states(plan,1) if e['kind']=='birth')
        np.testing.assert_allclose(start['center'],plan['source'][0].region.center)
        np.testing.assert_allclose(end['center'],plan['target'][j].region.center)
        self.assertEqual(start['opacity'],0);self.assertEqual(end['opacity'],1)
        self.assertLess(start['scale'],middle['scale']);self.assertLess(middle['scale'],end['scale'])
        self.assertFalse(np.allclose(start['center'],middle['center']))
    def test_disappearing_part_moves_into_a_retained_part_while_fading(self):
        a=np.zeros((80,160));a[20:40,20:35]=1;a[20:40,100:115]=1
        b=np.zeros_like(a);b[20:40,30:45]=1
        plan=plan_coverage_pair(a,b);i=plan['mapping']['unmatched_source'][0]
        self.assertEqual(plan['death_parents'][i],0)
        middle=next(e for e in event_states(plan,.5) if e['kind']=='death')
        end=next(e for e in event_states(plan,1) if e['kind']=='death')
        self.assertEqual(middle['opacity'],.5);self.assertAlmostEqual(middle['scale'],.725)
        self.assertFalse(np.allclose(middle['center'],plan['source'][i].region.center))
        np.testing.assert_allclose(end['center'],plan['target'][0].region.center)
        self.assertEqual(end['opacity'],0)
    def test_family_contact_is_distinct_from_unrelated_overlap(self):
        from coverage_transport import related_events
        a={'key':('m',0),'parent':None};b={'key':('b',1),'parent':('m',0)};c={'key':('m',2),'parent':None}
        self.assertTrue(related_events(a,b));self.assertFalse(related_events(b,c))

if __name__=='__main__':unittest.main()
