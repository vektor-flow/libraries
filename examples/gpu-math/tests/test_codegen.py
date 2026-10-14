import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from generate_gpu import Segments, distance_to_chord
from fontTools.svgLib.path import parse_path

class Codegen(unittest.TestCase):
    def test_counter_contours_keep_winding_orientation(self):
        pen=Segments(.01)
        parse_path('M0 0L4 0L4 4L0 4Z M1 1L1 3L3 3L3 1Z',pen)
        self.assertEqual(len(pen.segments),8)
        area=sum(a*d-c*b for a,b,c,d in pen.segments)/2
        self.assertEqual(area,12)
    def test_curve_has_bounded_chord_approximation(self):
        pen=Segments(.005)
        parse_path('M0 0Q1 2 2 0Z',pen)
        for i in range(101):
            t=i/100;point=(2*t,4*t*(1-t))
            self.assertLessEqual(min(distance_to_chord(point,s[:2],s[2:]) for s in pen.segments),.005)
    def test_open_contours_rejected(self):
        with self.assertRaises(ValueError):parse_path('M0 0L1 1',Segments(.01))

if __name__=='__main__':unittest.main()
