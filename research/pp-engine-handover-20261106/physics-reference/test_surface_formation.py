import unittest
import numpy as np
from surface_formation_reference import reconstruct

class SurfaceFormationTests(unittest.TestCase):
    def test_zero_mass_has_no_ink_despite_target_support(self):
        r=reconstruct(np.zeros((2,5)),[1,.25],.1,2)
        self.assertTrue(np.all(r.pma==0));self.assertTrue(np.all(r.coverage==0))
    def test_partial_fill_is_linear_in_captured_mass_and_support_bounded(self):
        mass=np.array([0,.02,.04,.06,.08,.1]);raw=np.column_stack((mass,.5*mass,.25*mass,mass,mass))
        r=reconstruct(raw,np.full(6,.5),.1,2)
        np.testing.assert_allclose(r.coverage,mass/.2,atol=1e-15)
        np.testing.assert_allclose(r.pma[:,0],mass/.2,atol=1e-15)
        self.assertTrue(np.all(r.coverage<=.5));self.assertTrue(np.all(r.excess_mass==0))
    def test_excess_remains_attached_thickness(self):
        raw=[[.6,.3,.15,.6,.6]];r=reconstruct(raw,[.5],.1,2)
        self.assertAlmostEqual(r.coverage[0],.5);self.assertAlmostEqual(r.layer_mass[0],.1)
        self.assertAlmostEqual(r.excess_mass[0],.5);self.assertAlmostEqual(r.thickness_factor[0],6)
        np.testing.assert_allclose(r.mass,r.layer_mass+r.excess_mass,atol=1e-15)
    def test_opacity_is_separate_from_geometric_coverage(self):
        r=reconstruct([[.2,.1,0,.2,.05]],[.5],.1,2)
        self.assertAlmostEqual(r.coverage[0],.5);self.assertAlmostEqual(r.authored_opacity[0],.25)
        np.testing.assert_allclose(r.pma[0],[.125,.0625,0,.125],atol=1e-15)
    def test_partition_invariance_uses_stock_moments_not_arrival_order(self):
        records=np.array([[.12,.03,.06,.15,.15],[.03,.06,.015,.075,.0375],[.05,.025,0,.05,.05]])
        direct=reconstruct(records.sum(axis=0)[None,:],[.75],.2,3)
        grouped=reconstruct((records[:2].sum(axis=0)+records[2])[None,:],[.75],.2,3)
        np.testing.assert_allclose(direct.pma,grouped.pma,atol=1e-15)
        np.testing.assert_allclose(direct.mass,grouped.mass,atol=1e-15)
    def test_dpr_subdivision_preserves_mass_and_covered_world_area(self):
        raw=np.array([[.06,.03,.015,.12,.09]])
        for dpr in [1,2,3]:
            k=dpr*dpr;r=reconstruct(np.repeat(raw/k,k,axis=0),np.full(k,.6),.25/k,2)
            self.assertAlmostEqual(r.mass.sum(),.12);self.assertAlmostEqual(r.covered_area.sum(),.06)
            np.testing.assert_allclose(r.pma.sum(axis=0)/k,reconstruct(raw,[.6],.25,2).pma[0],atol=1e-15)
    def test_input_stocks_are_unchanged_and_reemission_keeps_excess(self):
        raw=np.array([[1,.5,.25,2,2]],dtype=np.float32);before=raw.tobytes()
        r=reconstruct(raw,[.1],1,1)
        self.assertEqual(raw.tobytes(),before);self.assertEqual(r.mass[0],2)
        self.assertAlmostEqual(r.layer_mass[0]+r.excess_mass[0],2)
    def test_finite_roundoff_clamp_is_reported(self):
        r=reconstruct([[1+1e-7,0,0,1,1]],[1],1,1)
        self.assertEqual(r.clamped_ratios,1);self.assertEqual(r.pma[0,0],1)
        with self.assertRaises(ValueError):reconstruct([[1.01,0,0,1,1]],[1],1,1)
    def test_malformed_or_unsupported_material_rejects(self):
        for raw,alpha,area,sigma in [([[0,0,0,0,1]],[1],1,1),([[0,0,0,-1,0]],[1],1,1),([[0,0,0,1,1]],[0],1,1),([[0,0,0,1,1]],[1],0,1),([[0,0,0,1,1]],[1],1,float('inf'))]:
            with self.assertRaises(ValueError):reconstruct(raw,alpha,area,sigma)

if __name__=='__main__':unittest.main()
