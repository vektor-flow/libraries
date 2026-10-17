"""Compile VKF itself; Python only drives independent runtime assertions.

Set VKF_COMPILER to the Linux compiler. No document is known during compilation.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPILER = os.environ.get('VKF_COMPILER')


@unittest.skipUnless(COMPILER, 'VKF_COMPILER is required for native compiler checks')
class NativeVkfTokens(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='vkf-renderer-tests-')
        cls.directory = Path(cls.temp.name)
        cls.executable = cls.directory / 'token-dump'
        subprocess.run([COMPILER, '-b', str(ROOT/'native-vkf/token_dump.vkf'),
                        '-o', str(cls.executable)], check=True, capture_output=True,
                       text=True, timeout=120)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def tokens(self, source):
        path = self.directory / 'changed-after-compilation.tex'
        path.write_text(source)
        run = subprocess.run([str(self.executable)], input=str(path)+'\n',
                             check=True, capture_output=True, text=True, timeout=10)
        fields = list(map(int, run.stdout.split()))
        self.assertEqual(len(fields), 1+3*fields[0])
        raw = source.encode()
        return [(fields[i], fields[i+1], fields[i+2],
                 raw[fields[i+1]:fields[i+2]].decode())
                for i in range(1, len(fields), 3)]

    def check_tokens(self, source, expected):
        actual = self.tokens(source)
        self.assertEqual([(kind, text) for kind, _, _, text in actual], expected)
        previous = 0
        for _, start, stop, text in actual:
            self.assertGreaterEqual(start, previous)
            self.assertEqual(stop-start, len(text.encode()))
            previous = stop

    def test_math_commands_comments_and_utf8_byte_spans(self):
        self.check_tokens('A $x_i^2$ \\alpha{é} % ignored\nB', [
            (7, 'A'), (6, ' '), (5, '$'), (7, 'x'), (9, '_'), (7, 'i'),
            (8, '^'), (7, '2'), (5, '$'), (6, ' '), (1, '\\alpha'),
            (3, '{'), (7, 'é'), (4, '}'), (6, ' '), (7, 'B')])

    def test_literal_link_targets_preserve_percent_and_hash(self):
        self.check_tokens(r'\url{https://a.test/x%20#p} A', [
            (1, '\\url'), (12, '{https://a.test/x%20#p}'), (6, ' '), (7, 'A')])
        self.check_tokens(r'\href {https://a.test/\{x\}%20}{label}', [
            (1, '\\href'), (6, ' '), (12, r'{https://a.test/\{x\}%20}'),
            (3, '{'), (7, 'label'), (4, '}')])
        self.check_tokens(r'\url|a%20#b|', [(1, '\\url'), (12, '|a%20#b|')])

    def test_verbatim_and_escaped_control_symbols(self):
        self.check_tokens(r'\verb*|{a}%$| \%\{\}', [
            (12, r'\verb*|{a}%$|'), (6, ' '), (2, r'\%'),
            (2, r'\{'), (2, r'\}')])

    def test_one_executable_reads_fresh_unknown_sources(self):
        before = self.tokens('first α')
        after = self.tokens('a different β document')
        restored = self.tokens('first α')
        self.assertNotEqual(before, after)
        self.assertEqual(before, restored)
        self.assertEqual(self.tokens(''), [])
