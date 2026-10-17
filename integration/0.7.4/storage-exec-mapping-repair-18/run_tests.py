from pathlib import Path
import json,subprocess,time,resource
H=Path(__file__).resolve().parent
start=time.monotonic();p=subprocess.Popen(['/usr/bin/python3.14','-I','-B',str(H/'test_repair.py')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:stdout,stderr=p.communicate(timeout=35)
except subprocess.TimeoutExpired:p.kill();stdout,stderr=p.communicate();raise
(H/'evidence/tests.stdout').write_bytes(stdout);(H/'evidence/tests.stderr').write_bytes(stderr)
r=dict(argv=p.args,pid=p.pid,exit=p.returncode,seconds=time.monotonic()-start,child_absent=not Path(f'/proc/{p.pid}').exists(),child_maxrss_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
(H/'test-results.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));print(stderr.decode()[-2000:]);raise SystemExit(p.returncode)
