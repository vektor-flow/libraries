"""Infer a rigid alignment before same-topology contour interpolation.

Registration and deformation run concurrently. Validation remains mandatory:
this is not a guarantee of an intersection-free contour homotopy.
"""
import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment, minimize_scalar
from field_transport import Transport,normalize,clock

def rotation(a):
 c,s=np.cos(a),np.sin(a);return np.array([[c,-s],[s,c]])

class RegisteredTransport:
 def __init__(self,a,b):
  a,b=normalize(a),normalize(b)
  if len(a)!=len(b):raise ValueError('Registration requires equal hole counts')
  self.ca=a[0].mean(0);self.cb=b[0].mean(0)
  x=[p-self.ca for p in a];y=[p-self.cb for p in b]
  target=cKDTree(y[0]);hx=np.array([p.mean(0) for p in x[1:]]);hy=np.array([p.mean(0) for p in y[1:]])
  def loss(angle):
   r=rotation(angle);points=x[0]@r.T
   score=np.mean(target.query(points)[0]**2)+np.mean(cKDTree(points).query(y[0])[0]**2)
   if len(hx):
    costs=np.sum(((hx@r.T)[:,None]-hy[None,:])**2,axis=2);i,j=linear_sum_assignment(costs);score+=np.mean(costs[i,j])
   return float(score)
  angles=np.linspace(-np.pi,np.pi,73)[:-1];initial=min(angles,key=loss)
  result=minimize_scalar(loss,bounds=(initial-np.pi/36,initial+np.pi/36),method='bounded')
  self.angle=float(result.x);self.plan=Transport([p@rotation(self.angle).T for p in x],y);self.expected=self.plan.expected
 def contours(self,t):
  v=clock(t);r=rotation(-(1-v)*self.angle);center=(1-v)*self.ca+v*self.cb
  return [p@r.T+center for p in self.plan.contours(t)]
