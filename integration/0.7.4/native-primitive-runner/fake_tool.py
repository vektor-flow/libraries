#!/usr/bin/env python3
"""Bounded test fixture only. Never selected by the runner CLI."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

kind, mode, raw, normalized, binary = sys.argv[1:]
if mode == 'nonzero': sys.exit(17)
if mode == 'deadline': time.sleep(2); sys.exit(0)
if mode == 'orphan':
    subprocess.Popen(['/usr/bin/python3','-B','-c','import time; time.sleep(2)'], start_new_session=True)
    sys.exit(0)
if kind == 'normalize':
    dest = Path(normalized)/'source'; dest.mkdir(parents=True)
    rows = []
    for src in sorted(Path(raw).glob('*.vkf')):
        data = src.read_bytes(); (dest/src.name).write_bytes(data)
        h = hashlib.sha256(data).hexdigest()
        rows.append(dict(name=src.name,beforeSha256=h,afterSha256=h,changed=False,imports=[]))
    report = dict(baseline=raw,files=rows,ambiguousAliases=[],changedFiles=0,rewrittenCalls=0)
    (Path(normalized)/'normalization.json').write_text(json.dumps(report))
    print(json.dumps(dict(changedFiles=0,rewrittenCalls=0,ambiguousAliases=0,files=len(rows),source=str(dest))))
    if mode == 'unexpected': print('UNEXPECTED')
    if mode == 'stale_binary': Path(binary).write_text('stale')
elif kind == 'compile':
    if mode == 'missing': sys.exit(0)
    if mode == 'not_executable': Path(binary).write_text('fixture'); sys.exit(0)
    script = '#!/usr/bin/python3\n'
    if mode == 'run_nonzero': script += 'raise SystemExit(23)\n'
    elif mode == 'run_stdout': script += 'print("UNEXPECTED")\n'
    elif mode == 'run_stderr': script += 'import sys\nprint("UNEXPECTED",file=sys.stderr)\n'
    elif mode == 'run_deadline': script += 'import time\ntime.sleep(2)\n'
    elif mode == 'run_orphan':
        script += 'import subprocess\nsubprocess.Popen(["/usr/bin/python3","-B","-c","import time; time.sleep(2)"],start_new_session=True)\n'
    elif mode == 'tamper_raw':
        script += 'from pathlib import Path\nPath('+repr(str(next(Path(raw).glob('*.vkf'))))+').write_text("tampered")\n'
    else: script += 'pass\n'
    Path(binary).write_text(script); os.chmod(binary,0o700)
else: raise SystemExit('unknown fixture stage')
