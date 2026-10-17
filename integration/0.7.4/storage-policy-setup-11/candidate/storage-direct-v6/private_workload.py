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

BINARIES = [{'path': '/usr/local/libexec/vkf-storage-private-v1/unshare', 'sha256': '41c65e55107cbbb1a1f6994784a938dd7dbbe255d1fea6b7a58ec96eabe382ef'}, {'path': '/usr/bin/python3.14', 'sha256': '52e0a13e60a981d8c4b6478be2ba5176f69da07948a056bf49cf6f077e30cb41'}, {'path': '/usr/bin/bwrap', 'sha256': '523da3e7399044be5163aee6f57a77a6bef7454376e28f0a0627920bae1b76b6'}]
UNSHARE, PYTHON, BWRAP = '/usr/local/libexec/vkf-storage-private-v1/unshare', '/usr/bin/python3.14', '/usr/bin/bwrap'


POLICY_INPUTS = [{'path': '/etc/apparmor.d/vkf-storage-private-v1', 'sha256': 'a6a82dd0c9f50c296e88933645e8a8487b947dd4de6ff6e66acee2541e1a17a4'}, {'path': '/etc/apparmor.d/abi/5.0', 'sha256': '6939ba05dd5b8e4934fc8d912d22ad13f4f77710b097287a2d2d37be6cabe775'}, {'path': '/etc/apparmor.d/bwrap-userns-restrict', 'sha256': 'd61facde27707b9c47ffe47921b7273e788784484cb5530eb819e6daac1f1990'}, {'path': '/etc/apparmor.d/tunables/alias', 'sha256': 'e7b8b278db3f7aca74e0176f22cbd3adc3c89212cc9e66a90a2787b3ceee8030'}, {'path': '/etc/apparmor.d/tunables/coreutils', 'sha256': '7160a15b9dbac8280584dc122a0b5a56f6fa4e5ed50c11f165ba0b09d8c305e6'}, {'path': '/etc/apparmor.d/tunables/etc', 'sha256': '4211a2db7a81c3edea6a657f8eacdae4322235c1d766ac95a592cb6f1b43f7ee'}, {'path': '/etc/apparmor.d/tunables/global', 'sha256': 'cb2a6a5aabaeefe52053fb6517202349efc80cf8ee2059fbcd319a4f3e1eb0a0'}, {'path': '/etc/apparmor.d/tunables/home', 'sha256': '806a4e80696e3870d46d1ae99ac7fe7099680b39040c2183094a44671d83218e'}, {'path': '/etc/apparmor.d/tunables/home.d/site.local', 'sha256': 'f6f9d209f8015196f2e391ea02debcebecbf8022ececfee3a08e3973c3bb06d4'}, {'path': '/etc/apparmor.d/tunables/home.d/ubuntu', 'sha256': 'e1b3a24d2ffdcf2b02f8726941f3c6c32dee3c9222553959a335147494d74a2d'}, {'path': '/etc/apparmor.d/tunables/kernelvars', 'sha256': 'a2fa754e93a435722ea4b8b03e2bdf52bf4c029c66397b773f5e4321d6f66ea5'}, {'path': '/etc/apparmor.d/tunables/multiarch', 'sha256': '0d35e0680f4dd9085a1c64911be21e95a65d12db045bde4b4ecae22915ce53ff'}, {'path': '/etc/apparmor.d/tunables/multiarch.d/site.local', 'sha256': '731ad52936633b9a0c738605a2a08aad2357df91ca8fbe3bd2c3427d7aac240b'}, {'path': '/etc/apparmor.d/tunables/proc', 'sha256': 'd6a8ac6910ecdde3930916dcb44d7b3d3bf1cfe5a8f54728f1f599e32a26ece7'}, {'path': '/etc/apparmor.d/tunables/run', 'sha256': 'cbe2d9c99a82124d6206bfdd377895fa3dec48ee255923d2c31b71be53ab9bdd'}, {'path': '/etc/apparmor.d/tunables/share', 'sha256': '5389ddceeb78d2012f528037e5c8205535f145c906cf6266ba400d9bafea26b7'}, {'path': '/etc/apparmor.d/tunables/system', 'sha256': '84dfeb5a2239e9cb7626b8008275c5aa0602d671303f4b43b7db0eff4688b828'}, {'path': '/etc/apparmor.d/tunables/xdg-user-dirs', 'sha256': '1d92b108e04a4067333224c4dbfd19df8ca0f0deef7a28b153995e22fe8cedb7'}, {'path': '/etc/apparmor.d/tunables/xdg-user-dirs.d/site.local', 'sha256': 'd9705b1ab368e32f4cce94f2242c6947b8624985b9c6de2ab4ee01b398dc4703'}, {'path': '/etc/apparmor.d/unprivileged_userns', 'sha256': '3263abe3b090d761a525a5e8c2d62ef89a39b41ab87ba25cecc5a6d686f73e65'}]
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


def policy_gate(stage, origin):
    """Observation only; never changes credentials, policy, or namespaces."""
    raw = Path('/proc/self/status').read_text()
    status = {}
    for line in raw.splitlines():
        k, _, v = line.partition(':')
        require(k not in status, 'duplicate status field')
        status[k] = v.split()
    for k, value in (('Uid',origin['uid']),('Gid',origin['gid'])):
        require(value != 0 and status.get(k) == [str(value)]*4, 'ordinary real/effective/saved/fs identity')
    for k in ('CapInh','CapPrm','CapEff','CapAmb') + (('CapBnd',) if stage == 'post' else ()):
        require(len(status.get(k, [])) == 1 and int(status[k][0],16) == 0, 'nonzero '+k)
    require(stage in ('origin','pre','post'), 'policy stage')
    require(status.get('NoNewPrivs') == ['1' if stage == 'post' else '0'], 'unexpected NoNewPrivs')
    label = Path('/proc/self/attr/current').read_text().strip()
    if stage == 'origin':
        require(label == 'unconfined', 'origin policy changed')
    elif stage == 'pre':
        require(label == 'vkf-storage-pre-v1 (enforce)', 'pre policy transition missing')
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


def command(m, origin):
    root = m['attempt_root']
    encoded = json.dumps(origin, sort_keys=True, separators=(',', ':'))
    helper = [PYTHON, '-I', '-B', str(HERE/'private_workload.py')]
    post = [*helper, 'post', encoded, root, '--', *m['argv']]
    bwrap = [BWRAP, '--unshare-user', '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc',
             '--ro-bind', '/dev/shm', '/dev/shm',
             '--remount-ro', '/dev/pts', '--remount-ro', '/dev', '--remount-ro', '/proc',
             '--bind', root, root,
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
