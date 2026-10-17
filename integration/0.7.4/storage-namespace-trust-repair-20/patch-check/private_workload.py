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


HOST_NAMESPACE_ANCHOR = {'boot': '36e567a7-0fa2-44a9-b95d-d93702c4b628', 'namespaces': {'mnt': 'mnt:[4026531832]', 'user': 'user:[4026531837]', 'pid': 'pid:[4026531836]', 'net': 'net:[4026531833]', 'cgroup': 'cgroup:[4026531835]'}}

# Host-authenticated trust protocol. No receipt file or caller-supplied trust bit.
# The admitted controller alone owns the reply writer. This transport is scoped
# to its Popen child and existing wait_owned guard, never a standalone admission.
import fcntl
import stat
import time
from contextlib import contextmanager
from storage_paths import strict_json

NS_NAMES = ('mnt', 'user', 'pid', 'net', 'cgroup')
NS_GET_USERNS, NS_GET_PARENT = 0xb701, 0xb702
MAX_FRAME = 262144
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
               'st_size', 'st_mtime_ns', 'st_ctime_ns')
IDENTITY_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_ctime_ns')


def stat_record(s):
    return {k: getattr(s, k) for k in STAT_FIELDS}


def single_map(raw, inside, outside):
    # Exactly one nonempty decimal row. No overlaps, duplicate rows, sign,
    # zero lengths, truncation, overflow, or implicit identity-map fallback.
    lines = raw.splitlines()
    require(len(lines) == 1, 'map row count')
    fields = lines[0].split()
    require(len(fields) == 3 and all(x.isascii() and x.isdecimal() for x in fields),
            'malformed map')
    values = [int(x) for x in fields]
    require(all(0 <= x < 2**32-1 for x in values), 'map range')
    require(values == [inside, outside, 1], 'unexpected single-ID map')
    return values


def _bounded_read(path, limit=8192):
    with open(path, 'rb') as stream:
        raw = stream.read(limit+1)
    require(len(raw) <= limit, 'observation exceeds bound')
    return raw.decode()


def _proc_context(pid='self'):
    base = Path('/proc')/str(pid)
    lines = _bounded_read(base/'cgroup').splitlines()
    require(len(lines) == 1 and lines[0].startswith('0::/'), 'unified service cgroup required')
    status = dict(line.split(':', 1) for line in _bounded_read(base/'status').splitlines())
    return dict(cgroup=lines[0][3:], uid=int(status['Uid'].split()[0]),
                gid=int(status['Gid'].split()[0]),
                namespaces={n: os.readlink(base/'ns'/n) for n in NS_NAMES},
                maps={k: _bounded_read(base/(k+'_map')) for k in ('uid','gid')},
                overflow={k: int(_bounded_read('/proc/sys/kernel/overflow'+k).strip())
                          for k in ('uid','gid')},
                boot=_bounded_read('/proc/sys/kernel/random/boot_id').strip())


def trust_observation(root_fd=None, mountinfo=None):
    """Bounded exact inputs only; lstat BEFORE any trust/dependency rejection.

    Each no-follow walk records actual fields, errors and same-descriptor bytes.
    The host may anchor this walk at a verified live child's /proc/PID/root.
    """
    result = dict(paths={}, files={}, errors=[], root_mount=None)
    root = os.open('/', os.O_RDONLY|os.O_DIRECTORY) if root_fd is None else os.dup(root_fd)
    try:
        try:
            from storage_paths import mount_id
            mid = mount_id(root)
            raw = _bounded_read('/proc/self/mountinfo', MAX_FRAME) if mountinfo is None else mountinfo
            mount = effective_storage.parse_mountinfo(raw)[mid]
            result['root_mount'] = dict(id=mid, path=mount.path, root=mount.root,
                dev=list(mount.dev), fstype=mount.fstype, options=list(mount.options),
                optional=list(mount.optional), readonly=bool(os.fstatvfs(root).f_flag & os.ST_RDONLY))
        except Exception as exc:
            result['errors'].append(dict(path='/', reason=type(exc).__name__+': '+str(exc)))
        for pin in BINARIES+POLICY_INPUTS:
            path = pin['path']; current = os.dup(root)
            try:
                result['paths']['/'] = stat_record(os.fstat(current))
                parts = Path(path).parts[1:]
                prefix = ''
                for i, name in enumerate(parts):
                    prefix += '/'+name
                    before = os.stat(name, dir_fd=current, follow_symlinks=False)
                    result['paths'][prefix] = stat_record(before)
                    flags = os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK
                    if i < len(parts)-1: flags |= os.O_DIRECTORY
                    child = os.open(name, flags, dir_fd=current)
                    os.close(current); current = child
                    require(stat_record(os.fstat(current)) == stat_record(before), 'path changed during open')
                    if i == len(parts)-1:
                        require(stat.S_ISREG(before.st_mode), 'system file type')
                        require(before.st_size <= 32*1024*1024, 'system file size bound')
                        digest = hashlib.sha256()
                        total = 0
                        while True:
                            data = os.read(current, 65536)
                            if not data: break
                            total += len(data)
                            require(total <= 32*1024*1024, 'growing system file')
                            digest.update(data)
                        caps = 'security.capability' in os.listxattr(current)
                        require(stat_record(os.fstat(current)) == stat_record(before), 'file changed while read')
                        result['files'][path] = dict(sha256=digest.hexdigest(), filecaps=caps)
            except Exception as exc:
                result['errors'].append(dict(path=path, reason=type(exc).__name__+': '+str(exc)))
            finally:
                os.close(current)
    finally:
        os.close(root)
    return result


def dependency_diagnostic(stage, observation, ctx=None, reason=None):
    # Requests are untrusted until accepted. Even a rejected/spoofed request
    # cannot turn diagnostics into an arbitrary path inventory or unbounded log.
    pins = {p['path'] for p in BINARIES+POLICY_INPUTS}
    allowed = {str(q) for path in pins for q in (Path(path), *Path(path).parents)}
    if isinstance(observation, dict):
        observation = dict(
            paths={k:{f:v for f,v in row.items() if f in STAT_FIELDS and type(v) is int}
                   for k,row in observation.get('paths', {}).items() if k in allowed and isinstance(row,dict)},
            files={k:v for k,v in observation.get('files', {}).items() if k in pins},
            root_mount=observation.get('root_mount'),
            errors=[dict(path=e.get('path'), reason=str(e.get('reason'))[:512])
                    for e in observation.get('errors', [])[:len(pins)+1]
                    if isinstance(e,dict) and e.get('path') in allowed])
    if isinstance(ctx,dict):
        ctx = {k:ctx.get(k) for k in ('cgroup','uid','gid','namespaces','maps','overflow','boot')}
    print(json.dumps(dict(private_workload_system_trust=stage, context=ctx,
                          observation=observation, reason=None if reason is None else str(reason)[:1024]),
                     sort_keys=True), flush=True)


def validate_observation(observation, *, host, scaffold_origin=None):
    require(not observation['errors'], 'system observation errors')
    pins = {p['path']: p['sha256'] for p in BINARIES+POLICY_INPUTS}
    paths = {str(q) for p in pins for q in (Path(p), *Path(p).parents)}
    require(set(observation['paths']) == paths and set(observation['files']) == set(pins),
            'exact bounded system input closure')
    if scaffold_origin is not None:
        validate_scaffold(observation, scaffold_origin)
    for path, row in observation['paths'].items():
        require(set(row) == set(STAT_FIELDS) and all(type(v) is int and v >= 0 for v in row.values()),
                'invalid lstat fields '+path)
        require(not stat.S_ISLNK(row['st_mode']) and not row['st_mode'] & 0o022,
                'symlink or writable system path '+path)
        if host and not (path == '/' and scaffold_origin is not None):
            require(row['st_uid'] == 0, 'non-root host owner '+path)
        if path in pins:
            require(stat.S_ISREG(row['st_mode']) and not row['st_mode'] & 0o6000
                    and row['st_nlink'] == 1, 'unsafe system file '+path)
        else:
            require(stat.S_ISDIR(row['st_mode']), 'non-directory system parent '+path)
    for path, digest in pins.items():
        require(observation['files'][path] == dict(sha256=digest, filecaps=False),
                'system bytes/file capabilities '+path)


def scaffold_source_contract():
    # Enabled only by separately reviewed proposal22 SOURCE composition, never
    # by a grant/context/request flag. The exact command still has to match the
    # live helper argv. Standalone proposal20 retains the frozen-v8 root bind.
    return (globals().get('RUNTIME_READ_TREES') == ('/usr','/etc','/home','/mnt')
            and callable(globals().get('runtime_view')))


def validate_scaffold(observation, origin):
    row, mount = observation['paths']['/'], observation['root_mount']
    require(row['st_mode'] == stat.S_IFDIR|0o755
            and row['st_uid'] == origin['uid'] and row['st_gid'] == origin['gid'],
            'constructed scaffold owner/type/mode')
    require(mount is not None and mount['path'] == '/' and mount['root'] == '/newroot'
            and mount['fstype'] == 'tmpfs' and mount['optional'] == []
            and set(('ro','nosuid','nodev')).issubset(mount['options'])
            and mount['readonly'] is True
            and mount['dev'] == [os.major(row['st_dev']), os.minor(row['st_dev'])],
            'constructed scaffold readonly mount proof')


def compare_host(before, after, scaffold_origin=None):
    validate_observation(after, host=True, scaffold_origin=scaffold_origin)
    for path, row in before['paths'].items():
        if path == '/' and scaffold_origin is not None:
            require((row['st_dev'],row['st_ino']) !=
                    (after['paths'][path]['st_dev'],after['paths'][path]['st_ino']),
                    'scaffold unexpectedly reuses host root')
            continue  # ONLY this constructed object has its own stricter proof.
        fields = STAT_FIELDS if path in before['files'] else IDENTITY_FIELDS+('st_uid','st_gid')
        require(all(after['paths'][path][k] == row[k] for k in fields), 'host identity changed '+path)
    require(before['files'] == after['files'], 'host bytes changed')


def compare_namespace(host, local, ctx, origin):
    validate_observation(local, host=False)
    for path, row in host['paths'].items():
        other = local['paths'][path]
        fields = STAT_FIELDS if path in host['files'] else IDENTITY_FIELDS
        for k in fields:
            if k not in ('st_uid','st_gid'):
                require(other[k] == row[k], 'namespace identity changed '+path+':'+k)
        for kind in ('uid','gid'):
            # Both approved chains compose to exactly origin ID -> same host ID.
            # The overflow number alone never authenticates ownership: host root,
            # object identity, bytes, modes and ACTUAL lineage must already pass.
            host_id = row['st_'+kind]
            expected = origin[kind] if host_id == origin[kind] else ctx['overflow'][kind]
            require(other['st_'+kind] == expected, 'namespace ownership projection '+path)
    require(local['files'] == host['files'], 'namespace bytes changed')
    require(local['root_mount'] == host['root_mount'], 'namespace root mount evidence changed')


def validate_stage_context(stage, now, origin):
    require(stage in ('pre','post'), 'trust stage')
    require(now['boot'] == origin['boot'] and now['overflow'] == origin['overflow'], 'host context changed')
    require(now['cgroup'] == origin['cgroup'] and origin['cgroup'].endswith('.service'), 'wrapper cgroup changed')
    require(now['uid'] == origin['uid'] != 0 and now['gid'] == origin['gid'] != 0, 'wrapper identity changed')
    for n in NS_NAMES:
        changed = now['namespaces'][n] != origin['namespaces'][n]
        require(changed == (n in ('mnt','user') or (stage == 'post' and n in ('pid','net'))),
                'wrapper namespace '+n)
    for kind in ('uid','gid'):
        single_map(now['maps'][kind], origin[kind], origin[kind] if stage == 'pre' else 0)


def _process(pid):
    base = Path('/proc')/str(pid)
    fields = _bounded_read(base/'stat').rsplit(')', 1)[1].split()
    return dict(pid=pid, starttime=int(fields[19]), ppid=int(fields[1]),
                executable=os.readlink(base/'exe'),
                argv=_bounded_read(base/'cmdline', 65536).rstrip('\0').split('\0'),
                context=_proc_context(pid))


def _descendant(pid, leader):
    for _ in range(128):
        p = _process(pid)
        if pid == leader['pid']:
            return p['starttime'] == leader['starttime']
        if p['ppid'] <= 1 or p['ppid'] == pid: return False
        pid = p['ppid']
    return False


def _ns_identity(fd):
    s = os.fstat(fd)
    return (s.st_dev, s.st_ino)


@contextmanager
def _related(fd, op):
    related = fcntl.ioctl(fd, op)
    try: yield related
    finally: os.close(related)


def lineage(stage, fds, host, pre):
    """Only the outside controller calls ioctls; children do not walk ancestors."""
    ident = lambda name: _ns_identity(fds[name])
    require(ident('cgroup') == _ns_identity(host['cgroup']), 'cgroup namespace changed')
    if stage == 'pre':
        with _related(fds['user'], NS_GET_PARENT) as parent:
            require(_ns_identity(parent) == _ns_identity(host['user']), 'pre user parent')
        with _related(fds['mnt'], NS_GET_USERNS) as owner:
            require(_ns_identity(owner) == ident('user'), 'pre mount owner')
        for n in ('pid','net'):
            require(ident(n) == _ns_identity(host[n]), 'pre '+n+' changed')
        require(ident('mnt') != _ns_identity(host['mnt']), 'pre mount unchanged')
    else:
        require(pre is not None, 'post without authenticated pre')
        # final -> intermediate(devpts root mapping) -> pre -> host.
        with _related(fds['user'], NS_GET_PARENT) as intermediate:
            require(_ns_identity(intermediate) not in
                    (_ns_identity(host['user']), _ns_identity(pre['user']), ident('user')),
                    'missing bwrap intermediate user namespace')
            with _related(intermediate, NS_GET_PARENT) as parent:
                require(_ns_identity(parent) == _ns_identity(pre['user']), 'intermediate parent')
            for n in ('mnt','pid','net'):
                require(ident(n) != _ns_identity(pre[n]), 'post '+n+' unchanged')
                with _related(fds[n], NS_GET_USERNS) as owner:
                    require(_ns_identity(owner) == _ns_identity(intermediate), 'post '+n+' owner')
        with _related(fds['pid'], NS_GET_PARENT) as parent:
            require(_ns_identity(parent) == _ns_identity(host['pid']), 'post pid parent')
    return {n: list(ident(n)) for n in NS_NAMES}


def _frame(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()+b'\n'
    require(len(raw) <= MAX_FRAME, 'trust frame bound')
    return raw


def _write_all(fd, raw):
    while raw:
        count = os.write(fd, raw)
        require(count > 0, 'trust pipe short write')
        raw = raw[count:]


def namespace_trust(stage, origin, attempt, argv, now, observation):
    # These are transport handles, not a trust override. The admitted controller
    # independently validates the live process, exact argv and every observation.
    channel = origin['trust_channel']
    require(set(channel) == {'request_fd','reply_fd','nonce'}, 'trust channel shape')
    request_fd, reply_fd = channel['request_fd'], channel['reply_fd']
    for fd, mode in ((request_fd, os.O_WRONLY), (reply_fd, os.O_RDONLY)):
        require(type(fd) is int and fd > 2 and stat.S_ISFIFO(os.fstat(fd).st_mode)
                and fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE == mode, 'trust pipe direction/type')
    require(request_fd != reply_fd and len(channel['nonce']) == 64, 'trust channel identity')
    request = dict(stage=stage, nonce=channel['nonce'], origin=origin,
                   attempt=attempt, argv=argv, context=now, observation=observation)
    raw = _frame(request)
    _write_all(request_fd, raw)
    # A bounded wait is also subject to the unchanged outside wait_owned timeout.
    import select
    received = b''; deadline = time.monotonic()+15
    while b'\n' not in received:
        remaining = deadline-time.monotonic()
        require(remaining > 0 and select.select([reply_fd], [], [], max(0, remaining))[0], 'trust reply timeout')
        part = os.read(reply_fd, 4096)
        require(part, 'trust reply EOF')
        received += part
        require(len(received) <= 4096, 'trust reply bound')
    reply = strict_json(received)
    require(isinstance(reply,dict) and reply.get('accepted') is True
            and reply == dict(stage=stage, nonce=channel['nonce'],
                          request_sha256=hashlib.sha256(raw).hexdigest(), accepted=True),
            'unauthenticated or rejected trust response')
    if stage == 'post':
        # Payload must inherit no trust channel. Pre keeps both through bwrap.
        os.close(request_fd); os.close(reply_fd)


class HostTrust:
    """In-memory authority owned by an already admitted service controller.

    No socket, new process, root helper, trust file or operational-state schema.
    Errors propagate into unchanged wait_owned guard cleanup. Never release a
    stage after partial observations. Held ns FDs prevent namespace-ID reuse.
    """
    def __init__(self, manifest, origin, writable_roots):
        require(origin == context(), 'origin must be freshly observed by host')
        self.manifest, self.origin = manifest, dict(origin)
        for root in writable_roots:
            root = Path(root)
            require(root.is_absolute() and '..' not in root.parts, 'canonical writable root')
            for path in [HERE, *[Path(p['path']) for p in BINARIES+POLICY_INPUTS]]:
                require(not path.is_relative_to(root), 'trust authority in writable root')
        verify_dependencies()  # authenticates initial host namespace and ownership
        self.baseline = trust_observation()
        validate_observation(self.baseline, host=True)
        self.host_fds, self.pre_fds = {}, None
        self.request_read = self.request_write = self.reply_read = self.reply_write = None
        self.buffer, self.stages, self.proofs = b'', [], []
        try:
            self.host_fds = self._open_ns('self')
            self.request_read, self.request_write = os.pipe()
            self.reply_read, self.reply_write = os.pipe()
            os.set_blocking(self.request_read, False)
            os.set_blocking(self.reply_write, False)
            self.origin['trust_channel'] = dict(request_fd=self.request_write,
                reply_fd=self.reply_read, nonce=os.urandom(32).hex())
            self.argv = command(manifest, self.origin)
        except BaseException:
            self.close(); raise

    @staticmethod
    def _open_ns(pid):
        fds = {}
        try:
            for n in NS_NAMES:
                fds[n] = os.open('/proc/'+str(pid)+'/ns/'+n, os.O_RDONLY|os.O_CLOEXEC)
            return fds
        except BaseException:
            for fd in fds.values(): os.close(fd)
            raise

    @property
    def pass_fds(self):
        return (self.request_write, self.reply_read)

    def attach(self, child):
        self.leader = _process(child.pid)
        # The creator keeps only its endpoints; child cannot inherit a reply writer.
        os.close(self.request_write); self.request_write = None
        os.close(self.reply_read); self.reply_read = None

    def poll(self):
        try: part = os.read(self.request_read, MAX_FRAME+1)
        except BlockingIOError: return
        if not part:
            require(self.stages == ['pre','post'] and not self.buffer, 'trust request premature EOF')
            return
        self.buffer += part
        require(len(self.buffer) <= MAX_FRAME, 'trust request bound')
        if b'\n' not in self.buffer: return
        raw, rest = self.buffer.split(b'\n', 1)
        require(not rest, 'multiple or trailing trust requests')
        self.buffer = b''
        request = strict_json(raw)
        try:
            self._accept(request)
        except BaseException as exc:
            dependency_diagnostic('host-protocol-rejected', None, None, type(exc).__name__+': '+str(exc))
            raise
        response = dict(stage=request['stage'], nonce=self.origin['trust_channel']['nonce'],
                        request_sha256=hashlib.sha256(raw+b'\n').hexdigest(), accepted=True)
        _write_all(self.reply_write, _frame(response))
        self.stages.append(request['stage'])

    def _accept(self, request):
        stage = 'pre' if not self.stages else 'post'
        require(len(self.stages) < 2 and request['stage'] == stage, 'trust stage order/replay')
        require(request['nonce'] == self.origin['trust_channel']['nonce']
                and request['origin'] == self.origin, 'spoofed origin/channel')
        require(request['attempt'] == self.manifest['attempt_root'], 'trust attempt')
        # Exact gate command extracted from the controller's original launch.
        pre_index = self.argv.index('pre')
        pre_argv = self.argv[pre_index+4:]
        post_index = pre_argv.index('post')
        expected = pre_argv if stage == 'pre' else self.manifest['argv']
        require(request['argv'] == expected, 'trust workload argv')
        helper_argv = (self.argv[pre_index-4:pre_index+4] + expected if stage == 'pre'
                       else pre_argv[post_index-4:])
        validate_stage_context(stage, request['context'], self.origin)
        # Read only this admitted cgroup, bounded by unchanged TasksMax128.
        pids = _bounded_read(Path('/sys/fs/cgroup')/self.origin['cgroup'].lstrip('/')/'cgroup.procs').split()
        require(len(pids) <= 128 and all(x.isdecimal() for x in pids), 'custody PID bound')
        matches = []
        for value in pids:
            try: p = _process(int(value))
            except FileNotFoundError: continue
            if p['argv'] == helper_argv and p['context']['namespaces'] == request['context']['namespaces']:
                matches.append(p)
        require(len(matches) == 1, 'ambiguous/missing live helper custody')
        p = matches[0]; pid = p['pid']
        require(p['executable'] == PYTHON, 'live helper interpreter')
        require(_descendant(pid, self.leader), 'helper outside owned descendant tree')
        observed = p['context']
        require(observed['cgroup'] == self.origin['cgroup'] and observed['uid'] == self.origin['uid']
                and observed['gid'] == self.origin['gid'], 'host process custody/identity')
        require(observed['boot'] == self.origin['boot'] and observed['overflow'] == self.origin['overflow'], 'host observation context')
        for kind in ('uid','gid'):
            # Host reads composition to HOST scope; self post maps to ns0 instead.
            single_map(observed['maps'][kind], self.origin[kind], self.origin[kind])
        fds = self._open_ns(pid)
        try:
            proof = lineage(stage, fds, self.host_fds, self.pre_fds)
            for n in NS_NAMES:
                require(request['context']['namespaces'][n] == n+':['+str(_ns_identity(fds[n])[1])+']', 'namespace fd race')
            # Kernel proc-root magic link is used ONLY after live PID/starttime,
            # exact cmdline, cgroup, ancestry and actual namespace proofs.
            root = os.open('/proc/'+str(pid)+'/root', os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
            try:
                actual = trust_observation(root, _bounded_read('/proc/'+str(pid)+'/mountinfo', MAX_FRAME))
            finally: os.close(root)
            dependency_diagnostic('host-observer-'+stage, actual, observed)
            compare_host(self.baseline, trust_observation())
            scaffold = self.origin if stage == 'post' and scaffold_source_contract() else None
            compare_host(self.baseline, actual, scaffold)
            compare_namespace(actual, request['observation'], request['context'], self.origin)
            require(_process(pid) == p, 'helper changed during observation')
            self.proofs.append(dict(stage=stage, process=p, lineage=proof,
                                   self_maps=request['context']['maps'], host_maps=observed['maps'],
                                   intermediate_maps_observed=False,
                                   scaffold_root=actual['root_mount'] if scaffold is not None else None,
                                   observation_sha256=hashlib.sha256(_frame(actual)).hexdigest()))
            if stage == 'pre':
                self.pre_fds = fds; fds = {}
        except BaseException as exc:
            dependency_diagnostic('host-rejected-'+stage, request.get('observation'),
                                  request.get('context'), type(exc).__name__+': '+str(exc))
            raise
        finally:
            for fd in fds.values(): os.close(fd)

    def complete(self):
        require(self.stages == ['pre','post'], 'missing authenticated namespace trust stages')
        return self.proofs

    def close(self):
        for attr in ('request_read','request_write','reply_read','reply_write'):
            fd = getattr(self, attr, None)
            if fd is not None: os.close(fd); setattr(self, attr, None)
        for group in (self.host_fds, self.pre_fds or {}):
            for fd in group.values(): os.close(fd)
            group.clear()



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
    """Host admission only. Namespace stages require live controller approval."""
    observation, now = trust_observation(), None
    try:
        now = _proc_context()
        dependency_diagnostic('host-before-validation', observation, now)
        require(now['boot'] == HOST_NAMESPACE_ANCHOR['boot']
                and now['namespaces'] == HOST_NAMESPACE_ANCHOR['namespaces'],
                'host namespace anchor changed; fresh reviewed authority required')
        for kind in ('uid','gid'):
            require(now['maps'][kind].split() == ['0','0','4294967295'], 'host identity map required')
        verify_dependency_contract()
        validate_observation(observation, host=True)
    except BaseException as exc:
        dependency_diagnostic('host-rejected', observation, now, type(exc).__name__+': '+str(exc))
        raise


def verify_dependency_contract():
    require([p['path'] for p in BINARIES] == [UNSHARE, PYTHON, BWRAP], 'exact binary contract')
    require(Path(sys.executable).resolve() == Path(PYTHON), 'executing interpreter contract')
    for p in ABSENT_INCLUDES:
        require(not os.path.lexists(p), 'policy include appeared '+p)
    require(Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip() == '1',
            'userns restriction changed')


def context():
    return _proc_context()


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
    observation, now = trust_observation(), None
    try:
        now = context()
        dependency_diagnostic(stage+'-before-validation', observation, now)
        security = policy_gate(stage, origin)
        validate_stage_context(stage, now, origin)
        if stage == 'pre':
            require(argv[0] == BWRAP, 'pre gate must exec bwrap')
        verify_dependency_contract()
        validate_observation(observation, host=False)
        namespace_trust(stage, origin, attempt, argv, now, observation)
    except BaseException as exc:
        dependency_diagnostic(stage+'-rejected', observation, now, type(exc).__name__+': '+str(exc))
        raise
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
