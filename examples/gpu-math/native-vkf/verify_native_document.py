"""Compare a fresh native source-to-PDF request with production JS geometry.

Correctness only: this driver neither evicts file caches nor measures performance.
The JS renderer is the integration oracle, not a fresh LaTeX glyph oracle.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

if sys.version_info[:2] != (3, 14):
    raise SystemExit('Python 3.14 required')
parser = argparse.ArgumentParser(description=__doc__)
for name in ['binary', 'source', 'fonts', 'operators', 'metrics', 'language', 'output']:
    parser.add_argument('--'+name, type=Path, required=True)
parser.add_argument('--files', type=Path)
parser.add_argument('--job', default='main')
parser.add_argument('--entry', default='main.tex')
parser.add_argument('--timeout', type=float, default=600)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = dict(passed=False, oracle='production document-layout.mjs',
              freshLaTeXValidated=False, performanceValidated=False,
              driverSha256=sha(Path(__file__)), inputs={})
for name in ['binary', 'source', 'fonts', 'operators', 'metrics', 'language', 'files']:
    path = getattr(args, name)
    if path is not None:
        report['inputs'][name] = dict(path=str(path.resolve()), sha256=sha(path))
report['referenceSources'] = {str(p.relative_to(root.parent)): sha(p)
                              for p in root.parent.rglob('*.mjs')}
errors = []
maximum = 0.0


def compare(expected, actual, path):
    global maximum
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or expected.keys() != actual.keys():
            errors.append(dict(path=path, expectedKeys=list(expected),
                               actualKeys=list(actual) if isinstance(actual, dict) else None))
            return
        for key in expected:
            compare(expected[key], actual[key], path+'/'+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            errors.append(dict(path=path, expectedCount=len(expected),
                               actualCount=len(actual) if isinstance(actual, list) else None))
            return
        for index, (left, right) in enumerate(zip(expected, actual)):
            compare(left, right, path+'/'+str(index))
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if type(expected) is not type(actual) or expected != actual:
            errors.append(dict(path=path, expected=expected, actual=actual))
    elif not isinstance(actual, (int, float)) or isinstance(actual, bool) or not math.isfinite(actual):
        errors.append(dict(path=path, expected=expected, actual=actual))
    else:
        error = abs(expected-actual)
        maximum = max(maximum, error)
        if error > 1e-9:
            errors.append(dict(path=path, expected=expected, actual=actual, error=error))


try:
    metrics = json.loads(args.metrics.read_text())
    roles = json.dumps(list(metrics['documentFonts']))
    pdf = args.output/'document.pdf'
    native_report = args.output/'report.json'
    layout = args.output/'layout.json'
    lines = [args.source.resolve(), args.fonts.resolve(), args.operators.resolve(),
             args.language.resolve(), roles, args.files.resolve() if args.files else '',
             args.job, args.entry, pdf.resolve(), native_report.resolve(), layout.resolve()]
    stdin = '\n'.join(map(str, lines))+'\n'
    (args.output/'stdin.txt').write_text(stdin)
    process = subprocess.run([str(args.binary.resolve())], input=stdin, text=True,
                             capture_output=True, timeout=args.timeout)
    (args.output/'native.stdout').write_text(process.stdout)
    (args.output/'native.stderr').write_text(process.stderr)
    report['nativeExitCode'] = process.returncode
    process.check_returncode()
    native = json.loads(native_report.read_text())
    actual = json.loads(layout.read_text())
    files = args.files.resolve() if args.files else args.output/'files.json'
    if not args.files:
        files.write_text('{}')
    oracle = args.output/'reference.mjs'
    oracle.write_text("""import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const [modulePath,sourcePath,metricsPath,filesPath,outPath,jobName,entry]=process.argv.slice(2);
const {typesetDocument}=await import(pathToFileURL(modulePath));
const result=await typesetDocument(await readFile(sourcePath,'utf8'),
 JSON.parse(await readFile(metricsPath)),{files:JSON.parse(await readFile(filesPath)),buildContext:{jobName,entry}});
await writeFile(outPath,JSON.stringify(result));
""")
    subprocess.run(['node', str(oracle), str(root.parent/'document-layout.mjs'),
                    str(args.source.resolve()), str(args.metrics.resolve()), str(files),
                    str(args.output/'reference.json'), args.job, args.entry],
                   check=True, capture_output=True, text=True, timeout=args.timeout)
    expected = json.loads((args.output/'reference.json').read_text())
    compare(expected['diagnostics'], native['diagnostics'], '/diagnostics')
    compare([], native['unresolved'], '/unresolved')
    compare(expected['complete'], native['complete'], '/complete')
    if not native['complete'] or not expected['complete']:
        errors.append(dict(path='/complete', reason='Complete document rendering is required'))
    compare(len(expected['pages']), len(actual['pages']), '/pageCount')
    for index, (left, right) in enumerate(zip(expected['pages'], actual['pages'])):
        for key in ['width', 'height', 'number', 'items']:
            compare(left[key], right[key], f'/pages/{index}/{key}')
        compare(left.get('links', []), right.get('links', []), f'/pages/{index}/links')
    compare(expected['destinations'], actual['destinations'], '/destinations')
    if native['complete']:
        info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True, check=True)
        (args.output/'pdfinfo.txt').write_text(info.stdout)
        if not pdf.stat().st_size or native['pdfBytes'] != pdf.stat().st_size:
            errors.append(dict(path='/pdf', reason='PDF byte count does not match native report'))
    report.update(nativeComplete=native['complete'], referenceComplete=expected['complete'],
                  nativePages=len(actual['pages']), referencePages=len(expected['pages']),
                  nativeGlyphs=sum(item.get('kind') == 'glyph' for page in actual['pages'] for item in page['items']),
                  referenceGlyphs=sum(item.get('kind') == 'glyph' for page in expected['pages'] for item in page['items']),
                  maximumAbsoluteNumericError=maximum, mismatchCount=len(errors),
                  mismatches=errors[:30], passed=not errors)
except Exception as error:
    report['exception'] = repr(error)
    raise
finally:
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({key: report[key] for key in ['passed', 'nativePages', 'nativeGlyphs', 'mismatchCount']}))
if not report['passed']:
    raise SystemExit(1)
