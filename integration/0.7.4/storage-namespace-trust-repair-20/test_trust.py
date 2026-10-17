"""Host read-only and injected-model tests. No namespaces/exec/capability/service operations."""
import ast, contextlib, copy, errno, hashlib, importlib.util, io, json, os
from pathlib import Path
import stat, sys, unittest
from unittest.mock import patch
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'proposed'))
import private_workload as p
from storage_paths import Rejected


def fixture():
    paths = sorted({str(q) for pin in p.BINARIES+p.POLICY_INPUTS for q in (Path(pin['path']),*Path(pin['path']).parents)})
    files = {pin['path']:dict(sha256=pin['sha256'],filecaps=False) for pin in p.BINARIES+p.POLICY_INPUTS}
    rows = {}
    for i, path in enumerate(paths):
        rows[path] = dict(st_dev=1,st_ino=10+i,st_mode=(stat.S_IFREG|0o644 if path in files else stat.S_IFDIR|0o755),
            st_uid=0,st_gid=0,st_nlink=1 if path in files else 2,st_size=10,st_mtime_ns=100,st_ctime_ns=100)
    return dict(paths=rows,files=files,errors=[],root_mount=dict(id=10,path='/',root='/',dev=[0,1],fstype='ext4',options=['ro'],optional=[],readonly=True))


def origin():
    return dict(uid=1000,gid=1000,cgroup='/lane/test.service',boot='boot',overflow=dict(uid=65534,gid=65534),
        namespaces={n:n+':['+str(i+10)+']' for i,n in enumerate(p.NS_NAMES)},
        maps=dict(uid='0 0 4294967295\n',gid='0 0 4294967295\n'))


def ctx(stage):
    x=origin()
    for n in p.NS_NAMES:
        if n in ('user','mnt') or stage=='post' and n in ('pid','net'):
            x['namespaces'][n]=n+':['+str((100 if stage=='pre' else 200)+p.NS_NAMES.index(n))+']'
    x['maps']={k:('1000 1000 1\n' if stage=='pre' else '1000 0 1\n') for k in ('uid','gid')}
    return x


def projected(host, stage):
    x=copy.deepcopy(host)
    for row in x['paths'].values():
        for kind in ('uid','gid'):
            if row['st_'+kind] != 1000:row['st_'+kind]=65534
    return x


class Maps(unittest.TestCase):
    def test_pre_post_and_host_reader(self):
        p.validate_stage_context('pre',ctx('pre'),origin())
        p.validate_stage_context('post',ctx('post'),origin())
        p.single_map('1000 1000 1',1000,1000) # outside final read
        p.single_map('1000 0 1',1000,0)       # inside final read
    def test_malformed_and_ambiguous(self):
        for raw in ('','1000 1000 1\n1000 1000 1','1000 1000 2','+1000 1000 1','1000 1000 0',
                    '0 0 4294967295','1000 1000 1 junk','1000 1000 1\n\n','١٠٠٠ 1000 1','4294967295 1000 1'):
            with self.subTest(raw=raw),self.assertRaises(Rejected):p.single_map(raw,1000,1000)
    def test_post_pre_map_rejected(self):
        x=ctx('post');x['maps']['uid']='1000 1000 1'
        with self.assertRaises(Rejected):p.validate_stage_context('post',x,origin())
    def test_wrong_host_composition(self):
        with self.assertRaises(Rejected):p.single_map('1000 0 1',1000,1000)
    def test_spoofed_context(self):
        for key,value in (('boot','other'),('uid',0),('gid',0),('cgroup','/other.service')):
            x=ctx('pre');x[key]=value
            with self.subTest(key=key),self.assertRaises(Rejected):p.validate_stage_context('pre',x,origin())
    def test_namespace_change_matrix(self):
        for stage in ('pre','post'):
            for n in p.NS_NAMES:
                x=ctx(stage)
                x['namespaces'][n]=(origin()['namespaces'][n] if x['namespaces'][n]!=origin()['namespaces'][n] else n+':[999]')
                with self.subTest(stage=stage,n=n),self.assertRaises(Rejected):p.validate_stage_context(stage,x,origin())


class Objects(unittest.TestCase):
    def test_authentic_host_and_projections(self):
        h=fixture();p.validate_observation(h,host=True);p.compare_host(h,copy.deepcopy(h))
        for stage in ('pre','post'):p.compare_namespace(h,projected(h,stage),ctx(stage),origin())
    def test_overflow_is_not_ownership_authority(self):
        for uid in (1001,65534,4294967294):
            h=fixture();h['paths'][p.UNSHARE]['st_uid']=uid
            with self.subTest(uid=uid),self.assertRaises(Rejected):p.compare_host(fixture(),h)
    def test_changed_file_identity_fields(self):
        for field in p.STAT_FIELDS:
            h=fixture();h['paths'][p.UNSHARE][field]+=1
            with self.subTest(field=field),self.assertRaises(Rejected):p.compare_host(fixture(),h)
    def test_changed_parent_identity(self):
        for field in p.IDENTITY_FIELDS:
            h=fixture();h['paths']['/usr'][field]+=1
            with self.subTest(field=field),self.assertRaises(Rejected):p.compare_host(fixture(),h)
    def test_byte_and_filecaps(self):
        for key,val in (('sha256','0'*64),('filecaps',True)):
            h=fixture();h['files'][p.UNSHARE][key]=val
            with self.subTest(key=key),self.assertRaises(Rejected):p.validate_observation(h,host=True)
    def test_symlink_privileged_writable_hardlink(self):
        for path,field,val in ((p.UNSHARE,'st_mode',stat.S_IFLNK|0o777),('/usr','st_mode',stat.S_IFDIR|0o777),
                (p.UNSHARE,'st_mode',stat.S_IFREG|0o4755),(p.UNSHARE,'st_nlink',2)):
            h=fixture();h['paths'][path][field]=val
            with self.subTest(val=val),self.assertRaises(Rejected):p.validate_observation(h,host=True)
    def test_missing_extra_error(self):
        for change in ('missing','extra','error'):
            h=fixture()
            if change=='missing':del h['paths']['/usr']
            if change=='extra':h['paths']['/writable']=h['paths']['/']
            if change=='error':h['errors']=['EACCES']
            with self.subTest(change=change),self.assertRaises(Rejected):p.validate_observation(h,host=True)
    def test_bad_namespace_metadata(self):
        for field in p.STAT_FIELDS:
            h=fixture();l=projected(h,'post');l['paths'][p.UNSHARE][field]+=1
            with self.subTest(field=field),self.assertRaises(Rejected):p.compare_namespace(h,l,ctx('post'),origin())
    def test_namespace_root_proof_spoof(self):
        h=fixture();l=projected(h,'post');l['root_mount']['readonly']=False
        with self.assertRaises(Rejected):p.compare_namespace(h,l,ctx('post'),origin())


class Scaffold(unittest.TestCase):
    def scaffold(self):
        h=fixture();r=h['paths']['/'];r.update(st_dev=os.makedev(0,100),st_ino=3,st_uid=1000,st_gid=1000)
        h['root_mount'].update(id=999,dev=[0,100],root='/newroot',fstype='tmpfs',options=['ro','nosuid','nodev'])
        return h
    def test_constructed_root_distinct_from_host(self):
        h=self.scaffold();p.compare_host(fixture(),h,origin())
        p.compare_namespace(h,projected(h,'post'),ctx('post'),origin())
    def test_scaffold_rejected_without_specific_proof(self):
        with self.assertRaises(Rejected):p.compare_host(fixture(),self.scaffold())
    def test_root_owner_mode_symlink(self):
        for key,val in (('st_uid',0),('st_gid',0),('st_mode',stat.S_IFDIR|0o777),('st_mode',stat.S_IFLNK|0o755)):
            h=self.scaffold();h['paths']['/'][key]=val
            with self.subTest(key=key,val=val),self.assertRaises(Rejected):p.compare_host(fixture(),h,origin())
    def test_root_mount_failures(self):
        for key,val in (('id',0),('readonly',False),('root','/'),('fstype','ext4'),('options',['rw','nosuid','nodev']),('optional',['shared:2']),('dev',[1,1])):
            if key=='id':continue # kernel parser validates id; this is a post-parser model
            h=self.scaffold();h['root_mount'][key]=val
            with self.subTest(key=key),self.assertRaises(Rejected):p.compare_host(fixture(),h,origin())
    def test_imported_parent_is_never_exempt(self):
        for key,val in (('st_uid',1000),('st_mode',stat.S_IFDIR|0o777),('st_ino',1)):
            h=self.scaffold();h['paths']['/usr'][key]=val
            with self.subTest(key=key),self.assertRaises(Rejected):p.compare_host(fixture(),h,origin())
    def test_uncombined_source_has_no_scaffold_authority(self):
        self.assertFalse(p.scaffold_source_contract())


class Lineage(unittest.TestCase):
    def setUp(self):
        self.host=dict(user=1,mnt=2,pid=3,net=4,cgroup=5)
        self.pre=dict(user=10,mnt=11,pid=3,net=4,cgroup=5)
        self.post=dict(user=30,mnt=21,pid=22,net=23,cgroup=5)
        self.edges={(10,p.NS_GET_PARENT):1,(11,p.NS_GET_USERNS):10,
                    (30,p.NS_GET_PARENT):20,(20,p.NS_GET_PARENT):10,
                    (21,p.NS_GET_USERNS):20,(22,p.NS_GET_USERNS):20,
                    (23,p.NS_GET_USERNS):20,(22,p.NS_GET_PARENT):3}
    def runproof(self,stage,pre=True):
        @contextlib.contextmanager
        def related(fd,op):yield self.edges.get((fd,op),9999)
        with patch.object(p,'_ns_identity',side_effect=lambda fd:(3,fd)),patch.object(p,'_related',related):
            return p.lineage(stage,self.pre if stage=='pre' else self.post,self.host,self.pre if pre else None)
    def test_exact_devpts_chain(self):self.runproof('pre');self.runproof('post')
    def test_wrong_owner_or_parent(self):
        for key in list(self.edges):
            old=self.edges[key];self.edges[key]=999
            stage='pre' if key[0] in (10,11) else 'post'
            with self.subTest(edge=key),self.assertRaises(Rejected):self.runproof(stage)
            self.edges[key]=old
    def test_final_not_owner_of_mount_pid_net(self):
        for n in ('mnt','pid','net'):
            self.edges[(self.post[n],p.NS_GET_USERNS)]=30
            with self.subTest(n=n),self.assertRaises(Rejected):self.runproof('post')
            self.edges[(self.post[n],p.NS_GET_USERNS)]=20
    def test_no_pre_no_post(self):
        with self.assertRaises(Rejected):self.runproof('post',False)
    def test_missing_intermediate(self):
        self.edges[(30,p.NS_GET_PARENT)]=10
        with self.assertRaises(Rejected):self.runproof('post')
    def test_io_errors_are_not_proofs(self):
        for error in (PermissionError(errno.EPERM,'scope'),FileNotFoundError(errno.ENOENT,'exit')):
            with patch.object(p,'_ns_identity',side_effect=lambda fd:(3,fd)),patch.object(p,'_related',side_effect=error):
                with self.subTest(error=error),self.assertRaises(OSError):p.lineage('post',self.post,self.host,self.pre)
    def test_cgroup_namespace_is_unchanged(self):
        self.post['cgroup']=77
        with self.assertRaises(Rejected):self.runproof('post')


class Protocol(unittest.TestCase):
    def service(self,stage='pre'):
        t=p.HostTrust.__new__(p.HostTrust);t.manifest=dict(attempt_root='/attempt',cwd='/attempt',argv=['/payload','arg'])
        t.origin=origin();t.origin['trust_channel']=dict(request_fd=8,reply_fd=9,nonce='a'*64)
        t.argv=p.command(t.manifest,t.origin);t.baseline=fixture();t.stages=[] if stage=='pre' else ['pre'];t.proofs=[]
        t.host_fds={n:i+10 for i,n in enumerate(p.NS_NAMES)};t.pre_fds={n:i+100 for i,n in enumerate(p.NS_NAMES)};t.leader=dict(pid=123,starttime=50)
        i=t.argv.index('pre');pre=t.argv[i+4:];j=pre.index('post')
        expected=pre if stage=='pre' else t.manifest['argv']
        request=dict(stage=stage,nonce='a'*64,origin=t.origin,attempt='/attempt',argv=expected,context=ctx(stage),observation=projected(fixture(),stage))
        process=dict(pid=124,starttime=51,ppid=123,executable=p.PYTHON,argv=(t.argv[i-4:i+4]+expected if stage=='pre' else pre[j-4:]),context=ctx(stage))
        process['context']['maps']={k:'1000 1000 1\n' for k in ('uid','gid')}
        return t,request,process
    @contextlib.contextmanager
    def mocked(self,t,process):
        fds={n:(100 if t.stages==[] else 200)+i for i,n in enumerate(p.NS_NAMES)};fds['cgroup']=14
        if not t.stages:fds.update(pid=12,net=13)
        with contextlib.ExitStack() as stack:
            for name,value in [('_bounded_read',lambda *a:'124\n'),('_process',lambda pid:copy.deepcopy(process)),
                    ('_descendant',lambda *a:True),('lineage',lambda *a:{'model':True}),
                    ('_ns_identity',lambda fd:(3,fd)),('trust_observation',lambda *a:fixture()),
                    ('dependency_diagnostic',lambda *a:None)]:stack.enter_context(patch.object(p,name,value))
            stack.enter_context(patch.object(t,'_open_ns',return_value=fds))
            stack.enter_context(patch.object(p.os,'open',return_value=700));stack.enter_context(patch.object(p.os,'close'))
            yield
    def test_live_model_both_scopes(self):
        for stage in ('pre','post'):
            t,r,proc=self.service(stage)
            with self.subTest(stage=stage),self.mocked(t,proc):t._accept(r)
            self.assertEqual(len(t.proofs),1)
    def test_spoofed_context_nonce_attempt_argv_receipt(self):
        for key,value in (('origin',{}),('nonce','b'*64),('attempt','/wrong'),('argv',['/wrong']),('stage','post')):
            t,r,proc=self.service();r[key]=value
            with self.subTest(key=key),self.mocked(t,proc),self.assertRaises((Rejected,KeyError)):t._accept(r)
            self.assertEqual(t.proofs,[])
    def test_unowned_or_wrong_executable_process(self):
        for field,value in (('argv',['/not-helper']),('executable','/other'),('cgroup','/wrong.service')):
            t,r,proc=self.service()
            if field=='cgroup':proc['context'][field]=value
            else:proc[field]=value
            with self.subTest(field=field),self.mocked(t,proc),self.assertRaises(Rejected):t._accept(r)
    def test_wrong_composed_host_map(self):
        t,r,proc=self.service('post');proc['context']['maps']['uid']='1000 0 1'
        with self.mocked(t,proc),self.assertRaises(Rejected):t._accept(r)
    def test_pid_race(self):
        t,r,proc=self.service();raced=copy.deepcopy(proc);raced['starttime']+=1
        with self.mocked(t,proc),patch.object(p,'_process',side_effect=[proc,raced]),self.assertRaises(Rejected):t._accept(r)
    def test_foreign_ancestry(self):
        t,r,proc=self.service()
        with self.mocked(t,proc),patch.object(p,'_descendant',return_value=False),self.assertRaises(Rejected):t._accept(r)
    def test_proc_access_errors(self):
        t,r,proc=self.service()
        with self.mocked(t,proc),patch.object(t,'_open_ns',side_effect=PermissionError('scope')),self.assertRaises(PermissionError):t._accept(r)
    def test_complete_requires_both_stages(self):
        t,_,_=self.service()
        for stages in ([],['pre'],['post'],['pre','post','post']):
            t.stages=stages
            with self.subTest(stages=stages),self.assertRaises(Rejected):t.complete()
    def test_oversize_duplicate_json_and_replay(self):
        with self.assertRaises(Rejected):p._frame({'x':'a'*p.MAX_FRAME})
        with self.assertRaises(Rejected):p.strict_json('{"stage":"pre","stage":"post"}')
        t,r,proc=self.service();t.stages=['pre','post']
        with self.mocked(t,proc),self.assertRaises(Rejected):t._accept(r)
    def test_writable_authority_roots(self):
        for root in ('/',str(p.HERE),'/usr','/etc'):
            with patch.object(p,'context',return_value=origin()),patch.object(p,'verify_dependencies') as deps:
                with self.subTest(root=root),self.assertRaises(Rejected):p.HostTrust({},origin(),[root])
                deps.assert_not_called()
    def test_origin_not_accepted_from_user_json(self):
        with patch.object(p,'context',return_value=origin()),self.assertRaises(Rejected):p.HostTrust({},dict(uid=0),[])


class Ordering(unittest.TestCase):
    def test_diag_before_dependency_failure_and_no_release(self):
        events=[]
        with patch.object(p,'trust_observation',return_value=fixture()),patch.object(p,'context',return_value=ctx('pre')),\
             patch.object(p,'dependency_diagnostic',side_effect=lambda *a:events.append(a[0])),\
             patch.object(p,'policy_gate',return_value={}),patch.object(p,'verify_dependency_contract',side_effect=Rejected('dependency')) as deps,\
             patch.object(p,'namespace_trust') as release,patch.object(p.os,'execv') as execute:
            with self.assertRaises(Rejected):p.gate('pre',origin(),'/attempt',[p.BWRAP])
            self.assertEqual(events,['pre-before-validation','pre-rejected']);release.assert_not_called();execute.assert_not_called()
    def test_namespace_proof_before_dependency_release(self):
        x=ctx('post');x['maps']['uid']='1000 1000 1'
        with patch.object(p,'trust_observation',return_value=fixture()),patch.object(p,'context',return_value=x),\
             patch.object(p,'dependency_diagnostic'),patch.object(p,'policy_gate',return_value={}),\
             patch.object(p,'verify_dependency_contract') as deps,patch.object(p,'namespace_trust') as release:
            with self.assertRaises(Rejected):p.gate('post',origin(),'/attempt',['/payload'])
            deps.assert_not_called();release.assert_not_called()
    def test_old_gates_unchanged_ast(self):
        def functions(path):
            return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        old=functions(HERE/'frozen-v8/private_workload.py');new=functions(HERE/'proposed/private_workload.py')
        for name in ('_security_snapshot','_security_diagnostic','_drop_capabilities','initialize_origin_capabilities','policy_gate','command','private_snapshot','main'):
            self.assertEqual(old[name],new[name],name)
        self.assertEqual((HERE/'frozen-v8/effective_storage.py').read_bytes(),(HERE/'proposed/effective_storage.py').read_bytes())
    def test_controller_other_methods_unchanged(self):
        def methods(path):
            cls=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Controller')
            return {n.name:ast.dump(n) for n in cls.body if isinstance(n,ast.FunctionDef)}
        old=methods(HERE/'frozen-v8/storage_controller.py');new=methods(HERE/'proposed/storage_controller.py')
        for name in old:
            if name!='inner':self.assertEqual(old[name],new[name],name)
    def test_controller_join_transport_order(self):
        s=(HERE/'proposed/storage_controller.py').read_text()
        self.assertIn('pass_fds=trust.pass_fds',s);self.assertIn('guard=guarded_trust',s)
        self.assertLess(s.index('cleanup.wait_owned(child'),s.index('trust.complete()'))
        self.assertLess(s.index('trust.close()'),s.index('self.ledger.finish_service(self.key, result'))
    def test_no_child_ancestor_ioctl(self):
        tree=ast.parse((HERE/'proposed/private_workload.py').read_text())
        gate=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='gate')
        self.assertNotIn('ioctl',ast.dump(gate));self.assertNotIn('lineage',ast.dump(gate))


class HostReadOnly(unittest.TestCase):
    def test_real_host_dependencies_and_metadata(self):
        with contextlib.redirect_stdout(io.StringIO()):p.verify_dependencies()
        obs=p.trust_observation();p.validate_observation(obs,host=True)
        (HERE/'evidence/host-system-observations.json').write_text(json.dumps(obs,indent=2)+'\n')
        self.assertEqual(obs['paths'][p.UNSHARE]['st_uid'],0)
    def test_actual_own_symlink_nofollow(self):
        # No installed-path mutation: only an owned, bounded fixture.
        d=HERE/'evidence/owned-fixture';d.mkdir(exist_ok=True)
        target=d/'regular';target.write_bytes(b'bytes');link=d/'link'
        if not link.exists():link.symlink_to(target.name)
        with self.assertRaises(OSError):
            fd=os.open(link,os.O_RDONLY|os.O_NOFOLLOW)
            os.close(fd)
    def test_real_direction_and_eof(self):
        a,b=os.pipe()
        try:
            os.close(b)
            self.assertEqual(os.read(a,1),b'')
            self.assertEqual(p.fcntl.fcntl(a,p.fcntl.F_GETFL)&os.O_ACCMODE,os.O_RDONLY)
        finally:os.close(a)



class Pipes(unittest.TestCase):
    def invoke(self,stage,alter=None,eof=False):
        request_read,request_write=os.pipe();reply_read,reply_write=os.pipe()
        o=origin();o['trust_channel']=dict(request_fd=request_write,reply_fd=reply_read,nonce='a'*64)
        frames=[]
        def write(fd,raw):
            self.assertEqual(fd,request_write);frames.append(raw)
            if eof:
                os.close(reply_write);return
            answer=dict(stage=stage,nonce='a'*64,request_sha256=hashlib.sha256(raw).hexdigest(),accepted=True)
            if alter:alter(answer)
            os.write(reply_write,p._frame(answer))
        try:
            with patch.object(p,'_write_all',side_effect=write):
                p.namespace_trust(stage,o,'/attempt',['/payload'],ctx(stage),fixture())
            if stage=='pre':
                os.fstat(request_write);os.fstat(reply_read)
            else:
                for fd in (request_write,reply_read):
                    with self.assertRaises(OSError):os.fstat(fd)
            self.assertEqual(len(frames),1)
        finally:
            for fd in (request_read,request_write,reply_read,reply_write):
                try:os.close(fd)
                except OSError:pass
    def test_pre_preserves_post_closes_both_endpoints(self):
        self.invoke('pre');self.invoke('post')
    def test_wrong_receipt_hash_nonce_stage_acceptance(self):
        for key,val in (('nonce','b'*64),('stage','post'),('request_sha256','f'*64),('accepted',False),('accepted',1)):
            with self.subTest(key=key,val=val),self.assertRaises(Rejected):
                self.invoke('pre',lambda answer:answer.update({key:val}))
    def test_helper_eof(self):
        with self.assertRaises(Rejected):self.invoke('pre',eof=True)
    def test_nonblocking_partial_host_frame_no_early_release(self):
        t=p.HostTrust.__new__(p.HostTrust);t.request_read=8;t.reply_write=9;t.buffer=b'';t.stages=[]
        t.origin=dict(trust_channel=dict(nonce='a'*64))
        raw=p._frame(dict(stage='pre'));events=[]
        with patch.object(p.os,'read',side_effect=[raw[:3],raw[3:]]),patch.object(t,'_accept',side_effect=lambda r:events.append('accepted')),\
             patch.object(p,'_write_all',side_effect=lambda *a:events.append('replied')):
            t.poll();self.assertEqual(events,[]);self.assertEqual(t.stages,[])
            t.poll();self.assertEqual(events,['accepted','replied']);self.assertEqual(t.stages,['pre'])
    def test_host_eof_overflow_trailing_no_release(self):
        for data in (b'',b'x'*(p.MAX_FRAME+1),b'{}\n{}\n'):
            t=p.HostTrust.__new__(p.HostTrust);t.request_read=8;t.buffer=b'';t.stages=[]
            with patch.object(p.os,'read',return_value=data),patch.object(t,'_accept') as accept,patch.object(p,'_write_all') as reply:
                with self.subTest(size=len(data)),self.assertRaises(Rejected):t.poll()
                accept.assert_not_called();reply.assert_not_called()
    def test_observer_error_never_writes_ack(self):
        t=p.HostTrust.__new__(p.HostTrust);t.request_read=8;t.buffer=b'';t.stages=[]
        with patch.object(p.os,'read',return_value=b'{"stage":"pre"}\n'),patch.object(t,'_accept',side_effect=PermissionError('no proc')),\
             patch.object(p,'dependency_diagnostic'),patch.object(p,'_write_all') as reply:
            with self.assertRaises(PermissionError):t.poll()
            reply.assert_not_called()
    def test_host_closes_child_endpoints_after_attach(self):
        t=p.HostTrust.__new__(p.HostTrust);t.request_write=8;t.reply_read=9
        with patch.object(p,'_process',return_value=dict(pid=42,starttime=50)),patch.object(p.os,'close') as close:
            t.attach(type('Child',(),{'pid':42})())
            self.assertEqual(close.call_args_list, [unittest.mock.call(8),unittest.mock.call(9)])
            self.assertIsNone(t.request_write);self.assertIsNone(t.reply_read)
    def test_short_write_progress(self):
        with patch.object(p.os,'write',side_effect=[2,2,1]) as write:p._write_all(8,b'abcde')
        self.assertEqual([x.args[1] for x in write.call_args_list],[b'abcde',b'cde',b'e'])
    def test_partial_write_failure(self):
        with patch.object(p.os,'write',side_effect=[1,BrokenPipeError('closed')]),self.assertRaises(BrokenPipeError):p._write_all(8,b'ab')
    def test_diagnostic_path_inventory_bounded(self):
        x=fixture();x['paths']['/secret-not-an-input']=x['paths']['/']
        buf=io.StringIO()
        with contextlib.redirect_stdout(buf):p.dependency_diagnostic('rejected',x,ctx('pre'),'why')
        self.assertNotIn('/secret-not-an-input',buf.getvalue());self.assertIn('st_uid',buf.getvalue())


class CombinedReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('combined_review',HERE/'combined-review/private_workload.py')
        cls.c=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.c)
    def test_exact_reviewed22_command_and_host_transport(self):
        c=self.c;m=dict(attempt_root='/mnt/review-only-attempt',cwd='/mnt/review-only-attempt',inputs=c.BINARIES+c.POLICY_INPUTS,argv=[c.PYTHON,'-V'])
        o=origin();o['trust_channel']=dict(request_fd=8,reply_fd=9,nonce='a'*64)
        argv=c.command(m,o)
        for stage in ('pre','post'):
            i=argv.index(stage);self.assertEqual(json.loads(argv[i+1]),o)
        self.assertTrue(c.scaffold_source_contract())
        i=argv.index(c.BWRAP);tail=argv[i:]
        self.assertNotIn(['--ro-bind','/','/'],[tail[n:n+3] for n in range(len(tail)-2)])
        self.assertIn(['--remount-ro','/'],[tail[n:n+2] for n in range(len(tail)-1)])
    def test_only22_runtime_source_added(self):
        def functions(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        proposed=functions(HERE/'proposed/private_workload.py');combined=functions(HERE/'combined-review/private_workload.py')
        for name in proposed:
            if name!='command':self.assertEqual(proposed[name],combined[name],name)
    def test_scaffold_real_accept_path_model(self):
        c=self.c;t,r,proc=Protocol().service('post');t.__class__=c.HostTrust
        scaffold=Scaffold().scaffold();r['observation']=projected(scaffold,'post')
        # Cross-module pure fixtures; no namespace creation or /proc child reads.
        fds={n:200+i for i,n in enumerate(c.NS_NAMES)};fds['cgroup']=14
        with patch.object(c,'_bounded_read',return_value='124\n'),patch.object(c,'_process',return_value=proc),\
             patch.object(c,'_descendant',return_value=True),patch.object(c,'lineage',return_value={'model':True}),\
             patch.object(c,'_ns_identity',side_effect=lambda fd:(3,fd)),patch.object(t,'_open_ns',return_value=fds),\
             patch.object(c.os,'open',return_value=700),patch.object(c.os,'close'),\
             patch.object(c,'trust_observation',side_effect=[scaffold,fixture()]),patch.object(c,'dependency_diagnostic'):
            t._accept(r)
        self.assertEqual(len(t.proofs),1)


class OldSecurityGates(unittest.TestCase):
    def snapshot(self,stage):
        status={k:['0000000000000000'] for k in ('CapInh','CapPrm','CapEff','CapAmb','CapBnd')}
        status.update(Uid=['1000']*4,Gid=['1000']*4,NoNewPrivs=['1' if stage=='post' else '0'])
        return dict(errors=[],status=status,label={'origin':'unconfined','pre':'vkf-storage-pre-v2 (enforce)','post':'bwrap//&unpriv_bwrap (enforce)'}[stage])
    def test_all_original_policy_stages(self):
        for stage in ('origin','pre','post'):
            with patch.object(p,'_security_snapshot',return_value=self.snapshot(stage)),patch.object(p,'_security_diagnostic'):
                p.policy_gate(stage,origin())
    def test_old_strict_capability_ids_nnp_labels(self):
        for stage in ('origin','pre','post'):
            for field,value in (('CapEff',['0000000000000001']),('CapInh',['0000000000000001']),('Uid',['0']*4),('NoNewPrivs',['9'])):
                snap=self.snapshot(stage);snap['status'][field]=value
                with self.subTest(stage=stage,field=field),patch.object(p,'_security_snapshot',return_value=snap),patch.object(p,'_security_diagnostic'),self.assertRaises(Rejected):p.policy_gate(stage,origin())
        for label in ('unconfined','bwrap (enforce)','bwrap//&unpriv_bwrap//&other (enforce)','bwrap//&unpriv_bwrap (complain)'):
            snap=self.snapshot('post');snap['label']=label
            with self.subTest(label=label),patch.object(p,'_security_snapshot',return_value=snap),patch.object(p,'_security_diagnostic'),self.assertRaises(Rejected):p.policy_gate('post',origin())
    def test_post_storage_failure_still_blocks_exec(self):
        with patch.object(p,'trust_observation',return_value=fixture()),patch.object(p,'context',return_value=ctx('post')),\
             patch.object(p,'dependency_diagnostic'),patch.object(p,'policy_gate',return_value={}),\
             patch.object(p,'verify_dependency_contract'),patch.object(p,'validate_observation'),patch.object(p,'namespace_trust'),\
             patch.object(p,'private_snapshot',return_value=1),patch.object(p.effective_storage,'check',side_effect=Rejected('inaccessible mount')),\
             patch.object(p.Path,'read_text',return_value='model mountinfo'),patch.object(p.os,'execv') as execute,contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Rejected):p.gate('post',origin(),'/attempt',['/payload'])
            execute.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
