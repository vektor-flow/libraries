import unittest
import numpy as np
from ns_reference import Config,Smoke
from receiver_reference import ReceiverSmoke

class ReceiverTests(unittest.TestCase):
 def test_spatial_capture_equals_existing_species_ledger_without_parking_gas(self):
  cfg=Config(shape=(8,8,8),lengths=(1,1,1),collector_start=0,collector_flux=.5,buoyancy=0,loading=0,cs=0,diffusivity=0,max_dt=1/240)
  s=ReceiverSmoke(cfg);s.c[0]=1;s.c[1]=.3
  s.set_collector(np.ones(s.shape),np.ones(s.shape));initial=s.mass().copy();s.advance_to(.5)
  np.testing.assert_allclose(s.receiver_deposits.sum(axis=(1,2,3))*s.dv,s.deposited,atol=2e-15,rtol=0)
  np.testing.assert_allclose(s.mass()+s.deposited,initial,atol=2e-15,rtol=0)
  np.testing.assert_allclose(s.receiver_deposits[0],1-np.exp(-.125),atol=1e-8)
  self.assertGreater(float(s.c[0].min()),0);self.assertGreater(float(s.receiver_deposits[0].min()),0)

 def test_moving_receiver_preserves_original_flow_and_accounts_actual_capture_cells(self):
  cfg=Config(shape=(8,8,8),collector_start=0,collector_flux=.03,buoyancy=0,loading=0,cs=0,max_dt=1/120)
  s=ReceiverSmoke.plumes(cfg,seed=701);x=s.centres
  mask=lambda centre:np.exp(-((x[0]-centre)/.25)**2-((x[1]-.5)/.2)**2)
  s.set_collector(mask(.9),np.ones(s.shape));s.transition_collector(mask(1.2),np.ones(s.shape),.3,start_time=.2)
  baseline=Smoke.from_snapshot(s.snapshot());initial=s.mass().copy();s.advance_to(.8);baseline.advance_to(.8)
  np.testing.assert_array_equal(s.u,baseline.u);np.testing.assert_array_equal(s.c,baseline.c)
  np.testing.assert_array_equal(s.deposited,baseline.deposited)
  np.testing.assert_allclose(s.receiver_deposits.sum(axis=(1,2,3))*s.dv,s.deposited,atol=2e-15,rtol=0)
  np.testing.assert_allclose(s.mass()+s.deposited,initial,atol=2e-15,rtol=0)
  self.assertGreater(float(np.ptp(s.receiver_deposits)),0);self.assertGreaterEqual(float(s.receiver_deposits.min()),0)

 def test_receiver_history_survives_view_handover_and_rejects_missing_captured_material(self):
  cfg=Config(shape=(8,8,8),collector_start=0,collector_flux=.03,buoyancy=0,loading=0,cs=0)
  s=ReceiverSmoke.plumes(cfg,seed=701);s.set_collector(np.ones(s.shape),np.ones(s.shape))
  initial=s.snapshot();s.advance_to(.4);handover=s.snapshot();restored=ReceiverSmoke.from_snapshot(handover)
  s.advance_to(.8);restored.advance_to(.8);direct=ReceiverSmoke.from_snapshot(initial);direct.advance_to(.8)
  np.testing.assert_array_equal(restored.receiver_deposits,s.receiver_deposits)
  np.testing.assert_array_equal(direct.receiver_deposits,s.receiver_deposits)
  np.testing.assert_array_equal(restored.c,s.c)
  del handover['receiverDeposits']
  with self.assertRaisesRegex(ValueError,'missing spatial'):ReceiverSmoke.from_snapshot(handover)

if __name__=='__main__':unittest.main()
