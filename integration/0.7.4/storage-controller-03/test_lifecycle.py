"""Small mocked lifecycle: real flock/fsync/state, no systemd/bwrap/compiler launches."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import storage_controller as sc
from storage_admission import GIB, VERSION
from storage_paths import Rejected
from test_core_regression import Fixture

HERE = Path(__file__).resolve().parent


class FakeLinux:
    def __init__(self):
        self.props = dict(LoadState='not-found', MainPID='0', ActiveState='inactive', ControlGroup='', InvocationID='')
        self.command = []
        self.is_empty = True
        self.workers = set(); self.legacy = set()
        self.restored = False

    def show(self, unit): return dict(self.props)
    def argv(self, unit): return list(self.command)
    def empty(self, cg): return self.is_empty
    def profile(self, r, g, props): pass  # kernel limits separately inspected via mocked filesystem test
    def restore_high(self, r, g): self.restored = True
    def units(self, pattern): return self.legacy if pattern == 'vkfs0-*.service' else self.workers


class Harness:
    def __init__(self, base, ram=3*GIB):
        self.f = f = Fixture(base); f.enroll(); f.request()
        g,m,_,_,e = f.requests['A']
        self.config = dict(coordinator='coordinator',lane_cgroups={'A':'/mock/vkfworkers-a.slice'})
        cp = f.pin('config', self.config)
        g.update(controller=sc.pin(HERE/'storage_controller.py'), helpers=[sc.pin(HERE/n) for n in sc.HELPERS],
                 runtime_config=cp, ram_peak_bytes=ram)
        gp=f.pin('grant-v2',g); m.update(grant=gp,controller=g['controller'],ram_peak_bytes=ram)
        mp=f.pin('manifest-v2',m); e=dict(e,grant=gp); f.requests['A']=(g,m,gp,mp,e)
        c=self.c=sc.Controller.__new__(sc.Controller)
        c.a=SimpleNamespace(config_sha256=cp['sha256'],grant=Path(gp['path']),grant_sha256=gp['sha256'],
                            manifest=Path(mp['path']),manifest_sha256=mp['sha256'])
        c.config_pin=cp;c.config=self.config;c.gp=gp;c.mp=mp;c.g=g;c.m=m;c.ledger=f.ledger;c.key='A:attempt1'
        c.os=FakeLinux();c.current=lambda:e;c.host=lambda data:(30*GIB,0)
        self.outer=dict(pid=77,starttime=100,boot='boot',cgroup='/outer',argv=['outer'])
        self.inner=dict(pid=os.getpid(),starttime=101,boot='boot',
                        cgroup='/mock/vkfworkers-a.slice/vkfworkers-a-attempt1.service',argv=c.service_argv())
        self.live={77:self.outer}
        c.custody=lambda g,m:dict(identity=self.outer,unit='vkfworkers-a-attempt1.service',
                    service_argv=c.service_argv(),cgroup=self.inner['cgroup'],controller=g['controller'],config=cp)

    def activate(self):
        c=self.c; self.live[self.inner['pid']]=self.inner
        c.os.props=dict(LoadState='loaded',MainPID=str(self.inner['pid']),ActiveState='active',
                        ControlGroup=self.inner['cgroup'],InvocationID='invocation-1')
        c.os.command=c.service_argv(); c.os.is_empty=False
        c.ledger.attach_service(c.key,authenticate=c.attach)

    def finish(self, exitcode=0):
        c=self.c
        result=dict(exit=exitcode,tracked=[dict(pid=333,starttime=123)],remaining_identities=[],inputs_reverified=True)
        c.ledger.finish_service(c.key,result,authenticate=c.authenticate)
        del self.live[self.inner['pid']]
        c.os.props.update(MainPID='0',ActiveState='failed',Result='exit-code',ExecMainCode='1',ExecMainStatus=str(sc.CUSTODY_EXIT))
        c.os.is_empty=True

    def execute(self, argv, timeout, **streams):
        c=self.c;r=c.ledger.snapshot()['phases'][c.key]
        assert r['stage']=='launch_claimed' and r['ram_bytes']==c.g['ram_peak_bytes']
        assert r['custody']['service_argv']==argv[argv.index('--')+1:]
        self.activate();self.finish()
        return SimpleNamespace(returncode=sc.CUSTODY_EXIT)

    def receipt(self):
        c=self.c;r=c.ledger.snapshot()['phases'][c.key]
        return dict(grant=c.gp,manifest=c.mp,custody=r['custody'],service=r['service'],
                    inner_result=r['inner_result'],main_pid=0,cgroup_empty=True,
                    remaining_identities=[],actual_service_joined=True)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='lifecycle-',dir=HERE);self.addCleanup(self.tmp.cleanup)
        self.h=Harness(self.tmp.name);self.c=self.h.c
        p=patch.object(sc,'proc',side_effect=lambda pid:self.h.live.get(pid));p.start();self.addCleanup(p.stop)

    def reserve(self):
        c=self.c
        return c.ledger.reserve(c.gp,c.mp,current=c.current,host=c.host,custody=c.custody)

    def claimed(self):
        self.reserve();self.c.ledger.claim_launch(self.c.key,authenticate=self.c.authenticate,host=self.c.host)

    def test_outer_success_commits_before_exec_joins_and_retains_charge(self):
        with patch.object(sc.subprocess,'run',side_effect=self.h.execute) as run:
            self.assertEqual(self.c.outer(),0)
        self.assertEqual(run.call_count,1)
        self.assertEqual(json.loads((Path(self.c.m['receipts'])/'service-join.json').read_text())['outer_exit'],sc.CUSTODY_EXIT)
        r=self.c.ledger.snapshot()['phases'][self.c.key]
        self.assertEqual((r['stage'],r['phase_bytes'],r['ram_bytes']),('joined',100000,3*GIB))
        self.assertTrue(self.c.os.restored)
        with patch.object(sc.subprocess,'run') as run,self.assertRaisesRegex(Rejected,'permanently charged'):
            self.c.outer()
        run.assert_not_called()

    def test_crash_after_atomic_commit_retains_custody_and_ram(self):
        self.reserve()
        r=self.h.f.open().snapshot()['phases'][self.c.key]
        self.assertEqual(r['custody']['identity'],self.h.outer)
        self.assertEqual(r['phase_bytes'],100000);self.assertEqual(r['ram_bytes'],3*GIB)
        with self.assertRaisesRegex(Rejected,'permanently charged'):self.reserve()

    def test_claim_crash_cannot_relaunch_and_no_inner_without_claim(self):
        self.reserve()
        with self.assertRaisesRegex(Rejected,'unclaimed'):
            self.c.ledger.attach_service(self.c.key,authenticate=self.c.attach)
        self.c.ledger.claim_launch(self.c.key,authenticate=self.c.authenticate,host=self.c.host)
        with self.assertRaisesRegex(Rejected,'already claimed'):
            self.c.ledger.claim_launch(self.c.key,authenticate=self.c.authenticate,host=self.c.host)

    def test_receipt_failure_before_exec_and_after_join_keeps_reservation(self):
        original=self.c.write_receipt
        with (patch.object(self.c,'write_receipt',side_effect=OSError('receipt fault')),
              patch.object(sc.subprocess,'run') as run):
            with self.assertRaises(OSError):self.c.outer()
        run.assert_not_called()
        self.assertEqual(self.c.ledger.snapshot()['phases'][self.c.key]['stage'],'launch_claimed')
        # Model a separately completed service without retrying outer/launch claim.
        self.h.activate();self.h.finish()
        with patch.object(self.c,'write_receipt',side_effect=OSError('final receipt fault')):
            with self.assertRaises(OSError):self.c.write_receipt('service-join.json',self.h.receipt())
        self.assertNotIn('join',self.c.ledger.snapshot()['phases'][self.c.key])

    def test_timeout_is_failure_but_independently_joined_ram_can_release(self):
        self.claimed();self.h.activate();self.h.finish(124)
        rp=self.h.f.pin('timeout-join',self.h.receipt())
        self.c.ledger.join(self.c.key,rp,verify_join=self.c.verify_join)
        r=self.c.ledger.snapshot()['phases'][self.c.key]
        self.assertEqual(r['inner_result']['exit'],124);self.assertEqual(r['phase_bytes'],100000)

    def test_ambiguous_service_cgroup_pid_invocation_or_argv_never_releases(self):
        self.claimed();self.h.activate();self.h.finish()
        r=self.c.ledger.snapshot()['phases'][self.c.key];receipt=self.h.receipt()
        for field,value in [('MainPID','12'),('ActiveState','active'),('InvocationID','reused'),('ControlGroup','/wrong'),('ExecMainStatus','0'),('Result','success')]:
            with self.subTest(field=field),patch.dict(self.c.os.props,{field:value}),self.assertRaises(Rejected):
                self.c.verify_join(r,receipt)
        self.c.os.is_empty=False
        with self.assertRaisesRegex(Rejected,'terminal'):self.c.verify_join(r,receipt)
        self.c.os.is_empty=True;self.h.live[333]=dict(pid=333,starttime=123,boot='boot')
        with self.assertRaisesRegex(Rejected,'owned PID'):self.c.verify_join(r,receipt)
        del self.h.live[333];self.c.os.command+=['injected']
        with self.assertRaisesRegex(Rejected,'ExecStart'):self.c.verify_join(r,receipt)
        self.assertNotIn('join',self.c.ledger.snapshot()['phases'][self.c.key])

    def test_runtime_guard_rechecks_owner_sources_and_one_gib_floor(self):
        self.claimed();self.h.activate()
        self.c.ledger.guard_service(self.c.key,authenticate=self.c.authenticate,host=lambda d:(GIB,0))
        with self.assertRaisesRegex(Rejected,'emergency'):
            self.c.ledger.guard_service(self.c.key,authenticate=self.c.authenticate,host=lambda d:(GIB-1,0))
        with patch.object(self.c,'current',side_effect=Rejected('owner changed')),self.assertRaisesRegex(Rejected,'owner changed'):
            self.c.ledger.guard_service(self.c.key,authenticate=self.c.authenticate,host=self.c.host)
        self.assertNotIn('join',self.c.ledger.snapshot()['phases'][self.c.key])

    def test_preexec_floor_and_source_change_prevents_exec(self):
        self.claimed()
        with self.assertRaisesRegex(Rejected,'RAM floor'):
            self.c.ledger.preexec(self.c.key,authenticate=self.c.authenticate,host=lambda d:(5*GIB-1,0))
        Path(self.c.mp['path']).write_text('changed')
        with self.assertRaisesRegex(Rejected,'source pin'):
            self.c.ledger.preexec(self.c.key,authenticate=self.c.authenticate,host=self.c.host)

    def test_owner_rotation_requires_latest_authenticated_join_keeps_history(self):
        self.claimed();self.h.activate();self.h.finish()
        f=self.h.f;c=self.c;rp=f.pin('join',self.h.receipt());c.ledger.join(c.key,rp,verify_join=c.verify_join)
        before=c.ledger.snapshot()
        t=dict(version=VERSION,worker='A',coordinator='coordinator',policy=f.policies['A'][1],
               previous=None,from_owner='owner-A',to_owner='fresh-chat',prior_phase=c.key,prior_join=rp)
        tp=f.pin('transition',t)
        with self.assertRaisesRegex(Rejected,'independently'):
            c.ledger.rotate_owner(tp,verify_join=lambda r,j:False)
        c.ledger.rotate_owner(tp,verify_join=c.verify_join)
        after=c.ledger.snapshot()
        self.assertEqual(before['phases'],after['phases']);self.assertEqual(before['lanes']['A']['policy'],after['lanes']['A']['policy'])
        self.assertEqual(after['lanes']['A']['transitions'],[tp])
        f.request(attempt='attempt2')
        g,m,_,_,e=f.requests['A'];g.update(owner='fresh-chat',owner_transition=tp)
        gp=f.pin('fresh-grant',g);m.update(owner='fresh-chat',grant=gp);mp=f.pin('fresh-manifest',m)
        e.update(thread='fresh-chat',grant=gp)
        c.ledger.reserve(gp,mp,current=lambda:e,host=lambda d:(20*GIB,0),custody=f.custody)
        after=c.ledger.snapshot();self.assertEqual(sum(r['phase_bytes'] for r in after['phases'].values()),200000)
        self.assertEqual(after['phases'][c.key],before['phases'][c.key])
        with self.assertRaises(Rejected):c.ledger.rotate_owner(tp,verify_join=c.verify_join)

    def test_rotation_outstanding_or_wrong_anchor_rejected(self):
        self.reserve();f=self.h.f
        t=dict(version=VERSION,worker='A',coordinator='coordinator',policy=f.policies['A'][1],
               previous=None,from_owner='owner-A',to_owner='fresh',prior_phase=self.c.key,prior_join={})
        with self.assertRaisesRegex(Rejected,'outstanding'):
            self.c.ledger.rotate_owner(f.pin('transition',t),verify_join=lambda r,j:True)
        self.assertEqual(self.c.ledger.snapshot()['lanes']['A']['transitions'],[])

    def test_combined_registry_unknown_worker_and_offload_and_live_legacy(self):
        c=self.c;f=self.h.f
        c.config['legacy_registry']=f.pin('registry',{})
        continuation=f.pin('phase',{'script_sha256':'unused'})
        offload=f.pin('adopted',{'service':'vkfs0-offload.service','continuation_manifest':continuation})
        c.config['adopted_offload']=offload
        c.os.workers={'vkfworkers-unreserved.service'}
        with self.assertRaisesRegex(Rejected,'unreserved'):
            sc.Controller.host(c,c.ledger.snapshot())
        c.os.workers=set()
        oldg=dict(c.g,controller=dict(c.g['controller']))
        oldg['controller']['sha256']=sc.PREDECESSORS[3*GIB][1]
        ogp=f.pin('old-grant',oldg);omp=f.pin('old-manifest',dict(c.m,grant=ogp,controller=oldg['controller']))
        c.config['legacy_registry']=f.pin('registry',{'A':dict(grant=ogp,manifest=omp,identity=self.h.outer,unit='old.service')})
        with patch.object(sc,'pinned',return_value=b''),self.assertRaisesRegex(Rejected,'legacy custody'):
            sc.Controller.host(c,c.ledger.snapshot())

    def test_combined_registry_tampered_entry_and_service_identity(self):
        self.claimed();self.h.activate();r=self.c.ledger.snapshot()['phases'][self.c.key]
        for key,value in [('unit','wrong.service'),('service_argv',['arbitrary']),('cgroup','/wrong')]:
            bad=copy.deepcopy(r);bad['custody'][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(Rejected,'combined registry'):
                self.c.authenticate_record(bad)
        self.h.inner['starttime']+=1
        with self.assertRaisesRegex(Rejected,'identity replaced'):self.c.authenticate_record(r)

    def test_sandbox_and_service_profiles_are_exact(self):
        argv=sc.sandbox(self.c.m);self.assertEqual(argv.count('--bind'),1)
        i=argv.index('--bind');self.assertEqual(argv[i+1:i+3],[self.c.m['attempt_root']]*2)
        for flag in ('--unshare-pid','--unshare-net','--die-with-parent'):self.assertIn(flag,argv)
        self.assertEqual(argv[-len(self.c.m['argv']):],self.c.m['argv'])
        self.reserve();r=self.c.ledger.snapshot()['phases'][self.c.key]
        for ram in (3*GIB,8*GIB):
            command=sc.run_command(r,dict(self.c.g,ram_peak_bytes=ram))
            for arg in [f'--property=MemoryMax={ram//GIB}G','--property=MemorySwapMax=0','--property=TasksMax=128',
                        '--property=KillMode=control-group','--property=OOMPolicy=kill','--property=TimeoutStopSec=10s']:
                self.assertIn(arg,command)
            self.assertNotIn('--collect',command)


    def test_inner_timeout_and_guard_use_owned_cleanup_without_releasing_ram(self):
        # Exercise the actual inner method with a fake Popen and cleanup module.
        self.claimed();c=self.c;h=self.h
        for name in ('cwd','tmpdir','cache','ccache','receipts'):
            Path(c.m[name]).mkdir(parents=True,exist_ok=True)
        h.live[h.inner['pid']]=h.inner
        c.os.props=dict(LoadState='loaded',MainPID=str(h.inner['pid']),ActiveState='active',
                        ControlGroup=h.inner['cgroup'],InvocationID='invocation-1')
        c.os.command=c.service_argv();c.os.is_empty=False
        events=[]
        def wait(child, timeout, guard):
            self.assertEqual(timeout,30)
            c.host=lambda data:(GIB-1,0)
            try:guard()
            except Rejected as exc:events.append(str(exc))
            return 126,dict(tracked=[dict(pid=333,starttime=123)],remaining_identities=[],guard_error=events[-1])
        cleanup=SimpleNamespace(enable_subreaper=lambda:events.append('subreaper'),wait_owned=wait)
        spec=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module:None))
        with (patch.object(sc.importlib.util,'spec_from_file_location',return_value=spec),
              patch.object(sc.importlib.util,'module_from_spec',return_value=cleanup),
              patch.object(sc.subprocess,'Popen',return_value=SimpleNamespace(pid=333)) as popen):
            self.assertEqual(c.inner(),126)
        self.assertEqual(events[0],'subreaper');self.assertIn('emergency',events[1])
        self.assertEqual(popen.call_args.args[0],sc.sandbox(c.m))
        r=c.ledger.snapshot()['phases'][c.key]
        self.assertEqual(r['stage'],'inner_finished');self.assertNotIn('join',r)
        self.assertEqual(r['inner_result']['exit'],126)

    def test_kernel_profile_validation_both_profiles_and_high_restore(self):
        self.reserve();r=self.c.ledger.snapshot()['phases'][self.c.key];linux=sc.Linux()
        cg=Path('/sys/fs/cgroup')/r['custody']['cgroup'].lstrip('/')
        for ram in (3*GIB,8*GIB):
            props=dict(MemoryMax=str(ram),MemorySwapMax='0',TasksMax='128',KillMode='control-group',OOMPolicy='kill')
            values={cg/'memory.max':str(ram),cg/'memory.swap.max':'0',cg/'pids.max':'128',
                    cg.parent/'memory.max':str(ram),cg.parent/'memory.swap.max':'0',
                    cg.parent.parent/'memory.max':str(21*GIB),cg.parent.parent/'memory.swap.max':'0',
                    cg.parent/'memory.high':str(7*GIB)}
            def read(path,*args,**kwargs):return values[path]
            g=dict(self.c.g,ram_peak_bytes=ram)
            with patch.object(Path,'read_text',read):
                linux.profile(r,g,props)
                for path in (cg/'memory.max',cg/'memory.swap.max',cg/'pids.max',cg.parent.parent/'memory.max'):
                    original=values[path];values[path]='999'
                    with self.assertRaisesRegex(Rejected,'hierarchy'):linux.profile(r,g,props)
                    values[path]=original
                if ram==8*GIB:
                    values[cg.parent/'memory.high']=str(3*GIB)
                    with self.assertRaisesRegex(Rejected,'active memory.high'):linux.profile(r,g,props)
                    with patch.object(linux,'output',return_value='') as command:
                        linux.restore_high(r,g)
                    self.assertIn('MemoryHigh=3G',command.call_args.args[0])

    def test_outer_transport_timeout_retains_full_reservation(self):
        with patch.object(sc.subprocess,'run',side_effect=subprocess.TimeoutExpired(['mock'],90)):
            with self.assertRaises(subprocess.TimeoutExpired):self.c.outer()
        r=self.c.ledger.snapshot()['phases'][self.c.key]
        self.assertEqual(r['stage'],'launch_claimed');self.assertNotIn('join',r)
        self.assertEqual(r['phase_bytes'],100000)


    def test_precharge_files_rejected_and_no_log_or_launch(self):
        (Path(self.c.m['attempt_root'])/'premature').write_text('unreserved bytes')
        with patch.object(sc.subprocess,'run') as run,self.assertRaisesRegex(Rejected,'empty before charge'):
            self.c.outer()
        run.assert_not_called();self.assertEqual(self.c.ledger.snapshot()['phases'],{})

    def test_offload_remaining_and_unknown_legacy_service(self):
        c=self.c;f=self.h.f
        c.config['legacy_registry']=f.pin('registry',{})
        script=f.base/'offload.py';script.write_text('inert')
        phase=f.pin('continuation',dict(script_sha256=sc.pin(script)['sha256']))
        ident=dict(pid=77,starttime=100,boot='boot',cgroup='/outer',argv=['outer'])
        c.config['adopted_offload']=f.pin('offload',dict(service='vkfs0-offload.service',
            continuation_manifest=phase,main_identity=ident,service_properties={'ControlGroup':'/outer'}))
        c.os.props.update(MainPID='77',ActiveState='active',ControlGroup='/outer');c.os.command=['outer']
        with patch.object(sc,'mem',return_value=9*GIB),patch.object(sc,'resident',return_value=GIB):
            self.assertEqual(sc.Controller.host(c,c.ledger.snapshot()),(9*GIB,2*GIB))
            c.os.legacy={'vkfs0-unknown.service'}
            with self.assertRaisesRegex(Rejected,'unknown legacy demand'):sc.Controller.host(c,c.ledger.snapshot())


    def test_cli_inner_uses_retention_status_not_workload_status(self):
        c=self.c
        argv=['controller','--config-sha256',c.a.config_sha256,
              '--grant',str(c.a.grant),'--grant-sha256',c.a.grant_sha256,
              '--manifest',str(c.a.manifest),'--manifest-sha256',c.a.manifest_sha256,'--inside-service']
        for workload in (0,124,126):
            with patch.object(sc.sys,'argv',argv),patch.object(sc,'Controller',return_value=c),patch.object(c,'inner',return_value=workload):
                self.assertEqual(sc.main(),sc.CUSTODY_EXIT)

    def test_busctl_argv_preserves_spaces_and_rejects_multiple_commands(self):
        linux=sc.Linux();argv=['/usr/bin/python3','/a path/controller.py','--x','a b']
        values=[json.dumps(dict(type='o',data=['/unit'])),
                json.dumps(dict(type='a(sasbttttuii)',data=[[[argv[0],argv,False,0,0,0,0,0,0,0]]]))]
        with patch.object(linux,'output',side_effect=values):self.assertEqual(linux.argv('unit'),argv)
        data=json.loads(values[1]);data['data'][0]*=2
        with patch.object(linux,'output',side_effect=[values[0],json.dumps(data)]),self.assertRaises(Rejected):linux.argv('unit')


if __name__=='__main__':unittest.main(verbosity=2)
