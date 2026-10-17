import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'candidate'/'storage-direct-v3'))
import storage_controller as C
import recovery_check as R
from storage_paths import Rejected

STATE=json.loads((HERE/'state-before.json').read_text())
RECORD=STATE['phases'][R.KEY]
RAW=json.loads((HERE/'execstart-capture.json').read_text())['stdout']
GET=json.loads((HERE/'getunit-capture.json').read_text())['stdout']
ORIGINAL=json.loads((HERE/'original-result.json').read_text())
ANCHORS=json.loads((HERE/'recovery-anchors.json').read_text())
OBS=json.loads((HERE/'recovery-read-only-result.json').read_text())['observation']

class ParserTests(unittest.TestCase):
    def test_actual_recorded_response(self):
        row=C.parse_exec_start(RAW)
        self.assertEqual(len(row),10)
        self.assertEqual(row[1],RECORD['custody']['service_argv'])
        self.assertEqual(row[7:],[3956707,1,1])

    def test_old_bug_reproduced_on_recording(self):
        spec=importlib.util.spec_from_file_location('old',HERE/'original-storage_controller.py')
        old=importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
        with patch.object(old.Linux,'output',side_effect=[GET,RAW]):
            with self.assertRaisesRegex(Rejected,'single ExecStart required'):
                old.Linux().argv(RECORD['custody']['unit'])

    def test_linux_adapter_uses_recording(self):
        with patch.object(C.Linux,'output',side_effect=[GET,RAW]) as output:
            self.assertEqual(C.Linux().argv(RECORD['custody']['unit']),RECORD['custody']['service_argv'])
        self.assertEqual(output.call_args_list[1].args[0][5],C.parse_get_unit(GET))

    def test_reject_structural_mutations_of_real_recording(self):
        valid=json.loads(RAW)
        bad=[None,[],{},dict(type='s',data=valid['data']),dict(type=valid['type'],data=[]),
             dict(type=valid['type'],data=valid['data']*2),
             dict(type=valid['type'],data=[valid['data']]),  # prior invented wrapped shape
             dict(type=valid['type'],data=[valid['data'][0][:-1]]),
             dict(type=valid['type'],data=[valid['data'][0]+[0]]),
             dict(type=valid['type'],data='x'),dict(valid,extra=True)]
        for value in bad:
            with self.subTest(value=value):
                with self.assertRaises(RuntimeError): C.parse_exec_start(json.dumps(value))

    def test_reject_field_mutations_of_real_recording(self):
        for index,values in ((0,[None,1,'relative','/wrong','/nul\0']),
                             (1,[None,[],[1],['/wrong'],['/usr/bin/python3','x\0']]),
                             (2,[True,0,None,'false']),
                             (3,[-1,2**64,True,1.0,'1']),
                             (7,[-1,2**32,True]),(8,[-2**31-1,2**31,False]),
                             (9,[-2**31-1,2**31,False])):
            for value in values:
                v=json.loads(RAW); v['data'][0][index]=value
                with self.subTest(index=index,value=value):
                    with self.assertRaises(RuntimeError): C.parse_exec_start(json.dumps(v))

    def test_other_timestamp_fields_validated(self):
        for index in (4,5,6):
            v=json.loads(RAW); v['data'][0][index]=True
            with self.assertRaises(RuntimeError): C.parse_exec_start(json.dumps(v))

    def test_duplicate_keys_and_invalid_json(self):
        for raw in ('{','null','{"type":"bad","type":"a(sasbttttuii)","data":[]}'):
            with self.assertRaises(RuntimeError): C.parse_exec_start(raw)

    def test_exact_arg_strings_preserved(self):
        v=json.loads(RAW); v['data'][0][1]+=['','x y','quote"','back\\slash','λ']
        self.assertEqual(C.parse_exec_start(json.dumps(v))[1],v['data'][0][1])

    def test_getunit_strict(self):
        self.assertTrue(C.parse_get_unit(GET).endswith('_2eservice'))
        for data in ([],['/bad'],[1],[['/object']],['/org/freedesktop/systemd1/unit/a-b'],['/a','/b']):
            with self.assertRaises(RuntimeError): C.parse_get_unit(json.dumps(dict(type='o',data=data)))

class FailureTests(unittest.TestCase):
    def setup_controller(self, root):
        c=C.Controller.__new__(C.Controller); c.key=R.KEY
        c.g=dict(ram_peak_bytes=3*2**30,timeout_seconds=10,worker='F')
        c.gp=RECORD['grant']; c.mp=RECORD['manifest']
        c.m={k:str(root/k) for k in ('cwd','tmpdir','cache','ccache','receipts')}
        c.m['attempt_root']=str(root)
        c.current=lambda: None
        c.os=SimpleNamespace(show=lambda u:OBS['properties_before'],restore_high=lambda *a:self.fail('RAM restore attempted'))
        self.record=copy.deepcopy(RECORD)
        c.ledger=SimpleNamespace(reserve=lambda *a,**k:R.KEY,claim_launch=lambda *a,**k:self.record,
            preexec=lambda *a,**k:None,snapshot=lambda:dict(phases={R.KEY:self.record}),
            join=lambda *a,**k:self.fail('join attempted'))
        c.verify_join=lambda *a:self.fail('fabricated join verification attempted')
        return c

    def test_outer_seals_real_missing_attach_without_keyerror(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            c=self.setup_controller(Path(temp))
            with patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=1)),patch('sys.stderr',new=io.StringIO()):
                self.assertEqual(c.outer(),125)
            receipt=json.loads((Path(c.m['receipts'])/'controller-failure.json').read_text())
            self.assertEqual(receipt['missing'],['service','inner_result'])
            self.assertIs(receipt['passed'],False); self.assertIsNone(receipt['workload_result'])
            self.assertEqual(receipt['ram_intent_retained'],3*2**30)
            self.assertEqual(receipt['disk_charge_retained'],4*2**20)
            self.assertEqual(self.record,RECORD)
            self.assertFalse((Path(c.m['receipts'])/'service-join.json').exists())
            with self.assertRaisesRegex(RuntimeError,'NOT sealed'): c.seal_incomplete(self.record,outer_exit=1)

    def test_transport_exception_sealed_no_release(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            c=self.setup_controller(Path(temp))
            with patch.object(C.subprocess,'run',side_effect=C.subprocess.TimeoutExpired(['mock'],10)),patch('sys.stderr',new=io.StringIO()):
                self.assertEqual(c.outer(),125)
            receipt=json.loads((Path(c.m['receipts'])/'controller-failure.json').read_text())
            self.assertIn('TimeoutExpired',receipt['transport_error'])
            self.assertEqual(self.record,RECORD)

    def test_attached_but_missing_finish_is_explicit(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temp:
            c=self.setup_controller(Path(temp)); self.record['stage']='running'; self.record['service']={}
            with patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=1)),patch('sys.stderr',new=io.StringIO()):
                self.assertEqual(c.outer(),125)
            self.assertEqual(json.loads((Path(c.m['receipts'])/'controller-failure.json').read_text())['missing'],['inner_result'])

class HistoricalCustodyTests(unittest.TestCase):
    def controller(self):
        c=C.Controller.__new__(C.Controller)
        c.config_pin=RECORD['custody']['config']
        c.config=dict(coordinator=ANCHORS['coordinator'],preserved_record_authorities=[ANCHORS['preserved_authority']])
        c.os=SimpleNamespace(show=lambda unit:OBS['properties_before'],argv=lambda unit:C.parse_exec_start(RAW)[1])
        return c

    def test_old_hash_works_without_repinning_to_successor(self):
        c=self.controller()
        self.assertNotEqual(C.pin(C.HERE/'storage_controller.py'),RECORD['custody']['controller'])
        self.assertEqual(c.authenticate_record(copy.deepcopy(RECORD)),OBS['properties_before'])

    def test_unknown_historical_bundle_rejected(self):
        c=self.controller(); c.config['preserved_record_authorities']=[]
        with self.assertRaisesRegex(Rejected,'unapproved historical'): c.authenticate_record(RECORD)

    def test_changed_historical_source_rejected(self):
        c=self.controller(); real=C.pinned
        def reject(p):
            if p==RECORD['custody']['controller']: raise Rejected('source changed')
            return real(p)
        with patch.object(C,'pinned',side_effect=reject):
            with self.assertRaisesRegex(Rejected,'source changed'): c.authenticate_record(RECORD)

    def test_fresh_launch_cannot_use_old_controller_hash(self):
        c=self.controller(); c.config=C.pinned_json(c.config_pin)
        c.gp=RECORD['grant']; c.mp=RECORD['manifest']; c.g=C.pinned_json(c.gp); c.m=C.pinned_json(c.mp)
        with self.assertRaisesRegex(Rejected,'executing controller pin'): c.current()

    def test_old_missing_attach_never_normal_terminal_join(self):
        with self.assertRaisesRegex(Rejected,'terminal service/cgroup join'):
            self.controller().authenticate_record(RECORD,terminal=True)

class RecoveryTests(unittest.TestCase):
    def test_real_custody_pins_and_recorded_observation(self):
        before=copy.deepcopy(STATE)
        r=R.authenticate_sources(STATE,ORIGINAL,ANCHORS)
        result=R.validate_observation(r,OBS)
        self.assertFalse(result['ram_released']); self.assertFalse(result['passed'])
        self.assertEqual(result['total_F_charge'],19787718656)
        self.assertEqual(STATE,before)

    def test_wrong_state_or_fabricated_inner_completion_rejected(self):
        for key,value in [('stage','joined'),('inner_result',{'exit':0}),('service',{}),('join',{}),('phase_bytes',0),('ram_bytes',0)]:
            s=copy.deepcopy(STATE); s['phases'][R.KEY][key]=value
            with self.assertRaises(RuntimeError): R.authenticate_sources(s,ORIGINAL,ANCHORS)

    def test_changed_original_or_source_pin_rejected(self):
        original=copy.deepcopy(ORIGINAL); original['properties']['InvocationID']='0'*32
        with self.assertRaises(RuntimeError): R.authenticate_sources(STATE,original,ANCHORS)
        def reject(p): raise Rejected('changed pin')
        with self.assertRaisesRegex(Rejected,'changed pin'): R.authenticate_sources(STATE,ORIGINAL,ANCHORS,check=reject)

    def test_terminal_properties_negative_controls(self):
        for key,value in dict(InvocationID='0'*32,MainPID='1',ActiveState='active',LoadState='not-found',
            Result='success',ExecMainStatus='199',ExecMainCode='2',ExecMainPID='3956708',ControlGroup='/wrong',MemoryMax='1').items():
            o=copy.deepcopy(OBS)
            for suffix in ('before','after'): o['properties_'+suffix][key]=value
            with self.subTest(key=key):
                with self.assertRaises(RuntimeError): R.validate_observation(RECORD,o)

    def test_liveness_negative_controls(self):
        for key,value in dict(boot='wrong',outer_pid=1,outer_starttime=0,outer_absent_before=False,
            outer_absent_after=False,inner_absent_before=False,inner_absent_after=False,
            empty_before=False,empty_after=False,cgroup='/wrong').items():
            o=copy.deepcopy(OBS); o[key]=value
            with self.subTest(key=key):
                with self.assertRaises(RuntimeError): R.validate_observation(RECORD,o)

    def test_observation_race_or_argv_rejected(self):
        o=copy.deepcopy(OBS); o['properties_after']['InvocationID']='0'*32
        with self.assertRaises(RuntimeError): R.validate_observation(RECORD,o)
        o=copy.deepcopy(OBS); row=json.loads(RAW); row['data'][0][1].append('extra')
        for suffix in ('before','after'): o['execstart_'+suffix]=json.dumps(row)
        with self.assertRaises(RuntimeError): R.validate_observation(RECORD,o)
        o=copy.deepcopy(OBS); row=json.loads(RAW); row['data'][0][5]=0
        for suffix in ('before','after'): o['execstart_'+suffix]=json.dumps(row)
        with self.assertRaises(RuntimeError): R.validate_observation(RECORD,o)

if __name__=='__main__': unittest.main(verbosity=2)
