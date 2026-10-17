"""Independent PDF annotation/geometry verification with pypdf and MuPDF.

Consumes actual browser downloads and their positioned source layouts. It never
follows external URLs or invokes a LaTeX engine. The optional baseline verifies
that adding annotations changes neither the accepted layout nor page pixels.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pymupdf
from pypdf import PdfReader


def verify(pdf, layout_path):
    layout = json.loads(layout_path.read_text())
    reader, document = PdfReader(pdf), pymupdf.open(pdf)
    assert len(document) == len(layout['pages'])
    counts = {'uri': 0, 'destination': 0}
    rectangles, maximum = 0, 0
    page_indices = {page.indirect_reference.idnum: index for index, page in enumerate(reader.pages)}
    for index, source in enumerate(layout['pages']):
        expected = [item for item in source['items'] if item['kind'] == 'link' and item.get('target')]
        expected += [item for item in source.get('links', []) if item.get('target')]
        actual = [ref.get_object() for ref in reader.pages[index].get('/Annots', [])]
        assert len(actual) == len(expected), (index, len(actual), len(expected))
        # MuPDF must independently expose each annotation as a working URI or GoTo.
        decoded = document[index].get_links()
        assert len(decoded) == len(expected)
        for item, annotation, link in zip(expected, actual, decoded, strict=True):
            assert annotation['/Subtype'] == '/Link'
            assert list(annotation['/Border']) == [0, 0, 0], 'No duplicate visible border'
            rect = [max(0, item['x']-1), max(0, source['height']-item['y']-item['height']-1),
                    min(source['width'], item['x']+item['width']+1), min(source['height'], source['height']-item['y']+1)]
            error = max(abs(float(x)-y) for x, y in zip(annotation['/Rect'], rect, strict=True))
            maximum = max(maximum, error)
            assert error < 1e-8
            target = item['target']; counts[target['type']] += 1
            if target['type'] == 'uri':
                action = annotation['/A']
                assert action['/S'] == '/URI'
                assert str(action['/URI']) == target['value']
                assert link['kind'] == pymupdf.LINK_URI
                assert link['uri'] == target['value']
            else:
                point = layout['destinations'][target['value']]
                dest = annotation['/Dest']
                assert page_indices[dest[0].idnum] == point['page']
                assert dest[1] == '/XYZ'
                assert abs(float(dest[2])-point['x']) < 1e-8
                assert abs(float(dest[3])-(layout['pages'][point['page']]['height']-point['y'])) < 1e-8
                assert link['kind'] == pymupdf.LINK_GOTO and link['page'] == point['page']
                assert abs(link['to'].x-point['x']) < .001 and abs(link['to'].y-point['y']) < .001
            rectangles += 1
    return {'pages': len(document), 'annotations': rectangles, **counts,
            'maxRectangleSerializationErrorBp': maximum, 'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest()}


def compare_baseline(output, baseline, position_tolerance=0):
    before = json.loads((baseline/'full-paper-layout.json').read_text())
    after = json.loads((output/'full-paper-layout.json').read_text())
    # Link targets/semantic anchor IDs are new. Every painted rectangle and glyph
    # must retain its original identity, placement, scale and explicit colour.
    fields = ['kind', 'key', 'x', 'y', 'sx', 'sy', 'crop', 'cropX', 'width', 'height', 'asset', 'color']
    def positions(layout):
        return [[{key: item[key] for key in fields if key in item} for item in page['items']] for page in layout['pages']]
    x, y = positions(before), positions(after)
    exact = x == y
    maximum = 0
    def same(a, b):
        nonlocal maximum
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            maximum = max(maximum, abs(a-b))
            assert abs(a-b) <= position_tolerance, 'Position changed beyond the explicit numerical tolerance'
        elif isinstance(a, dict) and isinstance(b, dict):
            assert a.keys() == b.keys()
            for key in a: same(a[key], b[key])
        elif isinstance(a, list) and isinstance(b, list):
            assert len(a) == len(b)
            for l, r in zip(a, b, strict=True): same(l, r)
        else: assert a == b
    if not exact:
        assert position_tolerance > 0, 'Link metadata must not change the accepted layout'
        same(x, y)
    a, b = pymupdf.open(baseline/'full-paper.pdf'), pymupdf.open(output/'full-paper.pdf')
    assert len(a) == len(b) == 39
    compared = 0
    for index in range(len(a)):
        x = a[index].get_pixmap(matrix=pymupdf.Matrix(96/72, 96/72))
        y = b[index].get_pixmap(matrix=pymupdf.Matrix(96/72, 96/72))
        assert (x.width, x.height) == (y.width, y.height)
        assert x.samples == y.samples, 'Adding annotations changed page pixels: ' + str(index+1)
        compared += x.width*x.height
    return {'positionedItemsExactlyEqual': exact, 'maxPositionDifferenceBp': maximum,
            'positionToleranceBp': position_tolerance, 'pagesWithIdentical96dpiPixels': 39, 'comparedPixels': compared}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--position-tolerance-bp', type=float, default=0,
                        help='Explicit numerical roundoff gate; default preserves exact layout equality')
    args = parser.parse_args()
    report = {'fixture': verify(args.output/'links.pdf', args.output/'links-layout.json')}
    if (args.output/'full-paper.pdf').exists():
        report['fullPaper'] = verify(args.output/'full-paper.pdf', args.output/'full-paper-layout.json')
    if args.baseline:
        report['baselineComparison'] = compare_baseline(args.output, args.baseline, args.position_tolerance_bp)
    (args.output/'link-verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
