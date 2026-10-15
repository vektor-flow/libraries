import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tex_font_metrics import tex_kerning


def fixture(steps):
    # One character with a lig/kern program, two different kern values.
    lf = 6 + 2 + 1 + 2 + 1 + 1 + 1 + len(steps) + 2
    sizes = struct.pack('>12H', lf, 2, 65, 65, 2, 1, 1, 1, len(steps), 2, 0, 0)
    return (sizes + bytes(8) + bytes([1, 0, 1, 0]) + bytes(4 * 5)
            + b''.join(bytes(s) for s in steps) + struct.pack('>2i', -2**18, -2**19))


class TexKerningTests(unittest.TestCase):
    def test_first_match_wins_over_shared_tail_duplicate(self):
        raw = fixture([(0, 97, 128, 0), (128, 97, 128, 1)])
        self.assertEqual(tex_kerning(raw), {65: {97: -.25}})
        self.assertEqual(tex_kerning(raw + bytes(12)), {65: {97: -.25}})

    def test_prior_ligature_prevents_a_later_kern_for_same_pair(self):
        self.assertEqual(tex_kerning(fixture([(0, 97, 0, 66), (128, 97, 128, 1)])), {})

    def test_restart_and_skip_follow_executed_instructions(self):
        raw = fixture([(129, 0, 0, 1), (1, 97, 128, 0), (0, 98, 128, 0), (128, 99, 128, 1)])
        self.assertEqual(tex_kerning(raw), {65: {97: -.25, 99: -.5}})


if __name__ == '__main__':
    unittest.main()
