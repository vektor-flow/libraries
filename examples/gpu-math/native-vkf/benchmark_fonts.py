"""Compare VKF font-loading algorithms with mincore-proven cold file inputs.

Scope: installed font read/lookup plus one-glyph vector PDF saved to disk. NOT
full source-to-document rendering. Same-process warm requests reread every file,
reparse needed data and regenerate the PDF, without a retained font/result cache.
"""
import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

if sys.version_info[:2] != (3, 14):
    raise SystemExit('Reference driver requires Python 3.14')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--reference', type=Path, required=True)
parser.add_argument('--catalogs', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = {'scope': 'font inputs to saved one-glyph vector PDF; NOT document rendering',
          'componentOnly': True, 'fullRenderTargetsAchieved': False,
          'coldSamplesPerVariant': 3, 'warmSamplesPerVariant': 9,
          'coldPolicy': 'new process; sync/drop_caches=3; mincore zero for executable and all input files; font reads and PDF save inside timer',
          'warmPolicy': 'existing process; full file reread, requested record parse and PDF rebuild on each request; no retained font/result objects',
          'sharedHostLibraries': 'May remain mapped/resident; not claimed evicted',
          'diskOutput': 'write/close included; durable fsync excluded for both variants',
          'compilerSha256': sha(args.compiler),
          'sources': {p.name: sha(p) for p in root.glob('*.vkf')}, 'variants': []}


def checked(command, **kwargs):
    result = subprocess.run(list(map(str, command)), text=True, capture_output=True,
                            timeout=120, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


try:
    executable = args.output/'font_benchmark'
    diagnostics = checked([args.compiler, '-b', root/'font_benchmark.vkf', '-o',
                           executable, '--diagnostics'])
    (args.output/'build.json').write_text(diagnostics)
    report['executableSha256'] = sha(executable)
    for profile in ['base', 'amsart-12']:
        for mode in ['eager', 'indexed']:
            original = args.reference/profile
            catalog = args.catalogs/profile
            inputs = ([original/'metrics.json', original/'vector-index.json',
                       original/'operators.txt'] if mode == 'eager' else
                      [catalog/'catalog.vkfont', catalog/'operators.txt'])
            variant = {'profile': profile, 'mode': mode,
                       'inputs': {str(p): {'bytes': p.stat().st_size, 'sha256': sha(p)}
                                  for p in inputs}, 'cold': [], 'warm': []}
            report['variants'].append(variant)
            files = args.output/(profile+'-'+mode+'-files.json')
            files.write_text(json.dumps(list(map(str, [executable, *inputs]))))
            expected = (original/'glyph-0.pdf').read_bytes()

            def request(destination):
                paths = inputs if len(inputs) == 3 else [*inputs, 'unused']
                return '\n'.join(map(str, [mode, *paths, 'text/a', destination]))+'\n'

            for sample in range(3):
                destination = args.output/(profile+'-'+mode+'-cold-'+str(sample)+'.pdf')
                cache = json.loads(checked(['sudo', '-n', '/usr/bin/python3.14',
                                          root.parent/'verify_file_cache.py', files]))
                assert len(cache['after']) == len(inputs)+1
                assert all(row['resident'] == 0 for row in cache['after'].values())
                start = time.perf_counter_ns()
                output = checked([executable], input=request(destination))
                elapsed = (time.perf_counter_ns()-start)/1e6
                assert output == 'done\n'
                assert destination.read_bytes() == expected
                variant['cold'].append({'milliseconds': elapsed, 'cache': cache,
                                         'exactReferencePdf': True})
            process = subprocess.Popen([str(executable)], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, bufsize=1)
            try:
                for sample in range(10):
                    destination = args.output/(profile+'-'+mode+'-warm-'+str(sample)+'.pdf')
                    start = time.perf_counter_ns()
                    process.stdin.write(request(destination))
                    process.stdin.flush()
                    output = process.stdout.readline()
                    elapsed = (time.perf_counter_ns()-start)/1e6
                    assert output == 'done\n', (output, process.poll())
                    assert destination.read_bytes() == expected
                    if sample:
                        variant['warm'].append({'milliseconds': elapsed,
                                                'exactReferencePdf': True})
                process.stdin.close()
                assert process.wait(timeout=30) == 0
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
            variant['coldMedianMs'] = statistics.median(row['milliseconds'] for row in variant['cold'])
            variant['warmMedianMs'] = statistics.median(row['milliseconds'] for row in variant['warm'])
            print(json.dumps({k: variant[k] for k in ['profile', 'mode', 'coldMedianMs', 'warmMedianMs']}), flush=True)
    report['passed'] = True
finally:
    (args.output/'timings.json').write_text(json.dumps(report, indent=2)+'\n')
