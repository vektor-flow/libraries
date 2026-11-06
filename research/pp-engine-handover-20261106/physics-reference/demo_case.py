"""Declared demonstration conditions, separate from the fluid laws."""
import numpy as np
from ns_reference import Config,Smoke
from parcels import ParcelSmoke

def make_demo(shape=(16,12,8),count=16384):
    cfg=Config(shape=shape,collector_start=1.5,collector_flux=.24)
    s=Smoke.plumes(cfg,seed=701);X=s.centres;L=np.array(cfg.lengths)
    def collector(x):
        centre=L*np.array([x,.55,.5]);width=L*np.array([.16,.17,.40])
        return np.exp(-sum(((X[i]-centre[i])/width[i])**2 for i in range(3))/2)
    supply=np.exp(-((X[0]-.08*L[0])/(.05*L[0]))**2/2)*np.ones(s.shape)
    s.set_collector(collector(.70),supply)
    s.transition_collector(collector(.80),supply,.75,start_time=3.)
    return ParcelSmoke.from_fluid(s,count=count,seed=702) if count else s
