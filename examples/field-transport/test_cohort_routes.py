import unittest
import numpy as np
from cohort_routes import CohortRoutes
from field_transport import clock


class CohortRouteTests(unittest.TestCase):
 def test_changing_sizes_exchange_without_contact(self):
  def geometry(t):
   u=clock(t)
   return np.array([[-90+180*u,0],[90-180*u,0]]),np.array([18+12*u,30-12*u])
  def images(t):
   centers,radii=geometry(t);out=[]
   for center,radius in zip(centers,radii):
    im=np.zeros((720,1280),np.uint8);c=center+[640,360]
    lo=np.floor(c-radius-2).astype(int);hi=np.ceil(c+radius+2).astype(int)
    yy,xx=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]]
    im[lo[1]:hi[1],lo[0]:hi[0]]=np.uint8(((xx+.5-c[0])**2+(yy+.5-c[1])**2<radius**2)*255)
    out.append(im)
   return out
  def validate(route):
   for t in np.linspace(0,1,257):
    centers,radii=geometry(float(t));centers+=route.displacements(float(t))
    if np.linalg.norm(centers[0]-centers[1])<=sum(radii):raise ValueError('Independent circle contact')
  route=CohortRoutes(images,2,validate);validate(route)
  self.assertGreater(abs(route.displacements(.5)).max(),45)
  np.testing.assert_allclose(route.displacements(0),0,atol=1e-10)
  np.testing.assert_allclose(route.displacements(1),0,atol=1e-10)
  for t in [0,1]:
   displacement=lambda e:np.linalg.norm(route.displacements(t+e if t==0 else t-e))
   self.assertLess(displacement(.001),.002*displacement(.01))
 def test_empty_material_is_rejected(self):
  with self.assertRaises(ValueError):CohortRoutes(lambda t:[np.zeros((720,1280),np.uint8)],1,lambda route:None)
 def test_replay_failure_cannot_be_ignored(self):
  im=np.zeros((720,1280),np.uint8);im[350:370,630:650]=255
  def reject(route):raise ValueError('Independent validator rejected candidate')
  with self.assertRaisesRegex(ValueError,'No sampled cohort corridor'):
   CohortRoutes(lambda t:[im],1,reject)


class NonrigidSceneTests(unittest.TestCase):
 def test_nonrigid_bodies_exchange_with_hole_and_exact_endpoints(self):
  from benchmark_morphology import generated_cases
  from combined_transport import CombinedScene,topology
  from validated_transport import ValidatedCombinedScene
  from scene_transport import draw_scene
  from scipy import ndimage as ndi
  item=next(p for p in generated_cases() if p['id']=='nonrigid-hole-crossing')
  a,b=item['geometry'];original=CombinedScene(a,b)
  with self.assertRaises(ValueError):
   for t in np.linspace(0,1,17):original.images(float(t))
  candidate=ValidatedCombinedScene(a,b);self.assertIsNotNone(candidate.cohort_route)
  for t in np.linspace(0,1,33):
   ims,_=candidate.images(float(t));mask=np.max(ims,axis=0)>127
   self.assertEqual(topology(mask),(2,1))
   if t in [0,1]:
    truth=draw_scene(a if t==0 else b,ss=8)>127
    self.assertFalse(np.any(mask&~ndi.binary_dilation(truth)))
    self.assertFalse(np.any(ndi.binary_erosion(truth)&~mask))


if __name__=='__main__':unittest.main()
