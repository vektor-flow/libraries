"""Host-only checker controls. Synthetic PDFs and historical PDFs are not native runs."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfWriter
from prepare import HERE, check, make_edit, stdin_text
from verify_artifacts import inspect, report_check, verify


class AcceptancePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((HERE / 'fixtures.json').read_text())
        cls.binding = json.loads(Path(cls.manifest['binding']['path']).read_text())
        cls.pdf = Path(cls.manifest['legacy_pdf']['path'])
        cls.report = Path(cls.manifest['legacy_report']['path'])

    def test_original_historical_artifact_is_only_checker_control(self):
        result = verify(self.pdf, self.report, 'original')
        self.assertTrue(result['artifact_checks_passed'])
        self.assertFalse(result['native_provenance_verified'])
        self.assertFalse(result['performance_qualified'])
        self.assertFalse(result['selection_qualified'])

    def test_exact_one_character_edit_and_utf16_offsets(self):
        raw = Path(self.manifest['original']['path']).read_bytes()
        edited, edit = make_edit(raw)
        self.assertEqual(edited, Path(self.manifest['edited']['path']).read_bytes())
        differences = [i for i, (a, b) in enumerate(zip(raw, edited)) if a != b]
        self.assertEqual(differences, [edit['startByte']])
        self.assertEqual(len(raw), len(edited))
        before = raw.decode('utf-8').encode('utf-16-le')
        self.assertEqual(before[2 * edit['startUTF16']:2 * edit['stopUTF16']], b's\0')
        with self.assertRaises(ValueError):
            make_edit(raw + raw)

    def test_stdin_preserves_resources_and_11_lines(self):
        for layout in (False, True):
            data = stdin_text(self.binding, self.manifest['edited']['path'], Path('/admitted/path with å'), layout)
            lines = data.splitlines()
            self.assertEqual(len(lines), 11)
            self.assertEqual(lines[1:8], [x['value'] for x in self.binding['ordered_lines'][1:8]])
            self.assertEqual(lines[10], '/admitted/path with å/layout.json' if layout else '')
        with self.assertRaises(ValueError):
            stdin_text(self.binding, 'injected\npath', Path('/admitted'))

    def test_report_failures_remain_failures(self):
        original = json.loads(self.report.read_text())
        faults = [('complete', False), ('complete', 1), ('pageCount', 39),
                  ('pageCount', 40.0), ('blockCount', 429), ('blockCount', True),
                  ('pdfBytes', original['pdfBytes'] - 1), ('diagnostics', ['failure']),
                  ('unresolved', ['provider']), ('unresolved', None)]
        for field, value in faults:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                bad = copy.deepcopy(original)
                bad[field] = value
                report_check(bad, self.pdf.stat().st_size)

    def test_forged_report_cannot_hide_wrong_pdf_page_count(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            directory = Path(directory)
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            pdf = directory / 'one-page.pdf'
            writer.write(pdf)
            report = directory / 'forged.json'
            value = json.loads(self.report.read_text())
            value['pdfBytes'] = pdf.stat().st_size
            report.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'page/encryption'):
                inspect(pdf, report)

    def test_unchanged_pdf_cannot_pass_as_small_edit(self):
        with self.assertRaisesRegex(ValueError, 'did not change'):
            verify(self.pdf, self.report, 'edited-full')

    def test_pdf_mutation_retains_legacy_failure_and_cannot_claim_edit(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            directory = Path(directory)
            pdf = directory / 'synthetic-comment.pdf'
            pdf.write_bytes(self.pdf.read_bytes() + b'\n% synthetic checker mutation only\n')
            value = json.loads(self.report.read_text())
            value['pdfBytes'] = pdf.stat().st_size
            report = directory / 'report.json'
            report.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'Legacy PDF byte mismatch'):
                verify(pdf, report, 'original')
            result = verify(pdf, report, 'edited-full')
            self.assertIn('correctness oracle pending', result['scope'])
            self.assertFalse(result['editing_qualified'])
            with self.assertRaisesRegex(ValueError, 'Separate fresh'):
                verify(pdf, report, 'updated', pdf, report)
            with self.assertRaisesRegex(ValueError, 'PDF mismatch'):
                verify(pdf, report, 'updated', self.pdf, self.report)

    def test_all_prepared_source_and_resource_pins_still_match(self):
        for ref in json.loads((HERE / 'input-pins.json').read_text()):
            check(ref)
        closure = json.loads((HERE / 'source-closure.json').read_text())
        names = {Path(ref['path']).name for ref in closure['sources']}
        self.assertTrue({'native_document_cli.vkf', 'latex.vkf', 'document_materialize.vkf',
                         'document_label_scene.vkf', 'document_pdf_bulk.vkf'} <= names)
        self.assertFalse(closure['linked_closure_qualified'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
