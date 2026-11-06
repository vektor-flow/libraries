import unittest
import numpy as np
from ns_reference import Config
from material_transfer_reference import MaterialTransferSmoke

class TransferTests(unittest.TestCase):
 def test_instantaneous_release_debits_finite_solid_once_without_changing_air(self):
  s=MaterialTransferSmoke(Config(shape=(8,8,8),collector_flux=0,buoyancy=0,loading=0,cs=0))
  source=np.zeros_like(s.c);source[0,2:4,2:5,3:5]=.03;source[1,4:6,2:5,3:5]=.02
  s.attach_source('old-list',source);mass=s.total_material_mass();air=s.u.copy()
  self.assertTrue(np.all(s.c==0));s.advance_to(.2);np.testing.assert_array_equal(s.attached_mass(),mass)
  s.release_source('old-list');np.testing.assert_array_equal(s.c,source);np.testing.assert_array_equal(s.u,air)
  np.testing.assert_allclose(s.total_material_mass(),mass,atol=2e-15,rtol=0)
  with self.assertRaisesRegex(ValueError,'not attached'):s.release_source('old-list')
  with self.assertRaisesRegex(ValueError,'already'):s.attach_source('old-list',source)

 def test_capture_retains_uncaptured_gas_and_pending_solid_through_handover(self):
  cfg=Config(shape=(8,8,8),collector_start=0,collector_flux=.1,buoyancy=0,loading=0,cs=0)
  s=MaterialTransferSmoke(cfg);source=np.zeros_like(s.c);source[0,1:5,2:6,2:6]=.01;source[1,4:7,2:5,2:6]=.02
  s.attach_source('old-list',source);s.attach_source('later-list',source/2);initial=s.total_material_mass()
  s.set_collector(np.ones(s.shape),np.ones(s.shape));s.release_source('old-list');s.advance_to(.4)
  held=s.snapshot();restored=MaterialTransferSmoke.from_snapshot(held)
  for fluid in [s,restored]:fluid.advance_to(.8)
  np.testing.assert_array_equal(restored.c,s.c);np.testing.assert_array_equal(restored.receiver_deposits,s.receiver_deposits)
  np.testing.assert_array_equal(restored.attached_mass(),s.attached_mass())
  np.testing.assert_allclose(s.total_material_mass(),initial,atol=2e-15,rtol=0)
  self.assertGreater(float(s.mass().sum()),0);self.assertGreater(float(s.deposited.sum()),0);self.assertGreater(float(s.attached_mass().sum()),0)
  with self.assertRaisesRegex(ValueError,'already'):restored.attach_source('old-list',source)
  for fluid in [s,restored]:fluid.release_source('later-list');fluid.advance_to(1.)
  np.testing.assert_array_equal(restored.c,s.c);np.testing.assert_array_equal(restored.receiver_deposits,s.receiver_deposits)
  np.testing.assert_allclose(s.total_material_mass(),initial,atol=2e-15,rtol=0)

 def test_invalid_source_fields_cannot_create_or_overwrite_material(self):
  s=MaterialTransferSmoke(Config(shape=(8,8,8)));good=np.ones_like(s.c)
  for bad in [np.full_like(good,np.nan),-good,good[0]]:
   with self.assertRaises(ValueError):s.attach_source('invalid',bad)
  self.assertEqual(s.attached_sources,{})
  s.attach_source('source',good);good[:]=99
  self.assertEqual(float(s.attached_sources['source'].max()),1)
  with self.assertRaisesRegex(ValueError,'already'):s.attach_source('source',good)

if __name__=='__main__':unittest.main()
