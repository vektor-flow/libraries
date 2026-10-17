"""Create only this worker's two-file candidate from pinned installed v6."""
import ast, hashlib, json
from pathlib import Path
H=Path(__file__).resolve().parent
V=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/storage-direct-v6')
receipt=V.parent/'storage-direct-v6-installed-20261017.json'
pins=json.loads(receipt.read_text())['installed_files']
for p in pins:assert hashlib.sha256(Path(p['path']).read_bytes()).hexdigest()==p['sha256'],p
(H/'sourcepins.json').write_text(json.dumps(pins,indent=2)+'\n')
D=H/'proposed';D.mkdir(exist_ok=True)
s=(V/'storage_controller.py').read_text()
old="        private_workload.policy_gate('origin', context)"
assert s.count(old)==1
s=s.replace(old,"        private_workload.initialize_origin_capabilities(context)\n"+old)
(D/'storage_controller.py').write_text(s)
s=(V/'private_workload.py').read_text()
addition='''def _security_snapshot():
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


'''
pos=s.index('def policy_gate(')
s=s[:pos]+addition+s[pos:]
old="""    raw = Path('/proc/self/status').read_text()
    status = {}
    for line in raw.splitlines():
        k, _, v = line.partition(':')
        require(k not in status, 'duplicate status field')
        status[k] = v.split()
"""
new="""    observation = _security_snapshot()
    # Emit even when a strict identity/capability/NNP/label check below rejects.
    _security_diagnostic('policy-gate', observation, stage=stage)
    require(not observation['errors'], 'policy observation failed')
    status = observation['status']
"""
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace("    label = Path('/proc/self/attr/current').read_text().strip()\n","    label = observation['label']\n")
(D/'private_workload.py').write_text(s)
for p in D.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
print('Prepared two proposed files; installed seven-file hashes verified.')
