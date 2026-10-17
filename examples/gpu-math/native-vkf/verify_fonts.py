"""Independent Python 3.14 reference checks for VKF's real installed fonts.

No Python production layout/PDF implementation: VKF parses resources and writes
the fixtures. Python compares all numbers, PDF operators and rendered drawings.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pymupdf
from pypdf import PdfReader

from prepare_fonts import prepare

if sys.version_info[:2] != (3, 14):
    raise SystemExit('Reference checks require Python 3.14')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--assets', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = {'python': sys.version, 'compilerSha256': sha(args.compiler),
          'sourceHashes': {p.name: sha(p) for p in root.glob('*.vkf')},
          'commands': [], 'profiles': [], 'completeRendererPort': False,
          'fullRenderPerformanceMeasured': False}


def run(command, input=None, timeout=60):
    start = time.perf_counter()
    record = {'command': list(map(str, command)), 'input': input}
    report['commands'].append(record)
    try:
        result = subprocess.run(command, input=input, text=True, capture_output=True,
                                timeout=timeout)
        record.update(exitCode=result.returncode, seconds=time.perf_counter()-start,
                      stderr=result.stderr)
        if result.returncode:
            record['stdout'] = result.stdout
            raise RuntimeError(result.stderr or result.stdout or 'VKF command failed')
        return result.stdout
    except subprocess.TimeoutExpired:
        record.update(timedOut=True, limitSeconds=timeout)
        raise


def reference_nodes(value):
    numbers = []

    def walk(node):
        count = 1
        if isinstance(node, dict):
            for child in node.values():
                count += 1+walk(child)  # Each object key is a string node.
        elif isinstance(node, list):
            count += sum(walk(child) for child in node)
        elif type(node) in (int, float):
            numbers.append(node)
        return count

    return walk(value), numbers


try:
    executables = {}
    for name in ['resource_audit', 'font_fixture']:
        executable = args.output/name
        diagnostics = run([str(args.compiler), '-b', str(root/(name+'.vkf')),
                           '-o', str(executable), '--diagnostics'], timeout=120)
        (args.output/(name+'-build.json')).write_text(diagnostics)
        executables[name] = executable
    for profile in ['', 'amsart-12']:
        name = profile or 'base'
        source = args.assets/'font-profiles'/profile if profile else args.assets
        directory = args.output/name
        prepared = prepare(source, directory)
        result = {'name': name, 'prepared': prepared, 'numericAudits': [], 'pdfs': []}
        report['profiles'].append(result)
        for filename in ['metrics.json', 'vector-index.json']:
            path = directory/filename
            expected_count, expected = reference_nodes(json.loads(path.read_bytes()))
            output = run([str(executables['resource_audit'])], str(path)+'\n')
            fields = output.splitlines()
            (directory/(filename+'.numeric-output.txt')).write_text(output)
            assert int(fields[0]) == expected_count, (filename, 'JSON node count')
            actual = list(map(float, fields[1:]))
            assert len(actual) == len(expected), (filename, 'numeric value count')
            maximum = 0
            for index, (native, reference) in enumerate(zip(actual, expected)):
                error = abs(native-reference)
                maximum = max(maximum, error)
                assert error <= max(1e-12, abs(reference)*1e-14), (
                    filename, index, native, reference, error)
            result['numericAudits'].append({'file': filename, 'nodes': expected_count,
                                           'numbers': len(actual), 'maxAbsoluteError': maximum})
        index = json.loads((directory/'vector-index.json').read_bytes())
        operators = (directory/'operators.txt').read_bytes()
        keys = ['text/a', 'text/\\alpha']
        if profile:
            keys.append('text/@font:mathbbm:1')
        for ordinal, key in enumerate(keys):
            pdf_path = directory/('glyph-'+str(ordinal)+'.pdf')
            inputs = [directory/'metrics.json', directory/'vector-index.json',
                      directory/'operators.txt', key, pdf_path]
            run([str(executables['font_fixture'])], '\n'.join(map(str, inputs))+'\n')
            reader = PdfReader(pdf_path, strict=True)
            assert len(reader.pages) == 1
            forms = reader.pages[0]['/Resources']['/XObject']
            assert len(forms) == 1
            form = forms['/G0'].get_object()
            assert form['/Subtype'] == '/Form'
            path = index['paths'][index['keys'][key]]
            expected = operators[path['offset']:path['offset']+path['length']]+b'\nf'
            assert form.get_data() == expected, (key, 'exact font operator bytes')
            assert max(abs(float(a)-b) for a, b in zip(form['/BBox'], path['bounds'])) <= 1e-12
            document = pymupdf.open(pdf_path)
            assert len(document[0].get_images(full=True)) == 0
            assert len(document[0].get_drawings()) > 0
            dimensions = []
            for zoom in [1, 16, 64]:
                pixmap = document[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
                assert pixmap.width == 80*zoom and pixmap.height == 80*zoom
                assert min(pixmap.samples) < 128
                dimensions.append([pixmap.width, pixmap.height])
                del pixmap
            document.close()
            result['pdfs'].append({'key': key, 'path': str(pdf_path), 'sha256': sha(pdf_path),
                                   'operatorsExact': True, 'imageObjects': 0,
                                   'renderDimensions': dimensions})
    report['passed'] = True
finally:
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'passed': True, 'profiles': len(report['profiles']),
                  'pdfs': sum(len(profile['pdfs']) for profile in report['profiles'])}))
