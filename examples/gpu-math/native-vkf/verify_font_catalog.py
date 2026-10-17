"""Python 3.14 independent font-catalog roundtrip and native PDF reference checks.

Compile first, supply both real font profiles afterwards. Reconstruct complete
original resources from records returned by VKF, then compare existing qualified
PDFs byte-for-byte. This checks a font component, not full document rendering.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from prepare_font_catalog import prepare

if sys.version_info[:2] != (3, 14):
    raise SystemExit('Reference checks require Python 3.14')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--reference', type=Path, required=True,
                    help='Successful verify_fonts.py output with original inputs and PDFs')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = {'componentOnly': True, 'completeRendererPort': False,
          'compilerSha256': sha(args.compiler), 'python': sys.version,
          'sources': {p.name: sha(p) for p in root.glob('*.vkf')}, 'profiles': []}


def run(command, input=None):
    result = subprocess.run(list(map(str, command)), input=input, text=True,
                            capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def reconstruct(records):
    metrics = dict(records['metrics'], maps={}, documentFonts={}, tiles={})
    index = dict(records['index'], keys={}, paths={})
    for key, value in records.items():
        if key.startswith('style/'):
            metrics['maps'][key[len('style/'):]] = dict(value, symbols={})
        if key.startswith('font/'):
            metrics['documentFonts'][key[len('font/'):]] = dict(value, symbols={})
    for key, value in records.items():
        category, _, name = key.partition('/')
        if category == 'math':
            style, token = name.split('/', 1)
            metrics['maps'][style]['symbols'][token] = value
        elif category == 'text':
            font, code = name.rsplit('/', 1)
            metrics['documentFonts'][font]['symbols'][code] = value
        elif category == 'tile':
            metrics['tiles'][name] = value
        elif category == 'vector':
            index['keys'][name] = value
        elif category == 'path':
            index['paths'][name] = value
    return metrics, index


try:
    reference_report = json.loads((args.reference/'verification.json').read_bytes())
    assert reference_report['passed']
    binaries = {}
    for name in ['catalog_audit', 'catalog_fixture']:
        executable = args.output/name
        build = run([args.compiler, '-b', root/(name+'.vkf'), '-o', executable,
                     '--diagnostics'])
        (args.output/(name+'-build.json')).write_text(build)
        binaries[name] = executable
    for profile in reference_report['profiles']:
        name = profile['name']
        original = args.reference/name
        prepared = args.output/name
        manifest = prepare(original, prepared)
        output = run([binaries['catalog_audit']], str(prepared/'catalog.vkfont')+'\n')
        lines = output.splitlines()
        count = int(lines[0])
        assert len(lines) == 1+count*2
        records = {json.loads(lines[i]): json.loads(lines[i+1])
                   for i in range(1, len(lines), 2)}
        assert len(records) == count == manifest['records']
        actual_metrics, actual_index = reconstruct(records)
        assert actual_metrics == json.loads((original/'metrics.json').read_bytes())
        assert actual_index == json.loads((original/'vector-index.json').read_bytes())
        pdfs = []
        for ordinal, pdf in enumerate(profile['pdfs']):
            destination = prepared/('glyph-'+str(ordinal)+'.pdf')
            run([binaries['catalog_fixture']], '\n'.join(map(str, [
                prepared/'catalog.vkfont', prepared/'operators.txt', pdf['key'],
                destination]))+'\n')
            assert destination.read_bytes() == Path(pdf['path']).read_bytes()
            pdfs.append({'key': pdf['key'], 'path': str(destination),
                         'sha256': sha(destination), 'exactReferencePdfBytes': True})
        report['profiles'].append({'name': name, 'records': count,
                                   'completeMetricsEqual': True,
                                   'completeVectorIndexEqual': True,
                                   'manifest': manifest, 'pdfs': pdfs})
    report['passed'] = True
finally:
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'passed': True, 'profiles': len(report['profiles']),
                  'records': sum(p['records'] for p in report['profiles'])}))
