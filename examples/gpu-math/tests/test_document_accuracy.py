import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from document_accuracy import spatial_accuracy

class SpatialAccuracyTests(unittest.TestCase):
 def page(self):
  image=np.full((200,1000,3),255,np.uint8)
  for i in range(200):
   x,y=5+(i%50)*19,10+(i//50)*40;image[y:y+12,x:x+8]=0
  return image
 def test_missing_single_glyph_is_not_hidden_by_global_score(self):
  r=self.page();a=r.copy();a[10:22,5:13]=255
  R=r.mean(2)<178;A=a.mean(2)<178;self.assertGreaterEqual((R&A).sum()/(R|A).sum(),.995)
  report=spatial_accuracy(r,a);self.assertFalse(report['localPixelsPassed']);self.assertEqual(report['worstReferenceComponentCoverage'],0);self.assertEqual(report['referenceInkBeyond1px'],96)
 def test_distributed_one_pixel_edge_variation_is_separate_from_missing_content(self):
  r=self.page();a=np.full_like(r,255);a[:,1:]=r[:,:-1]
  report=spatial_accuracy(r,a);self.assertTrue(report['localPixelsPassed']);self.assertEqual(report['referenceCoverageWithin1px'],1);self.assertEqual(report['gpuCoverageWithin1px'],1)
 def test_displaced_one_glyph_is_localized(self):
  r=self.page();a=r.copy();a[10:22,5:13]=255;a[10:22,9:17]=0
  report=spatial_accuracy(r,a);self.assertFalse(report['localPixelsPassed']);self.assertTrue(report['regions']);self.assertEqual(len(report['regions']),2)
if __name__=='__main__':unittest.main()
