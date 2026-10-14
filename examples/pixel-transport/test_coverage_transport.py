import unittest
import numpy as np
from coverage_transport import plan_coverage_pair,event_states

class CoverageEventTests(unittest.TestCase):
    def test_new_shape_has_zero_initial_and_full_final_extent(self):
        a=np.zeros((50,70));b=a.copy();b[10:25,30:40]=.7
        plan=plan_coverage_pair(a,b)
        self.assertEqual(len(plan['mapping']['unmatched_target']),1)
        self.assertEqual(event_states(plan,0)[0]['scale'],0)
        self.assertEqual(event_states(plan,1)[0]['scale'],1)
        self.assertAlmostEqual(event_states(plan,.5)[0]['scale'],.5)
    def test_removed_shape_contracts_and_retained_part_moves(self):
        a=np.zeros((80,160));a[10:30,10:25]=1;a[50:65,80:115]=1
        b=np.zeros_like(a);b[50:70,135:150]=1
        plan=plan_coverage_pair(a,b)
        self.assertEqual(len(plan['mapping']['matches']),1)
        self.assertEqual(len(plan['mapping']['unmatched_source']),1)
        self.assertEqual(len(plan['mapping']['unmatched_target']),0)
        end=event_states(plan,1)
        self.assertEqual(next(e for e in end if e['kind']=='death')['scale'],0)
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
        f=lambda t:event_states(plan,t)[0]['scale']
        self.assertLess(abs((f(h)-f(0))/h),1e-6)
        self.assertLess(abs((f(1)-f(1-h))/h),1e-6)
        self.assertLess(abs((f(2*h)-2*f(h)+f(0))/h**2),.01)
        self.assertLess(abs((f(1)-2*f(1-h)+f(1-2*h))/h**2),.01)
    def test_invalid_coverage_and_time_rejected(self):
        a=np.zeros((30,30));b=a.copy();b[10:20,10:20]=1
        with self.assertRaises(ValueError):plan_coverage_pair(a-1,b)
        with self.assertRaises(ValueError):event_states(plan_coverage_pair(a,b),1.1)

if __name__=='__main__':unittest.main()
