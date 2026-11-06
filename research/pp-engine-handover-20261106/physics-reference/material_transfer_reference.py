"""Finite solid→aerosol initial-condition transfer for the accepted fluid.

Research bookkeeping only. Inputs are declared solid-density fields, not glyph
geometry. Release is instantaneous, with no heat/normal impulse: gas then uses
the existing resolved velocity. This is not a thermal sublimation model.
"""
import numpy as np
from receiver_reference import ReceiverSmoke

class MaterialTransferSmoke(ReceiverSmoke):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.attached_sources={};self.released_sources=set()

    def attach_source(self,identity,density):
        if not isinstance(identity,str) or not identity or len(identity)>128:raise ValueError('A bounded source identity is required')
        if identity in self.attached_sources or identity in self.released_sources:raise ValueError('Source material was already attached')
        if len(self.attached_sources)+len(self.released_sources)>=32:raise ValueError('Source history budget exceeded')
        value=np.asarray(density,dtype=float)
        if value.shape!=self.c.shape or not np.all(np.isfinite(value)) or np.any(value<0):raise ValueError('Invalid attached material density')
        self.attached_sources[identity]=value.copy()

    def release_source(self,identity):
        if identity not in self.attached_sources:raise ValueError('Source material is not attached')
        self.c+=self.attached_sources.pop(identity);self.released_sources.add(identity)

    def attached_mass(self):
        return sum((v.sum(axis=(1,2,3))*self.dv for v in self.attached_sources.values()),np.zeros(3))

    def total_material_mass(self):
        return self.attached_mass()+self.mass()+self.deposited

    def snapshot(self):
        return {**super().snapshot(),'attachedSources':{k:v.copy() for k,v in self.attached_sources.items()},'releasedSources':sorted(self.released_sources)}

    @classmethod
    def from_snapshot(cls,snapshot):
        s=super().from_snapshot(snapshot)
        for identity,value in snapshot.get('attachedSources',{}).items():s.attach_source(identity,value)
        released=snapshot.get('releasedSources',[])
        if len(released)+len(s.attached_sources)>32 or any(not isinstance(v,str) or not v or len(v)>128 or v in s.attached_sources for v in released) or len(set(released))!=len(released):raise ValueError('Invalid released material history')
        s.released_sources=set(released)
        return s
