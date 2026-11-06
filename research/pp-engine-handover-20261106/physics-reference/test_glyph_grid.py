import unittest
import numpy as np
from glyph_grid_reference import cell_average,extrude,frozen_reaction

class GlyphGridTests(unittest.TestCase):
 def test_conservative_nondivisible_pixel_and_cell_grids(self):
  a=np.random.default_rng(17).random((37,53))
  for shape in [(24,16),(7,11),(3,2),(80,60)]:
   b=cell_average(a,shape);self.assertEqual(b.shape,shape);self.assertGreaterEqual(b.min(),0);self.assertLessEqual(b.max(),1)
   self.assertAlmostEqual(float(b.mean()),float(a.mean()),places=14)
  b=extrude(a,(24,16,8),(1.6,1,.4));self.assertAlmostEqual(float(b.mean()),float(a.mean()),places=14)
 def test_mapping_retains_native_upward_y_coordinates(self):
  a=np.zeros((4,4));a[0,0]=1;b=cell_average(a,(2,2));self.assertEqual(b[0,1],.25);self.assertEqual(b.sum(),.25)
 def test_thin_receiver_falsifies_homogeneous_cell_absorption(self):
  a=np.zeros((40,80));a[15:17,10:70]=1
  r=frozen_reaction(a,(8,4,8),(2,1,.4),.03,1)
  self.assertGreater(r['coarseCaptured'],r['fineCaptured']*1.2)
  self.assertGreater(r['fineMaterialRemaining'],0)

if __name__=='__main__':unittest.main()
