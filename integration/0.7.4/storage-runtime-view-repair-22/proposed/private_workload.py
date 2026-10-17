"""Private propagation setup and mandatory pre-payload gate; never a fallback.

Only command() is called by the service controller. unshare does not fork with
this exact argv: its PID/starttime becomes this helper, then bwrap via exec.
All descendants remain in the same service cgroup and existing wait_owned scope.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
# -I excludes cwd/PYTHONPATH; only the authenticated helper directory is added.
sys.path.insert(0, str(HERE))
from storage_paths import pinned, require
import effective_storage

BINARIES = [{'path': '/usr/local/libexec/vkf-storage-private-v2/unshare', 'sha256': '41c65e55107cbbb1a1f6994784a938dd7dbbe255d1fea6b7a58ec96eabe382ef'}, {'path': '/usr/bin/python3.14', 'sha256': '52e0a13e60a981d8c4b6478be2ba5176f69da07948a056bf49cf6f077e30cb41'}, {'path': '/usr/bin/bwrap', 'sha256': '523da3e7399044be5163aee6f57a77a6bef7454376e28f0a0627920bae1b76b6'}]
UNSHARE, PYTHON, BWRAP = '/usr/local/libexec/vkf-storage-private-v2/unshare', '/usr/bin/python3.14', '/usr/bin/bwrap'


POLICY_INPUTS = [{'path': '/etc/apparmor.d/vkf-storage-private-v2', 'sha256': '8bd0a67dd92c2b7504d6c5c62ace5a450afc439f8ff3ae73f9c0bceb722b4029'}, {'path': '/etc/apparmor.d/abi/5.0', 'sha256': '6939ba05dd5b8e4934fc8d912d22ad13f4f77710b097287a2d2d37be6cabe775'}, {'path': '/etc/apparmor.d/bwrap-userns-restrict', 'sha256': 'd61facde27707b9c47ffe47921b7273e788784484cb5530eb819e6daac1f1990'}, {'path': '/etc/apparmor.d/tunables/alias', 'sha256': 'e7b8b278db3f7aca74e0176f22cbd3adc3c89212cc9e66a90a2787b3ceee8030'}, {'path': '/etc/apparmor.d/tunables/coreutils', 'sha256': '7160a15b9dbac8280584dc122a0b5a56f6fa4e5ed50c11f165ba0b09d8c305e6'}, {'path': '/etc/apparmor.d/tunables/etc', 'sha256': '4211a2db7a81c3edea6a657f8eacdae4322235c1d766ac95a592cb6f1b43f7ee'}, {'path': '/etc/apparmor.d/tunables/global', 'sha256': 'cb2a6a5aabaeefe52053fb6517202349efc80cf8ee2059fbcd319a4f3e1eb0a0'}, {'path': '/etc/apparmor.d/tunables/home', 'sha256': '806a4e80696e3870d46d1ae99ac7fe7099680b39040c2183094a44671d83218e'}, {'path': '/etc/apparmor.d/tunables/home.d/site.local', 'sha256': 'f6f9d209f8015196f2e391ea02debcebecbf8022ececfee3a08e3973c3bb06d4'}, {'path': '/etc/apparmor.d/tunables/home.d/ubuntu', 'sha256': 'e1b3a24d2ffdcf2b02f8726941f3c6c32dee3c9222553959a335147494d74a2d'}, {'path': '/etc/apparmor.d/tunables/kernelvars', 'sha256': 'a2fa754e93a435722ea4b8b03e2bdf52bf4c029c66397b773f5e4321d6f66ea5'}, {'path': '/etc/apparmor.d/tunables/multiarch', 'sha256': '0d35e0680f4dd9085a1c64911be21e95a65d12db045bde4b4ecae22915ce53ff'}, {'path': '/etc/apparmor.d/tunables/multiarch.d/site.local', 'sha256': '731ad52936633b9a0c738605a2a08aad2357df91ca8fbe3bd2c3427d7aac240b'}, {'path': '/etc/apparmor.d/tunables/proc', 'sha256': 'd6a8ac6910ecdde3930916dcb44d7b3d3bf1cfe5a8f54728f1f599e32a26ece7'}, {'path': '/etc/apparmor.d/tunables/run', 'sha256': 'cbe2d9c99a82124d6206bfdd377895fa3dec48ee255923d2c31b71be53ab9bdd'}, {'path': '/etc/apparmor.d/tunables/share', 'sha256': '5389ddceeb78d2012f528037e5c8205535f145c906cf6266ba400d9bafea26b7'}, {'path': '/etc/apparmor.d/tunables/system', 'sha256': '84dfeb5a2239e9cb7626b8008275c5aa0602d671303f4b43b7db0eff4688b828'}, {'path': '/etc/apparmor.d/tunables/xdg-user-dirs', 'sha256': '1d92b108e04a4067333224c4dbfd19df8ca0f0deef7a28b153995e22fe8cedb7'}, {'path': '/etc/apparmor.d/tunables/xdg-user-dirs.d/site.local', 'sha256': 'd9705b1ab368e32f4cce94f2242c6947b8624985b9c6de2ab4ee01b398dc4703'}, {'path': '/etc/apparmor.d/unprivileged_userns', 'sha256': '3263abe3b090d761a525a5e8c2d62ef89a39b41ab87ba25cecc5a6d686f73e65'}]
ABSENT_INCLUDES = ['/etc/apparmor.d/local/bwrap-userns-restrict', '/etc/apparmor.d/local/unpriv_bwrap', '/etc/apparmor.d/local/unprivileged_userns', '/etc/apparmor.d/tunables/alias.d', '/etc/apparmor.d/tunables/coreutils.d', '/etc/apparmor.d/tunables/etc.d', '/etc/apparmor.d/tunables/global.d', '/etc/apparmor.d/tunables/kernelvars.d', '/etc/apparmor.d/tunables/proc.d', '/etc/apparmor.d/tunables/run.d', '/etc/apparmor.d/tunables/share.d', '/etc/apparmor.d/tunables/system.d']


def trusted_system_file(path):
    """No symlink, privileged bits, filecaps or non-root-writable system input."""
    import stat
    path = Path(path)
    for p in (path, *path.parents):
        s = p.lstat()
        require(not stat.S_ISLNK(s.st_mode) and s.st_uid == 0
                and not s.st_mode & 0o022, 'untrusted system path '+str(p))
    s = path.stat()
    require(stat.S_ISREG(s.st_mode) and not s.st_mode & 0o6000, 'privileged system input')
    require('security.capability' not in os.listxattr(path), 'file capabilities forbidden')


def _security_snapshot():
    """Best-effort diagnostic only; any read/parse error is a hard gate failure."""
    result = dict(status={}, label=None, errors=[])
    try:
        raw = Path('/proc/self/status').read_text()
        for line in raw.splitlines():
            k, _, v = line.partition(':')
            require(k not in result['status'], 'duplicate status field')
            result['status'][k] = v.split()
    except Exception as error:
        result['errors'].append(type(error).__name__+': '+str(error))
    try:
        result['label'] = Path('/proc/self/attr/current').read_text().strip()
    except Exception as error:
        result['errors'].append(type(error).__name__+': '+str(error))
    return result


def _security_diagnostic(kind, observation, **details):
    fields = ('Uid','Gid','Groups','Threads','CapInh','CapPrm','CapEff',
              'CapAmb','CapBnd','NoNewPrivs')
    print(json.dumps(dict(private_workload_security=kind,
        status={k:observation['status'].get(k) for k in fields},
        label=observation['label'], observation_errors=observation['errors'],
        **details)), flush=True)


def _drop_capabilities():
    """Linux x86-64 LP64 libc capset(v3, pid=0): two ZERO u32 triples.

    No syscall-number fallback, cap grants, prctl, credential or bounding-set
    mutation. capset changes only the calling thread; the caller checks that
    it is the sole thread. Clearing I/P also clears any ambient intersection.
    """
    import ctypes
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64'
            and sys.byteorder == 'little' and ctypes.sizeof(ctypes.c_void_p) == 8
            and ctypes.sizeof(ctypes.c_long) == 8 and ctypes.sizeof(ctypes.c_int) == 4,
            'unsupported capability ABI (Linux x86-64 LP64 required)')

    class Header(ctypes.Structure):
        _fields_ = [('version', ctypes.c_uint32), ('pid', ctypes.c_int32)]

    class Data(ctypes.Structure):
        _fields_ = [('effective', ctypes.c_uint32), ('permitted', ctypes.c_uint32),
                   ('inheritable', ctypes.c_uint32)]

    require(ctypes.sizeof(Header) == 8 and Header.pid.offset == 4
            and ctypes.sizeof(Data) == 12 and Data.permitted.offset == 4
            and Data.inheritable.offset == 8, 'capset structure ABI')
    libc = ctypes.CDLL(None, use_errno=True)
    capset = libc.capset  # Missing symbol is fatal; never try another ABI.
    capset.argtypes = [ctypes.POINTER(Header), ctypes.POINTER(Data)]
    capset.restype = ctypes.c_int
    header = Header(0x20080522, 0)  # _LINUX_CAPABILITY_VERSION_3, current thread.
    data = (Data * 2)()  # Exactly 24 zero bytes, including bits 32..63.
    ctypes.set_errno(0)
    rc = capset(ctypes.byref(header), data)
    if rc != 0:
        err = ctypes.get_errno()
        raise OSError(err, 'capset(v3, self, zero) failed: '+os.strerror(err))


def initialize_origin_capabilities(origin):
    """Drop inherited bits once, before the independent strict origin gate.

    Unexpected active caps/IDs/NNP/label are rejected, not normalized. Leave
    CapBnd intact for namespace setup and NNP=0 for the required Px transitions.
    Diagnostics are observations, never completion/join or recovery authority.
    """
    before = _security_snapshot()
    _security_diagnostic('origin-capability-drop-before', before)
    after = None
    error = None
    try:
        require(not before['errors'], 'capability observation failed')
        status = before['status']
        for k, value in (('Uid',origin['uid']), ('Gid',origin['gid'])):
            require(value != 0 and status.get(k) == [str(value)]*4,
                    'ordinary real/effective/saved/fs identity before capability drop')
        require(status.get('Threads') == ['1']
                and os.readlink('/proc/thread-self') == f'{os.getpid()}/task/{os.getpid()}',
                'capability drop requires sole main thread')
        require(status.get('NoNewPrivs') == ['0'] and before['label'] == 'unconfined',
                'unexpected origin NNP/policy before capability drop')
        require('Groups' in status, 'missing supplementary groups')
        for k in ('CapInh','CapPrm','CapEff','CapAmb','CapBnd'):
            require(len(status.get(k, [])) == 1 and len(status[k][0]) == 16
                    and all(c in '0123456789abcdef' for c in status[k][0]),
                    'invalid capability field '+k)
        for k in ('CapPrm','CapEff','CapAmb'):
            require(int(status[k][0], 16) == 0, 'unexpected active '+k+' before drop')
        _drop_capabilities()
        after = _security_snapshot()
        require(not after['errors'], 'post-drop capability observation failed')
        for k in ('Uid','Gid','Groups','Threads','CapBnd','NoNewPrivs'):
            require(after['status'].get(k) == status[k], 'capability drop changed '+k)
        require(after['label'] == before['label'], 'capability drop changed policy')
        for k in ('CapInh','CapPrm','CapEff','CapAmb'):
            require(after['status'].get(k) == ['0000000000000000'],
                    'nonzero/missing '+k+' after capability drop')
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
        raise
    finally:
        if after is None:
            after = _security_snapshot()
        _security_diagnostic('origin-capability-drop-after', after,
                             passed=error is None, error=error)


def policy_gate(stage, origin):
    """Observation only; never changes credentials, policy, or namespaces."""
    observation = _security_snapshot()
    # Emit even when a strict identity/capability/NNP/label check below rejects.
    _security_diagnostic('policy-gate', observation, stage=stage)
    require(not observation['errors'], 'policy observation failed')
    status = observation['status']
    for k, value in (('Uid',origin['uid']),('Gid',origin['gid'])):
        require(value != 0 and status.get(k) == [str(value)]*4, 'ordinary real/effective/saved/fs identity')
    for k in ('CapInh','CapPrm','CapEff','CapAmb') + (('CapBnd',) if stage == 'post' else ()):
        require(len(status.get(k, [])) == 1 and int(status[k][0],16) == 0, 'nonzero '+k)
    require(stage in ('origin','pre','post'), 'policy stage')
    require(status.get('NoNewPrivs') == ['1' if stage == 'post' else '0'], 'unexpected NoNewPrivs')
    label = observation['label']
    if stage == 'origin':
        require(label == 'unconfined', 'origin policy changed')
    elif stage == 'pre':
        require(label == 'vkf-storage-pre-v2 (enforce)', 'pre policy transition missing')
    else:
        # Kernel label components are sorted, duplicates collapsed. No namespaces,
        # complain, unconfined or additional profiles are accepted here.
        require(label.endswith(' (enforce)') and
                set(label[:-10].split('//&')) == {'bwrap','unpriv_bwrap'} and
                len(label[:-10].split('//&')) == 2, 'payload capability-denial stack missing')
    return dict(stage=stage, label=label, status={k:status[k] for k in
        ('Uid','Gid','CapInh','CapPrm','CapEff','CapAmb','CapBnd','NoNewPrivs')})


def verify_dependencies():
    require([p['path'] for p in BINARIES] == [UNSHARE, PYTHON, BWRAP], 'exact binary contract')
    require(Path(sys.executable).resolve() == Path(PYTHON), 'executing interpreter contract')
    for p in BINARIES:
        pinned(p)
        trusted_system_file(p['path'])
    for p in POLICY_INPUTS:
        pinned(p)
        trusted_system_file(p['path'])
    for p in ABSENT_INCLUDES:
        require(not os.path.lexists(p), 'policy include appeared '+p)
    require(Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip() == '1',
            'userns restriction changed')


def context():
    lines = Path('/proc/self/cgroup').read_text().splitlines()
    require(len(lines) == 1 and lines[0].startswith('0::/'), 'unified service cgroup required')
    return dict(cgroup=lines[0][3:], uid=os.getuid(), gid=os.getgid(),
                namespaces={n:os.readlink('/proc/self/ns/'+n) for n in ('mnt','user','pid','net')})


# This is a construction contract, never an effective-storage exception list.
# Do not import the host root: recursive binds preserve inaccessible submounts.
RUNTIME_READ_TREES = ('/usr', '/etc', '/home', '/mnt')
RUNTIME_LINKS = (('/bin', 'usr/bin'), ('/sbin', 'usr/sbin'),
                 ('/lib', 'usr/lib'), ('/lib32', 'usr/lib32'),
                 ('/lib64', 'usr/lib64'))


def runtime_view(m):
    """Use bwrap's private scaffold; freeze it after all setup operations.

    Host controller/custody remains outside this workload-only view. No host
    /run, /var or /sys mount tree is copied, and no immutable empty host source
    or new privileged helper is needed. All imported submounts remain subject
    to the unchanged strict post gate, including unknown/inaccessible ones.
    """
    import stat
    for source in RUNTIME_READ_TREES:
        require(stat.S_ISDIR(Path(source).lstat().st_mode), 'view source directory '+source)
    for path, target in RUNTIME_LINKS:
        require(Path(path).is_symlink() and os.readlink(path) == target,
                'view compatibility symlink changed '+path)
    # The manifest inputs have already passed controller pin validation. Check
    # their nominal AND resolved locations so a new /run or /var dependency
    # cannot silently disappear. No discovery, fallback bind or permission fix.
    reads = [p['path'] for p in m['inputs']] + [p['path'] for p in BINARIES + POLICY_INPUTS]
    reads += [str(HERE/'private_workload.py'), str(HERE/'effective_storage.py'),
              str(HERE/'storage_paths.py'), m['argv'][0]]
    read_trees = (*RUNTIME_READ_TREES, '/dev/shm')
    for value in reads:
        require(Path(value).is_absolute(), 'absolute view input required')
        nominal = os.path.normpath(value)
        for link, target in RUNTIME_LINKS:
            if effective_storage.within(nominal, link):
                nominal = '/'+target+nominal[len(link):]
                break
        resolved = str(Path(value).resolve(strict=True))
        require(all(any(effective_storage.within(p, tree) for tree in read_trees)
                    for p in (nominal, resolved)), 'input outside runtime read view '+value)
    require(effective_storage.within(m['attempt_root'], '/mnt'), 'attempt outside retained /mnt')
    argv = []
    for source in RUNTIME_READ_TREES:
        argv += ['--ro-bind', source, source]
    for path, target in RUNTIME_LINKS:
        argv += ['--symlink', target, path]
    # These are ordinary empty directories in the single private scaffold;
    # root's final --remount-ro also makes all three read-only.
    argv += ['--dir', '/run', '--dir', '/var', '--dir', '/tmp']
    return argv


def command(m, origin):
    root = m['attempt_root']
    encoded = json.dumps(origin, sort_keys=True, separators=(',', ':'))
    helper = [PYTHON, '-I', '-B', str(HERE/'private_workload.py')]
    post = [*helper, 'post', encoded, root, '--', *m['argv']]
    bwrap = [BWRAP, '--unshare-user', *runtime_view(m), '--dev', '/dev', '--proc', '/proc',
             '--ro-bind', '/dev/shm', '/dev/shm',
             '--remount-ro', '/dev/pts', '--remount-ro', '/dev', '--remount-ro', '/proc',
             '--bind', root, root,
             '--remount-ro', '/',  # Last mount operation; no writable scaffold survives.
             '--unshare-pid', '--unshare-net', '--die-with-parent', '--chdir', m['cwd'],
             '--', *post]
    return [UNSHARE, '--user', '--map-current-user', '--mount', '--propagation', 'private',
            '--', *helper, 'pre', encoded, root, '--', *bwrap]


def private_snapshot(raw):
    mounts = effective_storage.parse_mountinfo(raw)
    require(sum(m.parent not in mounts for m in mounts.values()) == 1, 'disconnected mount roots')
    # PRIVATE has no shared/master/propagate_from/unbindable optional field.
    require(all(not m.optional for m in mounts.values()), 'workload tree is not entirely private')
    return len(mounts)


def gate(stage, origin, attempt, argv):
    require(stage in ('pre', 'post') and argv and Path(argv[0]).is_absolute(), 'private gate command')
    verify_dependencies()
    security = policy_gate(stage, origin)
    now = context()
    require(now['cgroup'] == origin['cgroup'] and origin['cgroup'].endswith('.service'), 'wrapper cgroup changed')
    require(now['uid'] == origin['uid'] != 0 and now['gid'] == origin['gid'], 'wrapper identity changed')
    for n in ('mnt','user','pid','net'):
        changed = now['namespaces'][n] != origin['namespaces'][n]
        require(changed == (stage == 'post' or n in ('mnt','user')), 'wrapper namespace '+n)
    if stage == 'pre':
        require(argv[0] == BWRAP, 'pre gate must exec bwrap')
        for kind, value in (('uid',origin['uid']), ('gid',origin['gid'])):
            fields = Path('/proc/self/'+kind+'_map').read_text().split()
            require(fields == [str(value), str(value), '1'], 'single current-user mapping required')
    raw = Path('/proc/self/mountinfo').read_text()
    print(json.dumps(dict(private_workload_snapshot=stage, context=now, policy=security,
        sha256=hashlib.sha256(raw.encode()).hexdigest(), mountinfo=raw)), flush=True)
    count = private_snapshot(raw)
    if stage == 'post':
        # Preserve the strict effective-storage checker unchanged; a future
        # payload cannot bypass it simply by omitting the qualification fixture.
        report = effective_storage.check(raw, attempt)
        require(Path('/proc/self/mountinfo').read_text() == raw, 'mount topology changed at payload gate')
        print(json.dumps(dict(private_workload_postcondition=True, mounts=count,
                              private_workload_storage=report)), flush=True)
    else:
        print(json.dumps(dict(private_workload_precondition=True, mounts=count)), flush=True)
    os.execv(argv[0], argv)
    raise RuntimeError('exec unexpectedly returned')


def main(argv):
    require(len(argv) >= 5 and argv[3] == '--', 'exact gate argument shape')
    gate(argv[0], json.loads(argv[1]), argv[2], argv[4:])


if __name__ == '__main__':
    main(sys.argv[1:])
