"""REVIEWED PROPOSAL ONLY: root install/rollback. Never invoked by repair18.

No replacement, service, namespace, workload, source/config or accounting mutation.
On partial failure leave non-executable staging for explicit review; never retry.
"""
import fcntl,hashlib,json,os,stat,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=HERE.parent
PARSER=Path('/usr/sbin/apparmor_parser')
PYTHON=Path('/usr/bin/python3.14')
DESTDIR=Path('/usr/local/libexec/vkf-storage-private-v2')
BINARY=DESTDIR/'unshare'
POLICY=Path('/etc/apparmor.d/vkf-storage-private-v2')
SOURCE=HERE/'vkf-storage-private-v2'
NAMES={'vkf-storage-private-v2','vkf-storage-pre-v2'}
V2_RAW={'vkf-storage-pre-v2': 'f37275a125fb28ef09822bf730a2208f8364aa7fd86b12b7c4be79a66e3f2c95', 'vkf-storage-private-v2': '7c8190cec6f88e47c77c7faeb4024be24f114451e4262505ad670bd6f137c329'}
POLICY_SHA='8bd0a67dd92c2b7504d6c5c62ace5a450afc439f8ff3ae73f9c0bceb722b4029'
BINARY_SHA='41c65e55107cbbb1a1f6994784a938dd7dbbe255d1fea6b7a58ec96eabe382ef'
COMPILED_SHA='8ee5871c01d522c165cf31dc504e02a3a997465cabab2af34ea9cbb15e2d2397'
BASE=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb')

def need(ok,message):
    if not ok:raise RuntimeError(message)

def sha(data):return hashlib.sha256(data).hexdigest()

def trusted(path,executable=False):
    path=Path(path)
    for p in (path,*path.parents):
        s=p.lstat()  # Missing path is fatal, including missing tools.
        need(not stat.S_ISLNK(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022,'untrusted '+str(p))
    s=path.stat()
    need(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and not s.st_mode&0o6000,'unsafe file '+str(path))
    need('security.capability' not in os.listxattr(path),'filecaps '+str(path))
    if executable:need(os.access(path,os.X_OK) and bool(s.st_mode&0o111),'missing execute '+str(path))

def checked_bytes(path,expected):
    data=Path(path).read_bytes();need(sha(data)==expected,'hash mismatch '+str(path));return data

def tools_present():
    # Standalone positive checks; absence never means a collision search passed.
    for p in (PYTHON,PARSER):trusted(p,True)
    need(Path(sys.executable).resolve()==PYTHON,'wrong Python')

def names_absent(text,names=NAMES):
    # Name and stack collisions both reject. No executable search tool involved.
    for line in text.splitlines():
        label=line.rsplit(' (',1)[0]
        need(not any(n in label.split('//&') for n in names),'loaded profile collision '+label)

def exact_loaded(expected):
    found={}
    for p in Path('/sys/kernel/security/apparmor/policy/profiles').iterdir():
        name=(p/'name').read_text().strip()
        if name in expected:
            need(name not in found,'duplicate loaded profile '+name)
            need((p/'mode').read_text().strip()=='enforce','non-enforce '+name)
            data=(p/'raw_data').read_bytes()
            need(sha(data)==expected[name],'loaded raw policy differs '+name)
            found[name]=sha(data)
    need(set(found)==set(expected),'missing loaded profiles')
    return found

def quiescent():
    # Root still must hold all admissions/owner publication for the entire operation.
    need(os.readlink('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')=='/dev/null','dispatcher not masked')
    for lane in 'af':
        cg=Path('/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/vkfworkers.slice')/('vkfworkers-'+lane+'.slice')
        need(cg.is_dir(),'missing lane cgroup')
        need('populated 0' in (cg/'cgroup.events').read_text().splitlines(),'populated lane')
        for p in [cg/'cgroup.procs',*cg.glob('**/cgroup.procs')]:need(not p.read_text().strip(),'lane PIDs')
    # An outside direct invocation of the dedicated binary must not race rollback.
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:label=(p/'attr/current').read_text().strip()
        except FileNotFoundError:continue  # exited PID only; permission errors fatal
        need(not any(n in label for n in NAMES),'task still using v2 '+p.name)
    # Exact live17 baseline is deliberate: no rollback deleting historical dependencies.
    pins=json.loads((OUT/'input-pins.json').read_text())
    for p in pins:
        if p['path'].endswith(('/storage-direct-v4/direct-state-v4.json','/storage-direct-v4/owners-v4.json')):
            checked_bytes(p['path'],p['sha256'])

def immutable_inputs():
    pins=json.loads((OUT/'input-pins.json').read_text())
    for p in pins:
        # Frozen v7, old system policy/binary, package tools, and exact authorities.
        checked_bytes(p['path'],p['sha256'])
    for p in json.loads((OUT/'absent-includes.json').read_text()):need(not os.path.lexists(p),'include appeared '+p)
    need(Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip()=='1','userns restriction changed')
    need(Path('/sys/kernel/security/apparmor/features/domain/fix_binfmt_elf_mmap').read_text().strip()=='yes','kernel mmap feature changed')
    exact_loaded({'vkf-storage-private-v1':'4e09156626ef69f2e3a471b51e66c07f36bab8a7d553fd2bccca0d470160413e',
                  'vkf-storage-pre-v1':'46f3f5180a2504d5f1d16acaf4bda25d739b15df985788e7e0a0fad1f5426346',
                  'bwrap':'078c26309e148c5911cde9ab79249c5742a4fadce0291861ab22c361b0158516',
                  'unpriv_bwrap':'078c26309e148c5911cde9ab79249c5742a4fadce0291861ab22c361b0158516',
                  'unprivileged_userns':'d5bed05f238f9b37db664ec499af0dd0d60f58ab01726b8bbccdd4f54d7777e0'})

def parser_args(action,path):
    return [str(PARSER),'--config-file=/dev/null',action,'--skip-cache','--jobs=1','--max-jobs=1','--zstd-compress-level=0','--base=/etc/apparmor.d',str(path)]

def run_parser(action,path,compile_only=False):
    args=parser_args(action,path)
    if compile_only:args.insert(3,'--skip-kernel-load')
    p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:out,err=p.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        p.kill();p.communicate();raise RuntimeError('parser timeout; stopped, inspect partial state')
    need(p.returncode==0,'parser failed '+err.decode(errors='replace'))
    return out

def exclusive_file(path,data,mode):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
    with os.fdopen(fd,'wb') as f:
        os.fchmod(f.fileno(),mode);f.write(data);f.flush();os.fsync(f.fileno())
    trusted(path)

def fsyncdir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)

def install():
    # All read/absence/tool/hash/parse checks precede the first mutation.
    for p in (DESTDIR,POLICY):need(not os.path.lexists(p),'destination collision '+str(p))
    names_absent(Path('/sys/kernel/security/apparmor/profiles').read_text())
    for parent in (DESTDIR.parent,POLICY.parent):
        for p in (parent,*parent.parents):
            s=p.lstat();need(stat.S_ISDIR(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022,'unsafe parent '+str(p))
    trusted('/usr/bin/unshare',True)
    binary=checked_bytes('/usr/bin/unshare',BINARY_SHA)
    policy=checked_bytes(SOURCE,POLICY_SHA)
    compiled=run_parser('--stdout',SOURCE,True);need(sha(compiled)==COMPILED_SHA,'no-load compiled hash differs')
    os.mkdir(DESTDIR,0o755);os.chmod(DESTDIR,0o755)
    exclusive_file(BINARY,binary,0o600)  # Expose execution only after loaded equality.
    exclusive_file(POLICY,policy,0o644)
    fsyncdir(DESTDIR);fsyncdir(DESTDIR.parent);fsyncdir(POLICY.parent)
    run_parser('--add',POLICY)
    exact_loaded(V2_RAW)
    checked_bytes(BINARY,BINARY_SHA);checked_bytes(POLICY,POLICY_SHA)
    os.chmod(BINARY,0o755);fsyncdir(DESTDIR)
    print('Installed exact v2 only; no source/config/admission/workload authorized.')

def rollback():
    # Full successful installation only. Partial/ambiguous installs stop for review.
    trusted(BINARY,True);trusted(POLICY)
    need({p.name for p in DESTDIR.iterdir()}=={'unshare'},'unexpected dedicated files')
    checked_bytes(BINARY,BINARY_SHA);checked_bytes(POLICY,POLICY_SHA)
    exact_loaded(V2_RAW)
    os.chmod(BINARY,0o600)  # Prevent new ordinary attachment before unload.
    run_parser('--remove',POLICY)
    names_absent(Path('/sys/kernel/security/apparmor/profiles').read_text())
    BINARY.unlink();POLICY.unlink();DESTDIR.rmdir()
    fsyncdir(DESTDIR.parent);fsyncdir(POLICY.parent)
    print('Removed exact unused v2 only; v1/v7 and all accounting preserved.')

def main():
    need(len(sys.argv)==2 and sys.argv[1] in ('install','rollback'),'exact install|rollback required')
    tools_present()
    need(os.geteuid()==0,'root setup operator required')
    lock=BASE/'capacity.lock'
    fd=os.open(lock,os.O_RDONLY|os.O_NOFOLLOW)  # Existing lock only; no file creation.
    try:
        st=os.fstat(fd)
        need(stat.S_ISREG(st.st_mode) and st.st_uid==1000 and st.st_nlink==1 and not st.st_mode&0o077,'unsafe capacity lock')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        need(st.st_ino==lock.lstat().st_ino,'capacity lock replaced')
        immutable_inputs();quiescent()
        (install if sys.argv[1]=='install' else rollback)()
    finally:
        os.close(fd)

if __name__=='__main__':main()
