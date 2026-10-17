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

BINARIES = [{'path': '/usr/bin/unshare', 'sha256': '41c65e55107cbbb1a1f6994784a938dd7dbbe255d1fea6b7a58ec96eabe382ef'}, {'path': '/usr/bin/python3.14', 'sha256': '52e0a13e60a981d8c4b6478be2ba5176f69da07948a056bf49cf6f077e30cb41'}, {'path': '/usr/bin/bwrap', 'sha256': '523da3e7399044be5163aee6f57a77a6bef7454376e28f0a0627920bae1b76b6'}]
UNSHARE, PYTHON, BWRAP = '/usr/bin/unshare', '/usr/bin/python3.14', '/usr/bin/bwrap'


def verify_dependencies():
    require([p['path'] for p in BINARIES] == [UNSHARE, PYTHON, BWRAP], 'exact binary contract')
    require(Path(sys.executable).resolve() == Path(PYTHON), 'executing interpreter contract')
    for p in BINARIES:
        pinned(p)
        require(not (Path(p['path']).stat().st_mode & 0o6000), 'unexpected privileged binary')


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
    print(json.dumps(dict(private_workload_snapshot=stage, context=now,
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
