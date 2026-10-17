"""Fail-closed mount qualification, not a general sandbox/security boundary.

No permission probes or write opens. O_PATH + fdinfo binds observations to the
actual mount, fstat to its object, and statvfs through that pinned descriptor to
its effective read-only flag. Unknown/inaccessible topology is a failure.
"""
from dataclasses import dataclass, asdict
import hashlib
import os
from pathlib import Path
import re
import stat

class Rejected(RuntimeError):
    pass

def need(ok, why):
    if not ok:
        raise Rejected(why)

def unescape(value):
    # Kernel seq_escape uses these four octal escapes. Single pass: \\134040
    # means literal backslash + 040, never a space. Do not unicode_escape.
    escapes = {'040': ' ', '011': '\t', '012': '\n', '134': '\\'}
    need(not re.search(r'\\(?!040|011|012|134)', value), 'unknown mountinfo escape')
    return re.sub(r'\\(040|011|012|134)', lambda m: escapes[m[1]], value)

def canonical(path):
    need(isinstance(path, str) and path.startswith('/') and '\0' not in path,
         'absolute non-NUL path required')
    need(path == '/' or all(p not in ('', '.', '..') for p in path[1:].split('/')),
         'noncanonical path')
    return path

def within(path, parent):
    return parent == '/' or path == parent or path.startswith(parent + '/')

@dataclass(frozen=True)
class Mount:
    id: int
    parent: int
    dev: tuple
    root: str
    path: str
    options: tuple
    optional: tuple
    fstype: str
    source: str
    super_options: tuple

    @property
    def readonly(self):
        return 'ro' in self.options or 'ro' in self.super_options


def parse_mountinfo(raw):
    mounts = {}
    for line in raw.split('\n'):
        if not line:
            continue
        need(line.count(' - ') == 1, 'mountinfo separator')
        left, right = line.split(' - ')
        a, b = left.split(' '), right.split(' ')
        need(len(a) >= 6 and len(b) == 3 and all(a+b), 'mountinfo fields')
        need(all(re.fullmatch(r'[0-9]+', v) for v in a[:2])
             and re.fullmatch(r'[0-9]+:[0-9]+', a[2]), 'mountinfo IDs')
        mid, parent = map(int, a[:2])
        need(mid > 0 and parent > 0 and mid != parent and mid not in mounts, 'duplicate/self mount ID')
        opts, sup = tuple(a[5].split(',')), tuple(b[2].split(','))
        for o in (opts, sup):
            need(('ro' in o) != ('rw' in o), 'missing/conflicting mount access flags')
        mounts[mid] = Mount(mid, parent, tuple(map(int, a[2].split(':'))),
            unescape(a[3]), canonical(unescape(a[4])), opts, tuple(a[6:]),
            b[0], unescape(b[1]), sup)
    need(mounts, 'empty mount table')
    for m in mounts.values():
        seen = set()
        p = m
        while True:
            need(p.id not in seen, 'mount parent cycle')
            seen.add(p.id)
            if p.parent not in mounts:
                need(p.path == '/', 'missing non-root mount parent')
                break
            parent = mounts[p.parent]
            need(within(p.path, parent.path), 'mount parent path mismatch')
            p = parent
    return mounts

@dataclass(frozen=True)
class Observation:
    mount_id: int
    dev: tuple
    ino: int
    mode: int
    rdev: tuple
    readonly: bool
    uid: int
    gid: int


def open_path(path):
    """Component-wise O_NOFOLLOW, including intermediate symlinks; caller closes."""
    canonical(path)
    fd = os.open('/', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in ([] if path == '/' else path[1:].split('/')):
            new = os.open(part, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = new
            need(not stat.S_ISLNK(os.fstat(fd).st_mode), 'symlink path: '+path)
        return fd
    except BaseException:
        os.close(fd)
        raise


def observe_fd(fd):
    s = os.fstat(fd)
    lines = Path(f'/proc/self/fdinfo/{fd}').read_text().splitlines()
    ids = [x.split(':', 1)[1].strip() for x in lines if x.startswith('mnt_id:')]
    need(len(ids) == 1 and ids[0].isdigit(), 'fdinfo mount ID missing')
    # fstatvfs(O_PATH) is not portable across kernels. This proc magic link
    # refers to our still-open FD, not a fresh lookup of an untrusted path.
    v = os.statvfs(f'/proc/self/fd/{fd}')
    return Observation(int(ids[0]), (os.major(s.st_dev), os.minor(s.st_dev)),
        s.st_ino, s.st_mode, (os.major(s.st_rdev), os.minor(s.st_rdev)),
        bool(v.f_flag & os.ST_RDONLY), s.st_uid, s.st_gid)


def observe(path):
    fd = open_path(path)
    try:
        return observe_fd(fd)
    finally:
        os.close(fd)


# These are identities of the six bwrap --dev character bindings, NOT a mount
# name/fstype filter. Directories, regular files, block devices and other rdevs
# at these paths fail. No write call to a character device is made here.
DEVICES = {'/dev/null': (1,3), '/dev/zero': (1,5), '/dev/full': (1,7),
           '/dev/random': (1,8), '/dev/urandom': (1,9), '/dev/tty': (5,0)}


def check(raw, attempt, inspect=observe):
    canonical(attempt)
    need(attempt != '/', 'attempt cannot be root')
    mounts = parse_mountinfo(raw)
    need(sum(m.parent not in mounts for m in mounts.values()) == 1, 'disconnected mount roots')
    for m in mounts.values():
        need(not any(x.startswith(('shared:', 'master:', 'propagate_from:')) for x in m.optional),
             'propagating mount topology')
    points = sorted({m.path for m in mounts.values()}, key=lambda p:(p.count('/'), p))
    cache, rows = {}, []
    def obs(path):
        if path not in cache:
            try:
                o = inspect(path)
            except (OSError, ValueError) as e:
                raise Rejected(f'unresolved mount path {path!r}: {e!r}') from e
            need(o.mount_id in mounts, 'FD mount absent from snapshot: '+path)
            actual = mounts[o.mount_id]
            need(within(path, actual.path) and o.dev == actual.dev, 'mount identity/path mismatch: '+path)
            need(o.readonly == actual.readonly, 'mount flags/statvfs disagreement: '+path)
            need(not stat.S_ISLNK(o.mode), 'symlink mount object')
            cache[path] = o
        return cache[path]
    for m in sorted(mounts.values(), key=lambda m:m.id):
        ancestors = {m.id}
        p = m
        while p.parent in mounts:
            p = mounts[p.parent]; ancestors.add(p.id)
        cover = None
        for point in points:
            if not within(m.path, point):
                continue
            o = obs(point)
            if o.mount_id not in ancestors:
                # First divergent, actually resolved mount blocks this row's
                # ancestry. Never reach through a hidden subtree to probe it.
                cover = dict(path=point, mount_id=o.mount_id)
                break
        if cover:
            rows.append(dict(id=m.id, path=m.path, result='hidden', cover=cover))
            continue
        o = obs(m.path)
        need(o.mount_id == m.id, 'unresolved stack at '+m.path)
        if stat.S_ISCHR(o.mode):
            need(DEVICES.get(m.path) == o.rdev, 'unapproved character device: '+m.path)
            result = 'character-device'
        else:
            need(stat.S_ISDIR(o.mode) or stat.S_ISREG(o.mode), 'unexpected mount object type: '+m.path)
            if o.readonly:
                result = 'readonly'
            else:
                need(m.path == attempt and stat.S_ISDIR(o.mode),
                     'reachable writable filesystem outside exact attempt mount: '+m.path)
                result = 'charged-attempt'
        rows.append(dict(id=m.id, path=m.path, result=result, observation=asdict(o)))
    allowed = [r for r in rows if r['result'] == 'charged-attempt']
    need(len(allowed) == 1, 'exactly one reachable charged attempt required')
    return dict(mountinfo_sha256=hashlib.sha256(raw.encode('utf-8', 'surrogateescape')).hexdigest(),
                attempt_mount_id=allowed[0]['id'], rows=rows)


def qualify(attempt):
    path = Path('/proc/self/mountinfo')
    raw = path.read_text(errors='surrogateescape')
    result = check(raw, attempt, observe)
    need(path.read_text(errors='surrogateescape') == raw, 'mount table changed during inspection')
    # Re-resolve reachable mountpoints: detect changed object/flags as well as
    # changes in the table. No concurrent hostile rename/mount actor is admitted.
    for row in result['rows']:
        if 'observation' in row:
            need(asdict(observe(row['path'])) == row['observation'], 'mount object changed')
    need(path.read_text(errors='surrogateescape') == raw, 'mount table changed during recheck')
    return result
