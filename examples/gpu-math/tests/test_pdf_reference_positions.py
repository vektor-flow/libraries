"""Replay an independently measured pdfTeX fixture through the PDF oracle."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from fontTools.t1Lib import T1Font

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pdf_reference_positions import pdf_reference_positions


@unittest.skipUnless(shutil.which('pdflatex')and shutil.which('kpsewhich'),'native pdfTeX required')
class PdfReferencePositionsTests(unittest.TestCase):
 def test_native_type1_origins_survive_intervening_bitmap_glyphs_and_baseline_changes(self):
  fixture=json.loads((ROOT/'tests/pdf-text-positions-native.json').read_text())
  native=T1Font(subprocess.check_output(['kpsewhich','cmr10.pfb'],text=True).strip())
  with tempfile.TemporaryDirectory()as tmp:
   directory=Path(tmp);(directory/'source.tex').write_text(fixture['source'])
   subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','source.tex'],cwd=directory,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
   pages=pdf_reference_positions(directory/'source.pdf',lambda name:native['Encoding']if name=='cmr10'else None)
  expected=[g for g in fixture['glyphs']if g['key'].startswith('text/@document:roman:')]
  # The native page number is also CMR10, after the eight controlled inputs.
  self.assertEqual(len(pages),1);self.assertEqual(len(pages[0]),len(expected)+1)
  for actual,glyph in zip(pages[0],expected):
   code=int(glyph['key'].split(':')[-1]);self.assertEqual(actual['identity'],('cmr10',native['Encoding'][code]))
   self.assertAlmostEqual(actual['x'],glyph['expected'][0],places=7)
   self.assertAlmostEqual(actual['y'],glyph['expected'][1],places=7)


if __name__=='__main__':unittest.main()
