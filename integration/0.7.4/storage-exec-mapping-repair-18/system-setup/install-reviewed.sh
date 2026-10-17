#!/bin/bash
# REVIEW ONLY. Never executed by repair18. Hold admissions; see HANDOFF.txt.
set -euo pipefail
[[ -x /usr/bin/python3.14 ]] || { echo 'Missing /usr/bin/python3.14' >&2; exit 1; }
[[ -x /usr/sbin/apparmor_parser ]] || { echo 'Missing /usr/sbin/apparmor_parser' >&2; exit 1; }
exec /usr/bin/python3.14 -I -B - '/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-exec-mapping-repair-18/system-setup/system_setup.py' install 51a58a4d7e00164c60f24ae4d280e09ff4d46a886ba21b166b3990bad13b5ced <<'PYCODE'
import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]); data=p.read_bytes()
if hashlib.sha256(data).hexdigest()!=sys.argv[3]:raise RuntimeError('setup helper hash mismatch')
sys.argv=[str(p),sys.argv[2]]
exec(compile(data,str(p),'exec'),dict(__name__='__main__',__file__=str(p)))
PYCODE
