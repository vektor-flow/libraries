import unittest
import numpy as np
from scipy import ndimage as ndi
from stroke_transport import connected_field

class StrokeConnectivityTests(unittest.TestCase):
 def test_residual_island_stays_connected_at_every_area_threshold(self):
  y,x=np.mgrid[:45,:85]
  primary=12-np.hypot(x-20,y-22)
  orphan=3-np.hypot(x-64,y-22)
  field=np.maximum(primary,orphan)
  corrected=connected_field(field)
  for threshold in np.linspace(corrected.min(),corrected.max(),101,endpoint=False):
   self.assertEqual(ndi.label(corrected>threshold)[1],1)
  self.assertTrue(np.all(corrected<=field))
  self.assertEqual(corrected.max(),field.max())
 def test_connected_endpoint_and_field_continuity(self):
  y,x=np.mgrid[:45,:85];field=12-np.hypot(x-40,y-22)
  np.testing.assert_array_equal(connected_field(field),field)
  perturb=.01*np.sin(x/5)*np.cos(y/7)
  self.assertLessEqual(np.max(abs(connected_field(field+perturb)-connected_field(field))),.01+1e-12)

 def test_stroke_validation_checks_between_coarse_samples(self):
  from types import SimpleNamespace
  from scene_transport import draw_scene
  from validated_transport import valid_body
  body=[np.array([[-8,-8],[8,-8],[8,8],[-8,8]],float)]
  endpoint=draw_scene([body],ss=8)
  class ResidualStroke:
   def image(self,t):
    im=endpoint.copy()
    if abs(t-.9140625)<1e-10:im[360,700]=255
    return im,float(im.sum()/255)
  plan=SimpleNamespace(kind='stroke',plan=ResidualStroke())
  self.assertFalse(valid_body(plan,body,body))

if __name__=='__main__':unittest.main()
