"""Generate the review-only delta from the pinned v6 candidate; no execution."""
from pathlib import Path
import hashlib,json,difflib
H=Path(__file__).resolve().parent
P=H.parent/'storage-propagation-repair-10/candidate/storage-direct-v6'
C=H/'candidate/storage-direct-v6'
def pin(p,dest=None):return dict(path=str(dest or p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
policy=json.loads((H/'evidence/local-policy.json').read_text())
pins=[dict(path=p['path'],sha256=p['sha256']) for p in policy['files']]
pins.insert(0,pin(H/'system-setup/vkf-storage-private-v1','/etc/apparmor.d/vkf-storage-private-v1'))
source=(P/'private_workload.py').read_text()
source=source.replace("'/usr/bin/unshare'", "'/usr/local/libexec/vkf-storage-private-v1/unshare'")
source=source.replace('\n\ndef verify_dependencies():', '\n\nPOLICY_INPUTS = '+repr(pins)+'\nABSENT_INCLUDES = '+repr(policy['missing_includes'])+'''


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


def verify_dependencies():''')
source=source.replace("        require(not (Path(p['path']).stat().st_mode & 0o6000), 'unexpected privileged binary')", "        trusted_system_file(p['path'])\n    for p in POLICY_INPUTS:\n        pinned(p)\n        trusted_system_file(p['path'])\n    for p in ABSENT_INCLUDES:\n        require(not os.path.lexists(p), 'policy include appeared '+p)\n    require(Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip() == '1',\n            'userns restriction changed')")
source=source.replace("    now = context()", "    security = policy_gate(stage, origin)\n    now = context()")
source=source.replace('private_workload_snapshot=stage, context=now,','private_workload_snapshot=stage, context=now, policy=security,')
(C/'private_workload.py').write_text(source)
source=(P/'storage_controller.py').read_text()
source=source.replace("                'pinned namespace argv dependencies required')", "                'pinned namespace argv dependencies required')\n        require(all(p in g['inputs'] and p in m['inputs'] for p in private_workload.POLICY_INPUTS),\n                'pinned namespace policy dependencies required')")
source=source.replace('*private_workload.BINARIES]', '*private_workload.BINARIES, *private_workload.POLICY_INPUTS]')
source=source.replace('        argv = sandbox(self.m, context)', "        private_workload.policy_gate('origin', context)\n        argv = sandbox(self.m, context)")
(C/'storage_controller.py').write_text(source)
patch=''
for p in sorted(C.iterdir()):
 if p.is_file():patch+=''.join(difflib.unified_diff((P/p.name).read_text().splitlines(True),p.read_text().splitlines(True),fromfile='v6/'+p.name,tofile='candidate/'+p.name))
(H/'policy-setup-v6.patch').write_text(patch)
(H/'binary-contract.json').write_text(json.dumps([{'path':'/usr/local/libexec/vkf-storage-private-v1/unshare','sha256':'41c65e55107cbbb1a1f6994784a938dd7dbbe255d1fea6b7a58ec96eabe382ef'},*json.loads((H.parent/'storage-propagation-repair-10/binary-contract.json').read_text())[1:]],indent=2)+'\n')
(H/'policy-inputs.json').write_text(json.dumps(pins,indent=2)+'\n')
