"""One geometry-only algorithm for an entire sequence of anonymous states.

No per-example planner selection or acceptance gate. Tests belong to the shared
algorithm; callers can inspect its output throughout the complete time domain.
Current replica topology/routing limitations remain research work.
"""
import numpy as np
from combined_transport import CombinedScene,BodyPlan
from morph_replica_transport import MorphGroup


def replica(source,targets):
 return MorphGroup(source,targets,body_factory=BodyPlan)


class StateSequence:
 def __init__(self,states):
  if len(states)<2 or any(not state for state in states):
   raise ValueError('At least two nonempty geometric states required')
  self.states=states
  self.plans=[CombinedScene(a,b,replica_factory=replica,allow_general_branching=True)
              for a,b in zip(states,states[1:])]
 def image(self,time):
  if not np.isfinite(time) or not 0<=time<=len(self.plans):
   raise ValueError('Time outside sequence')
  i=min(int(time),len(self.plans)-1)
  images,_=self.plans[i].images(float(time-i),validate=False)
  return np.max(images,axis=0)
