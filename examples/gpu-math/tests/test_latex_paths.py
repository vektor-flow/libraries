import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from latex_paths import extract, transform

class Paths(unittest.TestCase):
    def svg(self,body):
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="10 20 30 40">'+body+'</svg>'
    def test_repeated_outlines_keep_two_placements(self):
        result=extract(self.svg('<defs><path id="x" d="M0 0L1 0L1 1Z"/></defs>'
            '<use href="#x" x="12" y="24"/><use href="#x" x="20" y="30"/>'))
        self.assertEqual(len(result['outlines']),1)
        self.assertEqual([p['transform'][4:] for p in result['primitives']],[[2,4],[10,10]])
    def test_rules_and_cubic_curves_are_preserved(self):
        result=extract(self.svg('<path d="M10 20C11 21 12 22 13 23Z"/>'
            '<rect x="10" y="20" width="3" height=".4"/>'))
        self.assertEqual([p['kind'] for p in result['primitives']],['path','rule'])
        self.assertIn('C1.0 1.0 2.0 2.0 3.0 3.0',result['combinedPath'])
    def test_transform_order(self):
        self.assertEqual(transform('translate(2,3) scale(4)').transformPoint((1,1)),(6,7))
    def test_unsupported_svg_cannot_silently_drop(self):
        for body in ['<image/>','<path fill="red" d="M0 0L1 1Z"/>',
            '<use href="#missing"/>','<path clip-path="url(#a)" d="M0 0L1 1Z"/>',
            '<path transform="rotate(30)" d="M0 0L1 1Z"/>']:
            with self.assertRaises(ValueError): extract(self.svg(body))

if __name__=='__main__': unittest.main()
