"""Linux, source-only candidate. No mkdir, mounts, services or allocation helpers."""
import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path


class Rejected(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Rejected(message)


@contextmanager
def directory(path):
    """Walk every component with O_NOFOLLOW; caller must protect ancestors."""
    path = str(path)
    require(path.startswith('/') and str(Path(path)) == path
            and '..' not in Path(path).parts, 'noncanonical absolute path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in Path(path).parts[1:]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def mount_id(fd):
    return int(next(line.split()[1] for line in
                    Path(f'/proc/self/fdinfo/{fd}').read_text().splitlines()
                    if line.startswith('mnt_id:')))


def unescape(value):
    return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), value)


def identity(path):
    with directory(path) as fd:
        s, v, mid = os.fstat(fd), os.fstatvfs(fd), mount_id(fd)
        rows = [line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines()]
        row = next(r for r in rows if int(r[0]) == mid)
        sep = row.index('-')
        require(row[sep + 1] == 'ext4', 'direct mode requires reviewed ext4')
        uuids = []
        for link in Path('/dev/disk/by-uuid').iterdir():
            try:
                if link.stat().st_rdev == s.st_dev:
                    uuids.append(link.name)
            except FileNotFoundError:
                continue
        require(len(uuids) == 1, 'ambiguous or absent filesystem UUID')
        return dict(path=str(path), dev=s.st_dev, ino=s.st_ino, uid=s.st_uid,
                    gid=s.st_gid, uuid=uuids[0], size=v.f_blocks*v.f_frsize,
                    mount_id=mid, source=unescape(row[sep + 2]),
                    mount_target=unescape(row[4]), mount_root=unescape(row[3]),
                    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip())


def allocated(path):
    """Allocated blocks, including directories; reject links and nested mounts."""
    with directory(path) as fd:
        dev, mid = os.fstat(fd).st_dev, mount_id(fd)

        def walk(current):
            s = os.fstat(current)
            require(s.st_dev == dev and mount_id(current) == mid, 'nested mount')
            total = s.st_blocks * 512
            with os.scandir(current) as entries:
                for entry in entries:
                    before = entry.stat(follow_symlinks=False)
                    require(stat.S_ISDIR(before.st_mode) or stat.S_ISREG(before.st_mode),
                            'symlink or special file')
                    child = os.open(entry.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                    dir_fd=current)
                    try:
                        after = os.fstat(child)
                        require((before.st_dev, before.st_ino, before.st_mode) ==
                                (after.st_dev, after.st_ino, after.st_mode), 'entry replaced')
                        require(after.st_dev == dev and mount_id(child) == mid, 'nested mount')
                        if stat.S_ISDIR(after.st_mode):
                            total += walk(child)
                        else:
                            require(after.st_nlink == 1, 'unaccounted hardlink')
                            total += after.st_blocks * 512
                    finally:
                        os.close(child)
            return total
        return walk(fd)


def contained(root, path):
    """Existing parents must be safe; missing suffix permitted for future outputs."""
    root, path = Path(root), Path(path)
    require(path.is_absolute() and '..' not in path.parts and path.is_relative_to(root),
            'path escapes attempt')
    with directory(root) as fd:
        mid = mount_id(fd)
        current = os.dup(fd)
        try:
            for name in path.relative_to(root).parts:
                try:
                    child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                    dir_fd=current)
                except FileNotFoundError:
                    break
                os.close(current)
                current = child
                s = os.fstat(current)
                require(mount_id(current) == mid, 'nested mount')
                require(stat.S_ISDIR(s.st_mode) or
                        (stat.S_ISREG(s.st_mode) and s.st_nlink == 1), 'unsafe output')
        finally:
            os.close(current)


def pinned(pin):
    """Pin bytes read through no-follow parent/file descriptors (trusted pin issuer)."""
    p = Path(pin['path'])
    with directory(p.parent) as parent:
        fd = os.open(p.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as f:
            require(stat.S_ISREG(os.fstat(f.fileno()).st_mode), 'pin is not regular')
            data = f.read()
    require(hashlib.sha256(data).hexdigest() == pin['sha256'], 'source pin mismatch')
    return data


def pinned_json(pin):
    return strict_json(pinned(pin))


def strict_json(raw):
    def pairs(items):
        value = {}
        for k,v in items:
            require(k not in value, 'duplicate JSON key')
            value[k] = v
        return value
    def constant(value):
        raise Rejected('nonfinite JSON constant')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
