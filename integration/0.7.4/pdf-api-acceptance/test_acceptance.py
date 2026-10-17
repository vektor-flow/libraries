"""Lightweight fixture/preflight checks; never invoke a renderer or compiler."""
import json
from pathlib import Path
import unittest
from check_surface import gaps

ROOT = Path(__file__).resolve().parent
GOOD = 'tex2pdf(source:str,dest:str="",selectable:bit=true,editable:bit=false):\n    @:source\n'


class AcceptancePreparation(unittest.TestCase):
    def test_current_resource_signature_is_not_requested_api(self):
        legacy = 'tex2pdf(source:str,fonts:Catalog,operators:str,ordered_roles:[str],language:Language,include_layout:bit=true):'
        self.assertEqual(gaps(legacy), ['Missing direct parameter: dest',
            'Missing direct parameter: selectable', 'Missing direct parameter: editable',
            'Source-only named call still requires: fonts, operators, ordered_roles, language'])

    def test_surface_only_accepts_direct_optional_flags(self):
        # This deliberately fake implementation proves preflight is NOT behavior acceptance.
        self.assertEqual(gaps(GOOD), [])
        self.assertTrue(gaps(GOOD.replace('selectable:bit=true,editable:bit=false', 'options:Options')))
        self.assertTrue(gaps(GOOD.replace('dest:str=""', 'dest:str')))
        self.assertTrue(gaps(GOOD.replace('selectable:bit=true', 'selectable:bit=false')))
        self.assertTrue(gaps(GOOD.replace('editable:bit=false', 'editable:bit=true')))

    def test_preflight_fails_closed(self):
        for text in ['', GOOD + GOOD, GOOD.replace('source:str', 'source:str,source:str'),
                     GOOD.replace('dest:str=""', 'dest:str=choose("a","b")')]:
            self.assertTrue(gaps(text))

    def test_policy_matrix_and_dest_omission(self):
        cases = json.loads((ROOT / 'cases.json').read_text())
        self.assertEqual(len(cases), 6)
        self.assertEqual({(c['selectable'], c['editable']) for c in cases if c['id'].startswith('flags-')},
                         {(False, False), (False, True), (True, False), (True, True)})
        for case in cases:
            self.assertEqual(case['effectiveSelectable'], case['selectable'] or case['editable'])
            self.assertIn('latex.tex2pdf(source', case['call'])
        self.assertNotIn('editable:', cases[4]['call'])
        self.assertNotIn('dest:', cases[5]['call'])

    def test_exact_authored_selection_oracles(self):
        oracle = json.loads((ROOT / 'selection.json').read_text())
        source = (ROOT / 'source.tex').read_bytes().decode('utf8')
        self.assertIn('\r\n', source)
        self.assertIn('😀', source)
        self.assertIn('e\u0301', source)
        encoded = source.encode('utf-16-le')
        spans = oracle['spans']
        self.assertEqual([s['id'] for s in spans], ['word', 'math', 'display', 'macro', 'page2'])
        for span in spans:
            self.assertEqual(encoded[2*span['start']:2*span['end']].decode('utf-16-le'), span['text'])
        # Reverse hit order and duplicate glyphs still copy exact authored order.
        ids = oracle['reverseAndDuplicateHitIds']
        ordered = sorted((s for s in spans if s['id'] in set(ids)), key=lambda s: s['start'])
        self.assertEqual([s['text'] for s in ordered], oracle['expectedOrderedSourceFragments'])
        # An invocation must not silently select the macro definition's expansion.
        self.assertEqual(spans[3]['text'], '\\sq{z}')


if __name__ == '__main__':
    unittest.main()
