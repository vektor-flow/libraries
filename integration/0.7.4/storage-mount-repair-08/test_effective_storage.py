import errno
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import effective_storage as es
HERE=Path(__file__).resolve().parent
D=stat.S_IFDIR|0o755
F=stat.S_IFREG|0o600
C=stat.S_IFCHR|0o666

def line(mid,parent,path,mode='ro',fstype='ext4',root='/',optional='',supermode='rw'):
    def esc(v):return v.replace('\\','\\134').replace(' ','\\040').replace('\t','\\011').replace('\n','\\012')
    return f'{mid} {parent} 8:1 {esc(root)} {esc(path)} {mode}'+(' '+optional if optional else '')+f' - {fstype} /dev/mock {supermode}\n'

def ob(mid,ro=True,mode=D,rdev=(0,0)):
    return es.Observation(mid,(8,1),mid+100,mode,rdev,ro,1000,1000)

class Topology(unittest.TestCase):
    def setUp(self):
        self.raw=line(10,9,'/')+line(20,10,'/attempt','rw')
        self.obs={'/':ob(10),'/attempt':ob(20,False)}
    def run_check(self,extra='',observations=None,attempt='/attempt'):
        values={**self.obs,**(observations or {})}
        return es.check(self.raw+extra,attempt,values.__getitem__)
    def test_only_attempt_writable(self):
        self.assertEqual(self.run_check()['attempt_mount_id'],20)
    def test_nested_rw_filesystems_and_file_binds_rejected(self):
        for path in ('/nested','/attempt/nested','/attempt-sibling','/dev','/proc'):
            for fs in ('ext4','tmpfs','proc','devpts','overlay','fuse.portal','nsfs'):
                for mode in (D,F):
                    with self.subTest(path=path,fs=fs,mode=mode),self.assertRaises(es.Rejected):
                        self.run_check(line(30,20 if path.startswith('/attempt/') else 10,path,'rw',fs),{path:ob(30,False,mode)})
    def test_readonly_nested_mounts_allowed(self):
        self.run_check(line(30,10,'/nested'),{'/nested':ob(30)})
    def test_hidden_proc_child_never_probed(self):
        raw=line(30,10,'/proc','rw','proc')+line(31,30,'/proc/sys/fs/binfmt_misc','rw','binfmt_misc')+line(40,30,'/proc','ro','proc')
        r=self.run_check(raw,{'/proc':ob(40)})
        self.assertEqual({x['id'] for x in r['rows'] if x['result']=='hidden'},{30,31})
    def test_same_path_stack_actual_id_not_order_or_largest(self):
        for rows in ((30,40),(40,30)):
            extra={30:line(30,10,'/stack','rw'),40:line(40,30,'/stack')}
            r=self.run_check(''.join(extra[x] for x in rows),{'/stack':ob(40)})
            self.assertIn('hidden',[x['result'] for x in r['rows'] if x['id']==30])
        self.run_check(line(90,10,'/stack','rw')+line(35,90,'/stack'),{'/stack':ob(35)})
    def test_hidden_old_boundary_is_plain_directory_in_new_mount(self):
        extra=line(30,10,'/proc','rw')+line(31,30,'/proc/a','rw')+line(40,30,'/proc')+line(50,40,'/proc/a/b')
        r=self.run_check(extra,{'/proc':ob(40),'/proc/a':ob(40),'/proc/a/b':ob(50)})
        self.assertEqual(next(x for x in r['rows'] if x['id']==50)['result'],'readonly')
        with self.assertRaises(es.Rejected):
            self.run_check(extra.replace('/proc/a/b ro','/proc/a/b rw'),{'/proc':ob(40),'/proc/a':ob(40),'/proc/a/b':ob(50,False)})
    def test_reachable_rw_overmount_fails(self):
        with self.assertRaises(es.Rejected):
            self.run_check(line(30,10,'/stack')+line(40,30,'/stack','rw'),{'/stack':ob(40,False)})
    def test_covering_sibling_mount_hides_nested_old_mount(self):
        r=self.run_check(line(30,10,'/x/old','rw')+line(40,10,'/x'),{'/x':ob(40)})
        self.assertEqual(next(x for x in r['rows'] if x['id']==30)['result'],'hidden')
    def test_new_nested_mount_under_cover_is_reachable_and_rejected(self):
        with self.assertRaises(es.Rejected):
            self.run_check(line(30,10,'/x/old','rw')+line(40,10,'/x')+line(50,40,'/x/new','rw'),{'/x':ob(40),'/x/new':ob(50,False)})
    def test_character_identity_and_object_type(self):
        self.run_check(line(30,10,'/dev/null','rw'),{'/dev/null':ob(30,False,C,(1,3))})
        for mode,dev,path in ((F,(1,3),'/dev/null'),(D,(1,3),'/dev/null'),(C,(1,1),'/dev/null'),(stat.S_IFBLK,(8,1),'/dev/null'),(C,(1,3),'/fake-null'),(stat.S_IFIFO,(0,0),'/fifo')):
            with self.subTest(mode=mode,dev=dev,path=path),self.assertRaises(es.Rejected):
                self.run_check(line(30,10,path,'rw'),{path:ob(30,False,mode,dev)})
    def test_errors_are_unknown_not_safe(self):
        for err in (errno.EACCES,errno.EPERM,errno.ENOENT,errno.ENOTDIR,errno.EIO,errno.ESTALE,errno.ELOOP):
            def inspect(path):
                if path=='/bad':raise OSError(err,'injected')
                return self.obs[path]
            with self.subTest(errno=err),self.assertRaises(es.Rejected):
                es.check(self.raw+line(30,10,'/bad','rw'),'/attempt',inspect)
    def test_unknown_mount_identity_device_and_flags_fail(self):
        for obj in (ob(99),es.Observation(30,(8,2),130,D,(0,0),True,1000,1000),ob(30,False)):
            with self.subTest(obj=obj),self.assertRaises(es.Rejected):self.run_check(line(30,10,'/bad'),{'/bad':obj})
    def test_ancestor_id_at_mountpoint_is_not_a_hidden_proof(self):
        with self.assertRaises(es.Rejected):
            self.run_check(line(30,10,'/stack')+line(40,30,'/stack','rw'),{'/stack':ob(30)})
    def test_root_overmount_hides_old_tree_but_keeps_new_attempt(self):
        raw=line(10,9,'/','rw')+line(11,10,'/hidden','rw')+line(15,10,'/')+line(20,15,'/attempt','rw')
        r=es.check(raw,'/attempt',{'/':ob(15),'/attempt':ob(20,False)}.__getitem__)
        self.assertEqual({x['id'] for x in r['rows'] if x['result']=='hidden'},{10,11})
    def test_disconnected_root_topology_rejected(self):
        with self.assertRaises(es.Rejected):self.run_check(line(30,999,'/'))
    def test_nsfs_opaque_root_is_parsed_without_type_exemption(self):
        raw=line(30,10,'/namespace','rw','nsfs',root='net:[4026532000]')
        self.assertEqual(es.parse_mountinfo(raw+line(10,9,'/'))[30].root,'net:[4026532000]')
        with self.assertRaises(es.Rejected):self.run_check(raw,{'/namespace':ob(30,False,F)})
    def test_ro_superblock_rw_mount_effective_readonly(self):
        self.run_check(line(30,10,'/sb','rw',supermode='ro'),{'/sb':ob(30)})
    def test_escape_roundtrip_all_four_and_single_pass(self):
        for path in ('/spaces here','/tab\there','/newline\nhere','/literal\\040'):
            self.run_check(line(30,10,path),{path:ob(30)})
        self.assertEqual(es.unescape(r'/x\134040'),'/x\\040')
    def test_malformed_escapes_and_topology_fail(self):
        cases=[line(30,10,'/bad').replace('/bad',r'/bad\777'),line(30,30,'/bad'),line(30,31,'/bad')+line(31,30,'/bad'),line(30,999,'/bad'),line(30,20,'/bad'),line(30,10,'/x/../bad'),line(30,10,'//bad'),line(30,10,'/bad','rw,ro'),line(30,10,'/bad','noatime'),line(20,10,'/dup'),line(30,10,'/bad',optional='shared:7'),line(30,10,'/bad',optional='master:7')]
        for raw in cases:
            with self.subTest(raw=raw),self.assertRaises(es.Rejected):self.run_check(raw)
    def test_symlink_mount_object_rejected(self):
        with self.assertRaises(es.Rejected):self.run_check(line(30,10,'/bad'),{'/bad':ob(30,True,stat.S_IFLNK|0o777)})
    def test_missing_readonly_or_symlink_attempt_fails(self):
        for attempt in ('/missing','/','/attempt/../attempt'):
            with self.subTest(attempt=attempt),self.assertRaises(es.Rejected):self.run_check(attempt=attempt)
        with self.assertRaises(es.Rejected):es.check(line(10,9,'/')+line(20,10,'/attempt'),'/attempt',{'/':ob(10),'/attempt':ob(20)}.__getitem__)
    def test_mount_changes_during_inspection_fail(self):
        with patch.object(Path,'read_text',side_effect=[self.raw,self.raw+'\n']),patch.object(es,'observe',side_effect=self.obs.__getitem__):
            with self.assertRaisesRegex(es.Rejected,'changed'):es.qualify('/attempt')
    def test_object_changes_during_second_scan_fail(self):
        counts={}
        def lookup(path):
            counts[path]=counts.get(path,0)+1
            return ob(10,True,F) if path=='/' and counts[path]>1 else self.obs[path]
        with patch.object(Path,'read_text',return_value=self.raw),patch.object(es,'observe',side_effect=lookup):
            with self.assertRaisesRegex(es.Rejected,'changed'):es.qualify('/attempt')

class RealReadOnlyAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=HERE,prefix='fs-test-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def test_actual_fd_mount_identity_and_owned_file_write(self):
        p=self.root/'owned file\twith\nslash\\040';p.write_bytes(b'bounded fixture\n')
        o=es.observe(str(p));mounts=es.parse_mountinfo(Path('/proc/self/mountinfo').read_text())
        self.assertEqual(o.dev,mounts[o.mount_id].dev);self.assertEqual(o.ino,p.stat().st_ino)
        self.assertTrue(stat.S_ISREG(o.mode));self.assertEqual(p.read_bytes(),b'bounded fixture\n')
    def test_final_and_intermediate_symlinks_refused(self):
        (self.root/'real').mkdir();(self.root/'real/file').write_bytes(b'x');(self.root/'link').symlink_to(self.root/'real',target_is_directory=True)
        for suffix in ('link','link/file'):
            with self.subTest(suffix=suffix),self.assertRaises(es.Rejected):es.observe(str(self.root/suffix))
    def test_real_missing_path_is_not_success(self):
        with self.assertRaises(FileNotFoundError):es.observe(str(self.root/'missing'))
    def test_metadata_adapter_never_uses_write_open(self):
        real_open=os.open;seen=[]
        def check(path,flags,*a,**kw):
            seen.append(flags);self.assertFalse(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC));return real_open(path,flags,*a,**kw)
        with patch.object(os,'open',side_effect=check):es.observe(str(self.root))
        self.assertTrue(seen)
if __name__=='__main__':unittest.main(verbosity=2)
