"""Spatial bookkeeping of the existing SSPRK3 collector, not a fluid solver.

Captured pigment becomes receiver stock; it is no longer a gas particle. This
does not implement glyph masks, stroke formation or thermal phase change.
"""
import numpy as np
from ns_reference import Smoke

class ReceiverSmoke(Smoke):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.receiver_deposits=np.zeros_like(self.c)
        self._capture_stages=[]

    def rhs(self,state,sink):
        result=super().rhs(state,sink)
        self._capture_stages.append(sink*state[2])
        return result

    def step(self,dt):
        self._capture_stages=[]
        super().step(dt)
        if len(self._capture_stages)!=3:raise RuntimeError('Unexpected accepted SSPRK3 stage count')
        first,second,third=self._capture_stages
        self.receiver_deposits+=dt*(first/6+second/6+2*third/3)
        self._capture_stages=[]

    def snapshot(self):
        return {**super().snapshot(),'receiverDeposits':self.receiver_deposits.copy()}

    @classmethod
    def from_snapshot(cls,snapshot):
        s=super().from_snapshot(snapshot)
        if 'receiverDeposits' not in snapshot:
            if np.any(s.deposited):raise ValueError('Cannot reconstruct missing spatial receiver history')
            return s
        value=np.asarray(snapshot['receiverDeposits'])
        if value.shape!=s.c.shape or not np.all(np.isfinite(value)) or np.any(value<0):
            raise ValueError('Invalid spatial receiver history')
        if not np.allclose(value.sum(axis=(1,2,3))*s.dv,s.deposited,atol=2e-12,rtol=1e-10):
            raise ValueError('Spatial and total receiver histories disagree')
        s.receiver_deposits=value.copy()
        return s
