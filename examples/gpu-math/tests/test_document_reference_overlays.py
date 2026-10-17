import sys,tempfile,unittest,shutil
from pathlib import Path
import numpy as np
import pymupdf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from document_reference_overlays import arxiv_stamp_regions,mask_reference_overlays
from compare_document_geometry import compare_geometry

STAMP='arXiv:1801.05894v1  [math.HO]  17 Jan 2018'

class ReferenceOverlayTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('mutool'),'mutool independent trace required')
 def test_default_position_gate_accepts_point_zero_nine_and_rejects_point_one_one_pixels(self):
  with tempfile.TemporaryDirectory()as tmp,pymupdf.open()as doc:
   root=Path(tmp);page=doc.new_page(width=612,height=792)
   page.insert_text((150,200),'A',fontname='tiro',fontsize=10);pdf=root/'source.pdf';doc.save(pdf)
   item={'kind':'glyph','key':'native/A','y':200,'nativeGlyph':{'fontName':'times-roman','glyphName':'A','fontSize':10}}
   for error,passed in [(.09,True),(.11,False)]:
    item['x']=150+error*72/96
    result=compare_geometry(pdf,{'pages':[{'items':[item]}]},{'maps':{}},root/f'{error}.xml')
    self.assertEqual(result['positionTolerancePixels'],.1);self.assertEqual(result['passed'],passed)
   for limit in [0,-1,float('nan'),float('inf')]:
    with self.assertRaises(ValueError):compare_geometry(pdf,{}, {},root/'invalid.xml',position_tolerance_pixels=limit)

 def document(self,rotate=90,x=32):
  doc=pymupdf.open();page=doc.new_page(width=612,height=792)
  page.insert_text((x,570),STAMP,fontname='tiro',fontsize=20,rotate=rotate)
  return doc
 def test_only_complete_rotated_margin_stamp_is_selected(self):
  with self.document()as doc:
   regions=arxiv_stamp_regions(doc[0]);self.assertEqual(len(regions),1);self.assertEqual(regions[0]['glyphs'],42);self.assertEqual(regions[0]['text'],STAMP)
  for rotate,x in [(0,32),(90,150)]:
   with self.document(rotate,x)as doc:self.assertEqual(arxiv_stamp_regions(doc[0]),[])
 def test_overlapping_body_content_is_never_excluded(self):
  with self.document()as doc:
   doc[0].insert_text((25,400),'Body text',fontsize=10)
   with self.assertRaisesRegex(ValueError,'overlaps'):arxiv_stamp_regions(doc[0])
 def test_reference_mask_preserves_original_and_other_content(self):
  with self.document()as doc:
   page=doc[0];page.insert_text((150,200),'Source text',fontsize=10)
   raster=page.get_pixmap(matrix=pymupdf.Matrix(96/72,96/72),alpha=False)
   original=np.frombuffer(raster.samples,dtype=np.uint8).reshape(raster.height,raster.width,3).copy();saved=original.copy()
   regions=arxiv_stamp_regions(page);masked=mask_reference_overlays(original,regions)
   self.assertTrue(np.array_equal(original,saved));self.assertFalse(np.array_equal(masked,original));self.assertTrue(np.array_equal(masked[:,100:],original[:,100:]));self.assertEqual(int(masked[:,:60].min()),255)
   # Unexpected renderer ink is not erased: only the reference array is masked.
   unexpected_gpu=original.copy();self.assertTrue(np.any(masked!=unexpected_gpu))
 @unittest.skipUnless(shutil.which('mutool'),'mutool independent trace required')
 def test_geometry_requires_explicit_opt_in_and_records_each_exclusion(self):
  with tempfile.TemporaryDirectory()as tmp,self.document()as doc:
   root=Path(tmp);pdf=root/'source.pdf';doc.save(pdf)
   layout={'pages':[{'items':[]}]};data={'maps':{}}
   strict=compare_geometry(pdf,layout,data,root/'strict.xml')
   source=compare_geometry(pdf,layout,data,root/'source.xml',exclude_arxiv_stamp=True)
   self.assertFalse(strict['passed']);self.assertEqual(len(strict['pages'][0]['missingReferenceGlyphs']),42)
   self.assertTrue(source['passed']);self.assertEqual(source['pages'][0]['excludedReferenceGlyphs'],42);self.assertEqual(len(source['pages'][0]['excludedReferenceOverlays']),1)

if __name__=='__main__':unittest.main()
