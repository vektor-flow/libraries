"""Bounded source/mock tests. No namespace, service, compiler or native launch."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
CODE = HERE/'candidate/storage-direct-v6'
ROOT = HERE.parents[4]
BASE = ROOT/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb'
V5 = BASE/'storage-direct-v5'
V4 = BASE/'storage-direct-v4'
sys.path.insert(0, str(CODE))
import storage_admission as sa
import storage_controller as sc
import storage_paths as sp
import terminal_recovery as tr
import private_workload as pw
import effective_storage as es
LIVE = sp.strict_json((HERE.parent/'storage-live-09/final-state.json').read_text())
CONFIG = sp.strict_json((CODE/'runtime-config.json').read_text())
RAW = (HERE.parent/'storage-live-09/live09-f-success-01-mountinfo.txt').read_text()
ORIGIN = dict(cgroup='/parent/vkfworkers-f-test.service', uid=1000, gid=1000,
              namespaces={n:n+'-original' for n in ('mnt','user','pid','net')})
M = dict(attempt_root='/charged/attempt',cwd='/charged/attempt/work',argv=['/usr/bin/python3.14','-B','/payload.py'])
PRIVATE = '10 9 8:1 / / ro - ext4 /dev/mock rw\n20 10 8:1 / /charged/attempt rw - ext4 /dev/mock rw\n'

class ExecReached(Exception): pass

class Wrapper(unittest.TestCase):
    def setUp(self):
        self.events=[]
        policy = patch.object(pw, 'policy_gate', return_value={'mock':True})
        policy.start(); self.addCleanup(policy.stop)
    def run_gate(self,stage='post',raw=PRIVATE,context=None,inspect=None,exec_error=ExecReached):
        now=copy.deepcopy(ORIGIN)
        for n in now['namespaces']:
            if stage=='post' or n in ('mnt','user'):now['namespaces'][n]+='-new'
        if context is not None:now=context
        def read(p,*args,**kwargs):
            if str(p)=='/proc/self/mountinfo':self.events.append('snapshot');return raw
            if str(p) in ('/proc/self/uid_map','/proc/self/gid_map'):return '1000 1000 1\n'
            raise AssertionError(str(p))
        def dep():self.events.append('dependencies')
        original_check = es.check
        def storage(*args):
            self.events.append('strict-storage')
            return original_check(*args,inspect=inspect or (lambda path:es.Observation(
                10 if path=='/' else 20,(8,1),1,stat.S_IFDIR|0o700,(0,0),path=='/',1000,1000)))
        def execute(*args):self.events.append(('exec',args));raise exec_error()
        with patch.object(pw,'verify_dependencies',side_effect=dep),patch.object(pw,'context',return_value=now),\
             patch.object(Path,'read_text',read),patch.object(pw.effective_storage,'check',side_effect=storage),\
             patch.object(pw.os,'execv',side_effect=execute),contextlib.redirect_stdout(io.StringIO()) as output:
            # Avoid recursive patch of the imported check function.
            with self.assertRaises(exec_error if raw==PRIVATE and context is None else sp.Rejected):
                pw.gate(stage,ORIGIN,M['attempt_root'],[pw.BWRAP] if stage=='pre' else M['argv'])
        return output.getvalue()
    def test_exact_prefix_and_single_rw_bind(self):
        argv=pw.command(M,ORIGIN)
        self.assertEqual(argv[:7],[pw.UNSHARE,'--user','--map-current-user','--mount','--propagation','private','--'])
        self.assertEqual(argv.count('--bind'),1)
        i=argv.index('--bind');self.assertEqual(argv[i:i+3],['--bind',M['attempt_root'],M['attempt_root']])
        for token in ('--fork','--kill-child','--map-root-user','--keep-caps','--unshare-cgroup','sudo'):
            self.assertNotIn(token,argv)
        self.assertEqual(argv.count('--unshare-user'),1)
        self.assertEqual(argv[argv.index('--remount-ro'):argv.index('--bind')],
                         ['--remount-ro','/dev/pts','--remount-ro','/dev','--remount-ro','/proc'])
        self.assertLess(argv.index('pre'),argv.index(pw.BWRAP));self.assertLess(argv.index('post'),argv.index('/payload.py'))
        self.assertIn('--unshare-pid',argv);self.assertIn('--unshare-net',argv);self.assertIn('--die-with-parent',argv)
    def test_pre_gate_records_then_execs_bwrap_without_child(self):
        out=self.run_gate('pre');self.assertIn('private_workload_precondition',out)
        self.assertEqual(self.events[:2],['dependencies','snapshot']);self.assertEqual(self.events[-1][1][0],pw.BWRAP)
    def test_post_gate_records_and_checks_storage_before_payload(self):
        # Keep original check callable before patching its module attribute.
        original=es.check
        observations=lambda path:es.Observation(10 if path=='/' else 20,(8,1),1,stat.S_IFDIR|0o700,(0,0),path=='/',1000,1000)
        now=copy.deepcopy(ORIGIN);now['namespaces']={n:v+'new' for n,v in now['namespaces'].items()}
        output=io.StringIO()
        with patch.object(pw,'verify_dependencies'),patch.object(pw,'context',return_value=now),\
             patch.object(Path,'read_text',return_value=PRIVATE),\
             patch.object(es,'check',side_effect=lambda raw,attempt:original(raw,attempt,inspect=observations)) as check,\
             patch.object(pw.os,'execv',side_effect=ExecReached) as execute,contextlib.redirect_stdout(output):
            with self.assertRaises(ExecReached):pw.gate('post',ORIGIN,M['attempt_root'],M['argv'])
            check.assert_called_once();execute.assert_called_once_with(M['argv'][0],M['argv'])
        lines=[json.loads(x) for x in output.getvalue().splitlines()]
        self.assertEqual(lines[0]['mountinfo'],PRIVATE);self.assertTrue(lines[1]['private_workload_postcondition'])
    def test_actual_live09_rejected_before_observation_or_exec(self):
        self.assertEqual(hashlib.sha256(RAW.encode()).hexdigest(),'73cd712b8582fb723bdad67d528bfb295fac84516ab2ce23de14b50045963dba')
        rows=es.parse_mountinfo(RAW);self.assertEqual(len(rows),407)
        self.assertEqual(sum(bool(r.optional) for r in rows.values()),403)
        self.assertEqual(next(r for r in rows.values() if r.path=='/' and r.parent not in rows).optional,('master:1',))
        with self.assertRaisesRegex(es.Rejected,'propagating mount topology'):
            es.check(RAW,M['attempt_root'],inspect=lambda p:self.fail('must not inspect propagated tree'))
        for stage in ('pre','post'):
            self.events=[];out=self.run_gate(stage,raw=RAW)
            self.assertIn('master:1',out);self.assertFalse(any(isinstance(x,tuple) for x in self.events))
    def test_entire_captured_topology_model_not_root_only(self):
        lines=[]
        for line in RAW.splitlines():
            a,b=line.split(' - ');lines.append(' '.join(a.split()[:6])+' - '+b)
        model='\n'.join(lines)+'\n'
        self.assertEqual(pw.private_snapshot(model),407)  # Model only, NEVER live proof.
        root_only=RAW.splitlines();a,b=root_only[0].split(' - ');root_only[0]=' '.join(a.split()[:6])+' - '+b
        with self.assertRaises(sp.Rejected):pw.private_snapshot('\n'.join(root_only)+'\n')
        for flag in ('master:1','shared:2','propagate_from:3','unbindable','unknown:4'):
            with self.subTest(flag=flag),self.assertRaises(sp.Rejected):
                pw.private_snapshot(PRIVATE.replace(' rw - ',' rw '+flag+' - '))
    def test_cgroup_uid_and_each_namespace_fail_closed(self):
        for field in ('cgroup','uid','mnt','user','pid','net'):
            now=copy.deepcopy(ORIGIN);now['namespaces']={n:v+'new' for n,v in now['namespaces'].items()}
            if field=='cgroup':now[field]='/wrong.service'
            elif field=='uid':now[field]=0
            else:now['namespaces'][field]=ORIGIN['namespaces'][field]
            with self.subTest(field=field):self.run_gate(context=now)
    def test_dependency_failure_prevents_mount_read_and_exec(self):
        with patch.object(pw,'verify_dependencies',side_effect=sp.Rejected('binary changed')),patch.object(pw.os,'execv') as execute:
            with self.assertRaises(sp.Rejected):pw.gate('pre',ORIGIN,M['attempt_root'],[pw.BWRAP])
            execute.assert_not_called()
    def test_post_storage_failure_no_payload(self):
        now=copy.deepcopy(ORIGIN);now['namespaces']={n:v+'new' for n,v in now['namespaces'].items()}
        with patch.object(pw,'verify_dependencies'),patch.object(pw,'context',return_value=now),\
             patch.object(Path,'read_text',return_value=PRIVATE),patch.object(es,'check',side_effect=es.Rejected('outside RW')),\
             patch.object(pw.os,'execv') as execute,contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(es.Rejected):pw.gate('post',ORIGIN,M['attempt_root'],M['argv'])
            execute.assert_not_called()
    def test_post_changed_snapshot_no_payload(self):
        now=copy.deepcopy(ORIGIN);now['namespaces']={n:v+'new' for n,v in now['namespaces'].items()}
        with patch.object(pw,'verify_dependencies'),patch.object(pw,'context',return_value=now),\
             patch.object(Path,'read_text',side_effect=[PRIVATE,PRIVATE+'\n']),patch.object(es,'check',return_value={}),\
             patch.object(pw.os,'execv') as execute,contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(sp.Rejected):pw.gate('post',ORIGIN,M['attempt_root'],M['argv'])
            execute.assert_not_called()
    def test_exec_failure_propagates_without_retry(self):
        self.run_gate('pre',exec_error=OSError)
        self.assertEqual(sum(isinstance(x,tuple) for x in self.events),1)
    def test_single_id_maps_required(self):
        now=copy.deepcopy(ORIGIN)
        for n in ('mnt','user'):now['namespaces'][n]+='new'
        with patch.object(pw,'verify_dependencies'),patch.object(pw,'context',return_value=now),\
             patch.object(Path,'read_text',return_value='0 1000 1'),patch.object(pw.os,'execv') as execute:
            with self.assertRaises(sp.Rejected):pw.gate('pre',ORIGIN,M['attempt_root'],[pw.BWRAP])
            execute.assert_not_called()
    def test_no_missing_arg_fallback(self):
        for args in ([],['pre'],['post','{}','/attempt','/payload']):
            with self.assertRaises(sp.Rejected):pw.main(args)

class OwnedLedger(sa.Ledger):
    """Only test adaptation: validate real historical authority at real paths.
    The transaction and all writes still use this fixture's own state/lock.
    No phase, recovery event, snapshot, transition or join is rebound/fabricated.
    """
    def released(self,data):
        return tr.validate_state(data,self.recovery_pin,V4/'direct-state-v4.json',BASE/'capacity.lock')

class UnusedChain(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(dir=HERE,prefix='owner-test-');self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.count=0
        self.state=self.root/'state.json';self.state.write_text(json.dumps(LIVE));self.lock=self.root/'capacity.lock';self.lock.touch()
        identities={};self.identities=identities
        for rec in LIVE['lanes'].values():
            for name in ('root','old_volume','old_workspace','old_workspace_alias'):
                identities[rec['policy'][name]['path']]=rec['policy'][name]
        for r in LIVE['phases'].values():identities[r['attempt_identity']['path']]=r['attempt_identity']
        def space(p):
            for rec in LIVE['lanes'].values():
                if str(p)==rec['policy']['old_volume']['path']:return dict(free=10*sa.GIB,used=rec['policy']['historical_charge'])
            return dict(free=10**15,used=0)
        self.l=OwnedLedger(self.state,self.lock,recovery_pin=CONFIG['recovery_authority'],
            observe=lambda p:identities[str(p)],usage=lambda p:0,space=space)
        self.before=self.l.snapshot()
        self.mapped_root=self.root/'A';self.mapped_root.mkdir()
    def pin(self,obj):
        self.count+=1;p=self.root/('pin-'+str(self.count)+'.json');p.write_text(json.dumps(obj,sort_keys=True));return sc.pin(p)
    def transition(self,to='fresh-A-test'):
        data=self.l.snapshot();rec=data['lanes']['A']
        return dict(version=sa.VERSION,worker='A',coordinator=rec['policy']['coordinator'],policy=rec['pin'],
            previous=rec['transitions'][-1],from_owner=self.l.owner(data,'A'),to_owner=to,
            kind='unused-owner-revocation',unused_state=self.pin(data),phase_sequence=len(data['phases']))
    def rotate(self,t):
        p=self.pin(t)
        self.l.rotate_owner(p,verify_join=lambda *args:self.fail('UNUSED must not request or fabricate a join'))
        return p
    def reserve_A(self,owner):
        data=self.l.snapshot();rec=data['lanes']['A'];attempt='test-reserve-A'
        path=str(Path(rec['policy']['root']['path'])/attempt)
        (self.mapped_root/attempt).mkdir(exist_ok=True)
        self.identities[path]=dict(rec['policy']['root'],path=path,ino=123456)
        g=sp.pinned_json(data['phases'][tr.KEY]['grant'])
        g.update(worker='A',owner=owner,attempt=attempt,iteration=100,ram_peak_bytes=3*sa.GIB,
                 storage_policy=rec['pin'],owner_transition=rec['transitions'][-1],
                 predecessor_controller=rec['policy']['predecessor_controller'],
                 resource_ledger=rec['policy']['predecessor_ledger'],
                 controller=sc.pin(CODE/'storage_controller.py'),helpers=[sc.pin(CODE/n) for n in sc.HELPERS])
        gp=self.pin(g)
        m={k:g[k] for k in ('owner','worker','iteration','attempt','phase_scope','phase_bytes','ram_peak_bytes',
                           'timeout_seconds','source_commit','inputs','argv','controller')}
        m.update(grant=gp,attempt_root=path,cwd=path+'/work',tmpdir=path+'/tmp',cache=path+'/cache',
                 ccache=path+'/ccache',receipts=path+'/receipts',output_paths=[path+'/out'])
        mp=self.pin(m);directory=sp.directory
        def mapped(p):
            p=Path(p);root=Path(rec['policy']['root']['path'])
            return directory(self.mapped_root/p.relative_to(root) if p.is_relative_to(root) else p)
        with patch.object(sa,'directory',side_effect=mapped),patch.object(sp,'directory',side_effect=mapped):
            return self.l.reserve(gp,mp,current=lambda:dict(grant=gp,thread=owner,iteration=100),
                                  host=lambda data:(10*sa.GIB,0),custody=lambda *args:dict(
                                      controller=g['controller'],service_argv=['/mock/never-executed'],
                                      unit='mock-unused-admission.service',cgroup='/mock/unused-admission',
                                      identity=dict(pid=99999999,starttime=1,boot='mock',cgroup='/mock',argv=['/mock'])))
    def test_actual_admission_new_owner_and_phase_barrier(self):
        self.rotate(self.transition());self.reserve_A('fresh-A-test');data=self.l.snapshot()
        self.assertEqual(data['phases']['A:test-reserve-A']['sequence'],3)
        self.assertEqual(data['phases']['A:test-reserve-A']['owner'],'fresh-A-test')
        self.assertNotIn('join',data['phases']['A:test-reserve-A'])
        self.assertEqual(sum(r['phase_bytes'] for r in data['phases'].values()),16*2**20)
        self.assertEqual({k:v for k,v in data['phases'].items() if k!='A:test-reserve-A'},LIVE['phases'])
        with self.assertRaises(sp.Rejected):self.rotate(self.transition('another-owner'))
    def test_actual_admission_retired_owner_refused(self):
        retired=self.l.owner(LIVE,'A');self.rotate(self.transition());before=self.l.snapshot()
        with self.assertRaises(sp.Rejected):self.reserve_A(retired)
        self.assertEqual(self.l.snapshot(),before)
    def test_actual_current_chain_fixture_and_charge(self):
        self.assertEqual(self.before,LIVE)
        chain=self.before['lanes']['A']['transitions']
        self.assertEqual([sp.pinned_json(p)['kind'] for p in chain],['enrolled-unused','unused-owner-revocation'])
        self.assertEqual(self.l.owner(self.before,'A'),'01a14947-e352-78b3-b2fc-ee61a0ca0dc0')
        self.assertEqual(self.l.active_rows(self.before),[])
        self.assertFalse(any(r['worker']=='A' for r in LIVE['phases'].values()))
        self.assertEqual(len(LIVE['phases']),3);self.assertEqual(sum(r['phase_bytes'] for r in LIVE['phases'].values()),12*2**20)
    def test_installed_one_time_branch_rejects_actual_current_chain(self):
        tree=ast.parse((V5/'storage_admission.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Ledger')
        method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='rotate_owner');env=dict(sa.__dict__)
        exec(compile(ast.Module(body=[method],type_ignores=[]),'installed-v5','exec'),env)
        with self.assertRaisesRegex(sp.Rejected,'exact quiescent unused A only'):
            env['rotate_owner'](self.l,self.pin(self.transition()),verify_join=lambda *a:False)
        self.assertEqual(self.l.snapshot(),LIVE)
    def test_two_successive_fresh_rotations_only_append(self):
        expected=copy.deepcopy(LIVE)
        for owner in ('fresh-A-test','fresh-A-second-test'):
            p=self.rotate(self.transition(owner));expected['lanes']['A']['transitions'].append(p)
            self.assertEqual(self.l.snapshot(),expected);self.assertEqual(self.l.owner(expected,'A'),owner)
        self.assertEqual(self.l.active_rows(expected),[])
        self.assertEqual(sum(r['phase_bytes'] for r in expected['phases'].values()),12*2**20)
    def test_stale_replayed_transition_rejected(self):
        t=self.transition();self.rotate(t);after=self.l.snapshot()
        with self.assertRaises(sp.Rejected):self.rotate(t)
        self.assertEqual(self.l.snapshot(),after)
    def test_retired_and_reused_owner_rejected(self):
        rec=LIVE['lanes']['A'];owners=[rec['policy']['owner']]+[sp.pinned_json(p)['to_owner'] for p in rec['transitions']]
        for owner in owners:
            with self.subTest(owner=owner),self.assertRaises(sp.Rejected):self.rotate(self.transition(owner))
        self.assertEqual(self.l.snapshot(),LIVE)
    def test_wrong_authority_previous_join_and_barrier_rejected(self):
        for k,v in (('coordinator','wrong'),('worker','F'),('from_owner','stale'),('to_owner',''),
                    ('previous',None),('policy',LIVE['lanes']['F']['pin']),('phase_sequence',2),
                    ('phase_sequence',True),('phase_sequence',4),('prior_join',{}),('prior_phase','fake'),('recovery_event','fake')):
            with self.subTest(field=k):
                t=self.transition();t[k]=v
                with self.assertRaises((sp.Rejected,KeyError)):self.rotate(t)
                self.assertEqual(self.l.snapshot(),LIVE)
    def test_stale_full_snapshot_after_other_lane_change(self):
        t=self.transition();bad=copy.deepcopy(LIVE);bad['lanes']['F']['transitions']=bad['lanes']['F']['transitions'][:-1]
        t['unused_state']=self.pin(bad)
        with self.assertRaises(sp.Rejected):self.rotate(t)
        self.assertEqual(self.l.snapshot(),LIVE)
    def test_snapshot_pin_tamper_rejected(self):
        t=self.transition();Path(t['unused_state']['path']).write_text('{}')
        with self.assertRaises(sp.Rejected):self.rotate(t)
        self.assertEqual(self.l.snapshot(),LIVE)
    def test_active_either_lane_and_used_A_rejected(self):
        for lane,used in (('F',False),('A',False),('A',True)):
            data=copy.deepcopy(LIVE);row=copy.deepcopy(data['phases']['F:live09-f-success-01'])
            row.update(worker=lane,owner=self.l.owner(data,lane),sequence=3)
            if not used:row.pop('join');row['stage']='reserved'
            # Explicit negative model row only; NEVER serialized as live proof.
            data['phases'][lane+':negative-model']=row
            self.state.write_text(json.dumps(data));t=self.transition()
            with self.assertRaises(sp.Rejected):self.rotate(t)
            self.assertEqual(self.l.snapshot(),data)
            self.state.write_text(json.dumps(LIVE))
    def test_history_charge_or_recovery_rewrite_reader_rejected(self):
        self.rotate(self.transition());base=self.l.snapshot()
        for change in ('charge','history','recovery','F-chain'):
            data=copy.deepcopy(base)
            if change=='charge':data['phases']['F:live09-f-success-01']['phase_bytes']-=1
            elif change=='history':del data['phases']['F:live07-f-success-01']
            elif change=='recovery':data['recovery_events'][0]['ram_released']=0
            else:data['lanes']['F']['transitions'].pop()
            with self.subTest(change=change),self.assertRaises((sp.Rejected,KeyError)):
                self.l.owner(data,'A')
    def test_future_phase_barrier_and_revoked_owner(self):
        self.rotate(self.transition());base=self.l.snapshot()
        for owner,seq in (('fresh-A-test',2),('01a14947-e352-78b3-b2fc-ee61a0ca0dc0',3),('01a14932-e9b3-7a33-bff0-0486c870eed7',3)):
            data=copy.deepcopy(base);row=copy.deepcopy(data['phases']['F:live09-f-success-01']);row.update(worker='A',owner=owner,sequence=seq)
            data['phases']['A:negative-model']=row
            with self.assertRaises(sp.Rejected):self.l.owner(data,'A')
        data=copy.deepcopy(base);row=copy.deepcopy(data['phases']['F:live09-f-success-01']);row.update(worker='A',owner='fresh-A-test',sequence=3,stage='reserved');row.pop('join');row.pop('inner_result',None)
        data['phases']['A:positive-reader-model']=row
        self.assertEqual(self.l.owner(data,'A'),'fresh-A-test')
    def test_F_uses_real_latest_join_callback_never_UNUSED(self):
        rec=LIVE['lanes']['F'];row=LIVE['phases']['F:live09-f-success-01']
        t=dict(version=sa.VERSION,worker='F',coordinator=rec['policy']['coordinator'],policy=rec['pin'],
               previous=rec['transitions'][-1],from_owner=self.l.owner(LIVE,'F'),to_owner='fresh-F-model',kind='joined',
               prior_phase='F:live09-f-success-01',prior_join=row['join'])
        seen=[]
        def refuse(r,receipt):
            self.assertEqual(r,row);self.assertEqual(receipt,sp.pinned_json(row['join']));seen.append(r);return False
        with self.assertRaisesRegex(sp.Rejected,'independently authenticated'):
            self.l.rotate_owner(self.pin(t),verify_join=refuse)
        self.assertEqual(len(seen),1);self.assertEqual(self.l.snapshot(),LIVE)

class ExactSources(unittest.TestCase):
    def test_preserved_helpers_and_effective_checker_byte_exact(self):
        for name in ('storage_paths.py','terminal_recovery.py'):
            self.assertEqual((CODE/name).read_bytes(),(V5/name).read_bytes())
        self.assertEqual((CODE/'effective_storage.py').read_bytes(),(HERE.parent/'storage-mount-repair-08/effective_storage.py').read_bytes())
    def test_only_scoped_methods_change(self):
        def nodes(p):
            result={}
            for n in ast.parse(p.read_text()).body:
                if isinstance(n,ast.FunctionDef):result[n.name]=ast.dump(n)
                elif isinstance(n,ast.ClassDef):
                    for m in n.body:
                        if isinstance(m,ast.FunctionDef):result[n.name+'.'+m.name]=ast.dump(m)
            return result
        for name,allowed in [('storage_controller.py',{'sandbox','Controller.current','Controller.inner'}),
                             ('storage_admission.py',{'Ledger.owner','Ledger.rotate_owner'})]:
            old,new=nodes(V5/name),nodes(CODE/name)
            self.assertEqual(set(old),set(new));self.assertEqual({n for n in old if old[n]!=new[n]},allowed)
        self.assertEqual(sc.STATE_HOME,sc.HERE.parent/'storage-direct-v4')
    def test_config_preserves_exact_oldv5_v4_v2_authorities(self):
        old=json.loads((V5/'runtime-config.json').read_text());new=copy.deepcopy(CONFIG)
        bundle=new['preserved_record_authorities'].pop();self.assertEqual(new,old)
        self.assertEqual(bundle,json.loads((HERE/'preserve-v5-record-authority.json').read_text()))
        self.assertEqual([Path(b['controller']['path']).parent.name for b in CONFIG['preserved_record_authorities']],
                         ['storage-direct-v2','storage-direct-v4','storage-direct-v5'])
    def test_every_historical_phase_bundle_authenticates_and_partial_rejected(self):
        c=sc.Controller.__new__(sc.Controller);c.config_pin=sc.pin(CODE/'runtime-config.json');c.config=CONFIG
        for row in LIVE['phases'].values():c.authenticate_record_sources(row)
        row=LIVE['phases']['F:live09-f-success-01'];bad=copy.deepcopy(CONFIG);bad['preserved_record_authorities'][-1]['helpers'].pop();c.config=bad
        with self.assertRaises(sp.Rejected):c.authenticate_record_sources(row)
    def test_installed_binaries_and_grant_contract(self):
        # Deployment is intentionally absent; validate unchanged installed binaries
        # and the pinned source bytes of the proposed dedicated unshare copy.
        for p in pw.BINARIES:
            path=Path('/usr/bin/unshare') if p['path']==pw.UNSHARE else Path(p['path'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),p['sha256'])
        self.assertEqual(pw.BINARIES,json.loads((HERE/'binary-contract.json').read_text()))
        src=(CODE/'storage_controller.py').read_text()
        self.assertIn("all(p in g['inputs'] for p in private_workload.BINARIES)",src)
        self.assertEqual(sc.HELPERS[-2:],('private_workload.py','effective_storage.py'))
    def test_unshare_exact_source_order_and_fatal_failure(self):
        s=(HERE.parent/'storage-propagation-repair-10/sources/ubuntu-unshare.c').read_text()
        self.assertIn('{ "private",\tMS_REC | MS_PRIVATE }',s)
        for x in ('mapuser = real_euid;', 'mapgroup = real_egid;', 'int c, forkit = 0;',
                  'if (usermap || groupmap)', 'if (npersists && (unshare_flags & (CLONE_NEWNS | CLONE_NEWUSER)))',
                  'if (forkit)', 'if (-1 == unshare(unshare_flags))',
                  'err(EXIT_FAILURE, _("unshare failed"))', 'execvp(argv[optind], argv + optind)'):
            self.assertIn(x,s)
        self.assertLess(s.index('if (-1 == unshare(unshare_flags))'),s.index('set_propagation(propagation)'))
        self.assertLess(s.index('set_propagation(propagation)'),s.index('execvp(argv[optind]'))
        self.assertIn('if (mount("none", "/", NULL, flags, NULL) != 0)',s)
        self.assertIn('err(EXIT_FAILURE, _("cannot change root filesystem propagation"))',s)
        b=(HERE.parent/'storage-propagation-repair-10/sources/ubuntu-bubblewrap.c').read_text()
        self.assertIn('MS_SILENT | MS_SLAVE | MS_REC',b)
        self.assertIn('else if (real_uid != 0 && has_caps ())',b)
        self.assertIn('if (usermap || (mapuser != (uid_t) -1 && owneruser != (uid_t) -1))',s)
        self.assertIn('uid_t mapuser = -1, owneruser = -1;',s)
        self.assertTrue((HERE.parent/'storage-propagation-repair-10/sources/ubuntu-util-linux-changelog').read_text().startswith('util-linux (2.41.3-3ubuntu2.2)'))
        self.assertTrue((HERE.parent/'storage-propagation-repair-10/sources/ubuntu-bubblewrap-changelog').read_text().startswith('bubblewrap (0.11.1-1ubuntu0.3)'))
        self.assertIn('drop_privs (!is_privileged, true, true)',b)
        kernel=(HERE.parent/'storage-propagation-repair-10/sources/sharedsubtree.rst').read_text()
        self.assertIn('** slaving a non-shared mount has no effect on the mount.',kernel)
    def test_input_pins_unchanged(self):
        for p in json.loads((HERE/'sourcepins.json').read_text()):
            self.assertEqual(hashlib.sha256(Path(p['path']).read_bytes()).hexdigest(),p['sha256'],p['path'])

class ControllerCustody(unittest.TestCase):
    def test_mock_unshare_setup_failure_is_waited_recorded_no_retry(self):
        for code in (1,124,126):
            with self.subTest(exit=code),tempfile.TemporaryDirectory(dir=HERE,prefix='custody-test-') as temp:
                c=sc.Controller.__new__(sc.Controller);c.current=Mock();c.key='F:test'
                c.config={'lane_cgroups':{'F':'/parent'}}
                c.g=dict(worker='F',attempt='test',owned_processes={'path':'/never-executed'},timeout_seconds=7)
                c.m=dict(M,receipts=temp,tmpdir=temp,cache=temp,ccache=temp,inputs=[])
                c.ledger=Mock();child=object();tracked=[dict(pid=99999999,starttime=123)]
                joined=dict(tracked=tracked,remaining_identities=[])
                cleanup=types.SimpleNamespace(enable_subreaper=Mock(),wait_owned=Mock(return_value=(code,joined)))
                spec=types.SimpleNamespace(loader=types.SimpleNamespace(exec_module=lambda m:None))
                with patch.object(pw,'policy_gate',return_value={'mock':True}),patch.object(sc.importlib.util,'spec_from_file_location',return_value=spec),\
                     patch.object(sc.importlib.util,'module_from_spec',return_value=cleanup),\
                     patch.object(pw,'context',return_value=ORIGIN),patch.object(sc.subprocess,'Popen',return_value=child) as launch:
                    self.assertEqual(c.inner(),code)
                launch.assert_called_once();self.assertEqual(launch.call_args.args[0],pw.command(c.m,ORIGIN))
                self.assertTrue(launch.call_args.kwargs['start_new_session'])
                self.assertIs(cleanup.wait_owned.call_args.args[0],child)
                self.assertEqual(cleanup.wait_owned.call_args.args[1],7)
                self.assertTrue(callable(cleanup.wait_owned.call_args.kwargs['guard']))
                result=c.ledger.finish_service.call_args.args[1]
                self.assertEqual(result['tracked'],tracked);self.assertEqual(result['sandbox_argv'],pw.command(c.m,ORIGIN))
                self.assertEqual(result['exit'],code);self.assertEqual(result['remaining_identities'],[])

if __name__=='__main__': unittest.main(verbosity=2)
