"""Source-derived bwrap construction model; NOT a Linux namespace emulator.

The final tree starts at bwrap's scaffold. Source binds always read oldroot,
not a previously constructed destination. Host oldroot is detached before exec.
We model recursive imports, ancestry, remount ordering and ordinary scaffolding;
real kernel/LSM/map/FD behavior requires a fresh authorized qualification.
"""
from dataclasses import replace
import json
from pathlib import Path
import stat
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE/'frozen-v8'))
import effective_storage as es


def escape(p):
    return p.replace('\\', '\\134').replace(' ', '\\040').replace('\t', '\\011').replace('\n', '\\012')


class View:
    def __init__(self, raw):
        self.host = es.parse_mountinfo(raw)
        self.mounts = {}
        self.kinds = {}
        self.directories = set()
        self.next_id = 100000
        self.add('/', (0, 999), 'tmpfs', readonly=False, parent=99999)

    def visible(self, path):
        return max((m for m in self.mounts.values() if es.within(path, m.path)),
                   key=lambda m: (len(m.path), m.id))

    def add(self, path, dev, fstype, readonly, parent=None, root='/', kind=None):
        mid = self.next_id
        self.next_id += 1
        if parent is None:
            parent = self.visible(path).id
        self.mounts[mid] = es.Mount(mid, parent, dev, root, path, ('ro' if readonly else 'rw',), (),
                                    fstype, 'MODEL', ('rw',))
        self.kinds[mid] = kind or (stat.S_IFDIR | 0o755, (0, 0))
        return mid

    def bind(self, source, dest, readonly):
        backing = max((m for m in self.host.values() if es.within(source, m.path)),
                      key=lambda m: (len(m.path), m.id))
        mapping = {backing.id: self.add(dest, backing.dev, backing.fstype, readonly)}
        remaining = {m.id: m for m in self.host.values() if m.path != source and es.within(m.path, source)}
        while remaining:
            ready = [m for m in remaining.values() if m.parent not in remaining]
            assert ready, 'source mount cycle'
            for m in ready:
                path = dest.rstrip('/') + m.path[len(source.rstrip('/')):]
                mapping[m.id] = self.add(path, m.dev, m.fstype, readonly or m.readonly,
                                         parent=mapping.get(m.parent, mapping[backing.id]), root=m.root)
                del remaining[m.id]

    def construct(self, argv):
        # argv is the actual bwrap argv through its first command separator.
        assert argv[0] == '/usr/bin/bwrap'
        i = 1
        while i < len(argv) and argv[i] != '--':
            op = argv[i]
            if op in ('--ro-bind', '--bind'):
                self.bind(argv[i+1], argv[i+2], op == '--ro-bind')
                i += 3
            elif op == '--dev':
                assert argv[i+1] == '/dev'
                dev = self.add('/dev', (0, 1000), 'tmpfs', False)
                self.add('/dev/pts', (0, 1001), 'devpts', False, parent=dev)
                for path, rdev in es.DEVICES.items():
                    self.add(path, (0, 7), 'devtmpfs', False, parent=dev,
                             kind=(stat.S_IFCHR | 0o666, rdev))
                i += 2
            elif op == '--proc':
                self.add(argv[i+1], (0, 1002), 'proc', False)
                i += 2
            elif op == '--remount-ro':
                mid = self.visible(argv[i+1]).id
                assert self.mounts[mid].path == argv[i+1], 'remount requires exact mount'
                self.mounts[mid] = replace(self.mounts[mid], options=('ro',))
                i += 2
            elif op == '--dir':
                self.directories.add(argv[i+1])
                i += 2
            elif op == '--symlink':
                i += 3
            elif op == '--chdir':
                i += 2
            elif op in ('--unshare-user', '--unshare-pid', '--unshare-net', '--die-with-parent'):
                i += 1
            else:
                raise AssertionError('unmodeled option '+op)
        return self

    def raw(self):
        return ''.join(f'{m.id} {m.parent} {m.dev[0]}:{m.dev[1]} {escape(m.root)} {escape(m.path)} '
                       f'{",".join(m.options)} - {m.fstype} MODEL {",".join(m.super_options)}\n'
                       for m in self.mounts.values())

    def observe(self, path):
        m = self.visible(path)
        mode, rdev = self.kinds[m.id]
        return es.Observation(m.id, m.dev, m.id+100000, mode, rdev, m.readonly, 1000, 1000)


def bwrap_argv(command):
    return command[command.index('/usr/bin/bwrap'):]
