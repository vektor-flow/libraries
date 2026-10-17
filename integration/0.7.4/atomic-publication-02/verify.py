"""Bounded host-only verification. Writes exclusively alongside this script."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import resource
import subprocess
import time

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
ENV = dict(os.environ, VKF_PUBLICATION_TEST_TMPDIR=str(OUT / 'test-tmp'))
ENV['PATH'] = '/home/viktor/.local/bin:' + ENV.get('PATH', '')
CHECKS = [
    ('final-tests', ['node', '--test', 'examples/gpu-math/tests/source-revision.test.mjs',
                     'examples/gpu-math/tests/source-publication.test.mjs'], OUT / 'candidate'),
    ('final-patch-check', ['git', 'apply', '--check', '--whitespace=error-all',
                           str(OUT / 'atomic-publication.patch')], REPO),
]
results = []
for label, command, cwd in CHECKS:
    started = time.monotonic()
    run = subprocess.run(command, cwd=cwd, env=ENV, capture_output=True, text=True)
    (OUT / (label + '.stdout')).write_text(run.stdout)
    (OUT / (label + '.stderr')).write_text(run.stderr)
    row = dict(label=label, command=command, cwd=str(cwd),
               elapsed_seconds=time.monotonic() - started, exit_code=run.returncode,
               max_child_rss_kib_cumulative=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
               joined=True, utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    results.append(row)
    print(json.dumps(row))
    if run.returncode:
        print(run.stdout, run.stderr)
        break
(OUT / 'final-results.json').write_text(json.dumps(results, indent=2) + '\n')
raise SystemExit(any(r['exit_code'] for r in results))
