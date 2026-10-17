#!/usr/bin/env python3
"""Check the authored VKF expected values with an independent host codec.

This reads only test expressions. It neither interprets production VKF nor
executes a compiler/native binary. Passing means the native test ORACLES are
consistent, not that the native implementation passed those tests.
"""
import ast
import json
from pathlib import Path
import re
import unittest

HERE = Path(__file__).resolve().parent
TESTS = HERE / 'candidate/examples/gpu-math/native-vkf/pdf_selection_tests.vkf'
ASSERTION = re.compile(r'^    \((.+)=("(?:[^"\\]|\\.)*")\)\?! ("(?:[^"\\]|\\.)*")$')
CALL = re.compile(r'(p|legacy)\.(\w+)\((.*)\)$')


def arguments(source):
    """Parse only test literals, integer constants and str(chr(integer))."""
    tree = ast.parse('[' + source + ']', mode='eval')

    def literal(node):
        if isinstance(node, ast.Constant) and type(node.value) in (str, int):
            return node.value
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'str' and len(node.args) == 1
                and not node.keywords):
            inner = node.args[0]
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id == 'chr' and len(inner.args) == 1
                    and not inner.keywords):
                return chr(literal(inner.args[0]))
        raise ValueError('Unsupported test expression: ' + ast.dump(node))

    return [literal(node) for node in tree.body.elts]


def read_vectors():
    vectors = []
    for line in TESTS.read_text(encoding='utf-8').splitlines():
        if '?!' not in line:
            continue
        match = ASSERTION.fullmatch(line)
        if not match:
            raise ValueError('Unparsed VKF assertion: ' + line)
        call, expected, label = match.groups()
        match = CALL.fullmatch(call)
        if not match:
            raise ValueError('Unparsed VKF call: ' + call)
        module, function, args = match.groups()
        vectors.append((module, function, arguments(args), json.loads(expected), json.loads(label)))
    return vectors


def oracle_text(value):
    return '<' + (b'\xfe\xff' + value.encode('utf-16-be', errors='strict')).hex().upper() + '>'


class IndependentOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors = read_vectors()

    def test_vector_inventory(self):
        counts = {}
        for module, function, args, expected, label in self.vectors:
            counts[(module, function)] = counts.get((module, function), 0) + 1
        self.assertEqual(counts, {
            ('p', 'utf16be_text_string'): 16,
            ('p', 'utf16be_scalar_hex'): 15,
            ('p', 'actual_text'): 7,
            ('legacy', 'hex_string'): 3,
        })

    def test_exact_text_string_oracles(self):
        for module, function, args, expected, label in self.vectors:
            if function != 'utf16be_text_string':
                continue
            with self.subTest(label=label):
                self.assertEqual(expected, oracle_text(*args))
                self.assertRegex(expected, r'^<FEFF(?:[0-9A-F]{4})*>$')
                self.assertEqual(bytes.fromhex(expected[5:-1]).decode('utf-16-be'), args[0])

    def test_exact_scalar_oracles(self):
        for module, function, args, expected, label in self.vectors:
            if function != 'utf16be_scalar_hex':
                continue
            with self.subTest(label=label):
                self.assertEqual(expected, chr(args[0]).encode('utf-16-be').hex().upper())

    def test_exact_marked_content_oracles(self):
        for module, function, args, expected, label in self.vectors:
            if function != 'actual_text':
                continue
            logical, drawing = args
            with self.subTest(label=label):
                match = re.fullmatch(r'/Span << /ActualText (<[0-9A-F]+>) >> BDC\n(.*)\nEMC\n', expected, re.S)
                self.assertIsNotNone(match)
                self.assertEqual(match[1], oracle_text(logical))
                # Check drawing bytes separately from replacement text/framing.
                self.assertEqual(match[2].encode('utf-8'), drawing.encode('utf-8'))

    def test_legacy_utf8_oracles(self):
        for module, function, args, expected, label in self.vectors:
            if module != 'legacy':
                continue
            with self.subTest(label=label):
                self.assertEqual(expected, '<' + args[0].encode('utf-8').hex().upper() + '>')


if __name__ == '__main__':
    print('HOST ORACLE VALIDATION ONLY; all 41 native VKF assertions UNEXECUTED.', flush=True)
    unittest.main(verbosity=2)
