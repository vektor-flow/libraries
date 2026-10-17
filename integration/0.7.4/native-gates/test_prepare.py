"""Fail-closed receipt checks; no compiler or native process."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prepare',HERE/'prepare.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

class ReceiptTests(unittest.TestCase):
    def run_receipt(self, rows, blocked=False):
        cases=[{'id':'positive','status':'ready'}]
        if blocked:cases.append({'id':'rejection','status':'blocked'})
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            receipt=Path(temp)/'receipt.json'
            receipt.write_text(json.dumps({'owner':gate.OWNER,'manifest':{'path':'manifest','sha256':'pinned'},'cases':rows}))
            with patch.object(gate,'check',return_value={'cases':cases}),patch.object(gate,'pin',return_value={'path':'manifest','sha256':'pinned'}),contextlib.redirect_stdout(io.StringIO()):
                return gate.assess('manifest',receipt)
    def row(self):
        return dict(id='positive',binary_produced=True,posthash_match=True,
            **{name:dict(exit=0,timed_out=False,no_live_descendants=True,elapsed_seconds=1) for name in ['normalize','compile','run']})
    def test_positive_needs_all_three_stages(self):
        self.assertEqual(self.run_receipt([self.row()]),1)
        self.assertEqual(self.run_receipt([]),1)
        row=self.row();del row['run'];self.assertEqual(self.run_receipt([row]),1)
    def test_compile_failure_signal_timeout_and_unjoined_fail(self):
        for stage,key,value in [('compile','exit',1),('run','exit',-11),('run','timed_out',True),('run','no_live_descendants',False),('run','elapsed_seconds',30.01)]:
            with self.subTest(stage=stage,key=key):
                row=self.row();row[stage][key]=value;self.assertEqual(self.run_receipt([row]),1)
    def test_blocked_rejections_never_pass(self):
        self.assertEqual(self.run_receipt([self.row()],blocked=True),1)
    def test_duplicates_and_unknown_cases_rejected(self):
        with self.assertRaises(ValueError):self.run_receipt([self.row(),self.row()])
        row=self.row();row['id']='foreign'
        with self.assertRaises(ValueError):self.run_receipt([row])
    def test_mutated_pin_rejected(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            file=Path(temp)/'source';file.write_text('original');pin=gate.pin(file)
            file.write_text('changed')
            with self.assertRaises(ValueError):gate.verify(pin)

if __name__=='__main__':unittest.main()
