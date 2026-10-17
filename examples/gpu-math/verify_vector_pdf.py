"""Independent MuPDF readback and 1/16/64x curve checks; no TeX engine.

Reference SVGs are drawn directly from original Type1 font programs via
fontTools' SVG pen, independently of the PDF pen and serialized outline bundle.
Rasterization is validation only; the exported artifact contains vector paths.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pymupdf
from pypdf import PdfReader
from pypdf.generic import ContentStream
from fontTools.t1Lib import T1Font
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen


def verify(output):
    root = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=True)
    data = json.loads((root/'typing-demo/typing-data.json').read_text())
    samples = [('cmr10', 79, 'text/@document:roman:79'),
               ('cmr10', 65, 'text/@document:roman:65'),
               ('cmmi10', 120, 'text/x')]
    report = []
    for name, code, key in samples:
        fontpath = Path(subprocess.check_output(['kpsewhich', name+'.pfb'], text=True).strip())
        font = T1Font(str(fontpath))
        size = data['documentFonts']['roman']['size']
        pen = SVGPathPen(None)
        font.getGlyphSet()[font['Encoding'][code]].draw(TransformPen(pen, (size/1000, 0, 0, -size/1000, 10, 20)))
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="30pt" height="30pt" viewBox="0 0 30 30"><path d="{pen.getCommands()}"/></svg>'
        svgdoc = pymupdf.open(stream=svg.encode(), filetype='svg')
        reference = pymupdf.open(stream=svgdoc.convert_to_pdf(), filetype='pdf')
        layout = {'pages': [{'width': 30, 'height': 30, 'items': [{'kind': 'glyph', 'key': key, 'x': 10, 'y': 20}]}]}
        inputpath, pdfpath = output/(name+'-'+str(code)+'.json'), output/(name+'-'+str(code)+'.pdf')
        inputpath.write_text(json.dumps(layout))
        subprocess.run(['node', str(root/'export_vector_pdf.mjs'), str(inputpath), str(pdfpath)], check=True, capture_output=True)
        exported = pymupdf.open(pdfpath)
        assert len(exported) == 1 and not exported[0].get_images()
        assert not exported[0].get_fonts(), 'Glyphs must be vector curves, not substituted fonts'
        drawing = exported[0].get_drawings()
        assert any(item[0] == 'c' for d in drawing for item in d['items']), 'Cubic curves must survive'
        for zoom in [1, 16, 64]:
            a = exported[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY)
            b = reference[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY)
            x, y = np.frombuffer(a.samples, np.uint8), np.frombuffer(b.samples, np.uint8)
            assert a.width == b.width and a.height == b.height
            # Both independent vector adapters use MuPDF's final rasterizer.
            # Float32 conversion can move a boundary's coverage by a few levels.
            mean = float(np.abs(x.astype(int)-y.astype(int)).mean())
            mask_a, mask_b = x < 128, y < 128
            iou = float(np.logical_and(mask_a, mask_b).sum()/np.logical_or(mask_a, mask_b).sum())
            assert mean < .02 and iou > .995, (name, code, zoom, mean, iou)
            report.append({'font': name, 'code': code, 'zoom': zoom, 'meanGrayError': mean, 'silhouetteIoU': iou})
            if zoom == 64:
                a.save(output/(name+'-'+str(code)+'-64x.png'))
    # Also inspect the actual browser download with an independent PDF reader.
    example = pymupdf.open(output/'example.pdf')
    assert len(example) == 1 and not example[0].get_images()
    assert len(example[0].get_drawings()) > 50
    example[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(output/'example.png')
    full = output/'full-paper.pdf'
    if full.exists():
        doc = pymupdf.open(full)
        assert len(doc) == 39
        # Original PNG figures are allowed; text and math must stay paths.
        images = sum(len(page.get_image_info()) for page in doc)
        drawings = sum(len(page.get_drawings()) for page in doc)
        assert drawings > 60000
        layout = json.loads((output/'full-paper-layout.json').read_text())
        reader = PdfReader(full)
        measured, maximum = 0, 0
        for source, page in zip(layout['pages'], reader.pages, strict=True):
            stack, matrix, actual = [], None, []
            for operands, op in ContentStream(page.get_contents(), reader).operations:
                if op == b'q': stack.append(matrix)
                elif op == b'Q': matrix = stack.pop()
                elif op == b'cm': matrix = list(map(float, operands))
                elif op == b'Do' and str(operands[0]).startswith('/G'):
                    actual.append(matrix)
            expected = [[i.get('sx', 1), 0, 0, i.get('sy', 1), i['x'], i['y']]
                        for i in source['items'] if i['kind'] in ['glyph', 'field'] and i.get('sx', 1) and i.get('sy', 1)]
            assert len(actual) == len(expected)
            for a, b in zip(actual, expected, strict=True):
                maximum = max(maximum, max(abs(x-y) for x, y in zip(a, b, strict=True)))
                measured += 1
        assert maximum < 1e-9, 'PDF must preserve every glyph placement and scale'
        report.append({'paperPages': len(doc), 'vectorPaints': drawings, 'originalIllustrationPlacements': images,
                       'verifiedGlyphAndFieldTransforms': measured, 'maxTransformSerializationErrorBp': maximum,
                       'pdfSha256': hashlib.sha256(full.read_bytes()).hexdigest()})
    (output/'vector-verification.json').write_text(json.dumps({'passed': True, 'checks': report}, indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    print(json.dumps(verify(p.parse_args().output)))
