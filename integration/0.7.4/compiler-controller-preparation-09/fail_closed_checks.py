"""Two actual CLI refusal probes, synchronous bounded children, own-output logs only."""
import json
from pathlib import Path
import resource
import subprocess
import time
HERE=Path(__file__).resolve().parent
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
rows=[]
commands=[['assemble','--plan',str(HERE.parent/'compiler-native-binding-08/root-check01/compiler-preview/plan.json'),
           '--root-inputs',str(HERE/'root-inputs.REQUIRED.json'),'--out',str(HERE/'MUST-NOT-EXIST')],
          ['run','--contract',str(HERE/'MISSING-ACTUAL-CONTRACT'),'--contract-sha256','0'*64,
           '--grant',str(HERE/'MISSING-ACTUAL-GRANT'),'--manifest',str(HERE/'MISSING-ACTUAL-MANIFEST')]]
for i,args in enumerate(commands):
    start=time.monotonic()
    p=subprocess.Popen(['/usr/bin/python3','-I','-B',str(HERE/'adapter.py'),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try: out,err=p.communicate(timeout=10)
    except BaseException:
        p.kill();p.communicate();raise
    assert p.returncode!=0 and not (HERE/'MUST-NOT-EXIST').exists()
    expected=b'actual root execution decision required' if i==0 else b'missing/oversized file'
    assert expected in err,err
    (HERE/('refusal-'+str(i)+'.stderr')).write_bytes(err)
    rows.append(dict(case=i,exit=p.returncode,pid=p.pid,joined=True,absent=not Path('/proc/'+str(p.pid)).exists(),
                     seconds=time.monotonic()-start,expected_refusal=expected.decode(),native_execution=False))
(HERE/'refusal-checks.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows))
