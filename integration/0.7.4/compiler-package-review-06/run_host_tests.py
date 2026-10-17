#!/usr/bin/env python3
"""Reproduce the two bounded, joined host-only review runs."""
import json
from pathlib import Path
import resource
import subprocess
import time

out = Path(__file__).resolve().parent
records = []

def bound():
    resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

for label, args in [('original', ['--original']), ('patched', [])]:
    start = time.monotonic()
    cmd = ['/usr/bin/python3', '-B', str(out/'test_review.py'), *args]
    with (out/(label+'-tests.log')).open('w') as f:
        result = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT,
                                timeout=60, preexec_fn=bound)
    records.append(dict(label=label, argv=cmd, exit=result.returncode,
                        seconds=time.monotonic()-start, joined=True,
                        limit_address_space_bytes=512*1024*1024))
    print(label, result.returncode)
(out/'test-results.json').write_text(json.dumps(records, indent=2)+'\n')
assert records[0]['exit'] == 1 and records[1]['exit'] == 0
