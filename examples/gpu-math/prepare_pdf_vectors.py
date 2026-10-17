"""Prepare PDF Bezier outlines once; never typeset a document or read a PDF.

Runtime needs only the resulting JSON, not Python, fonts, kpsewhich or TeX.
Font discovery via kpsewhich is a development convenience; --font-dir also
supports explicit font directories. Existing third-party font notices apply.
"""
import argparse
import gzip
import hashlib
import json
import math
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.t1Lib import T1Font


def number(value):
    return format(value, '.10f').rstrip('0').rstrip('.') or '0'


class PdfPen(BasePen):
    """Keep cubic curves; BasePen converts quadratic curves exactly to cubics."""
    def __init__(self, glyphs=None):
        super().__init__(glyphs)
        self.commands = []

    def emit(self, operator, *points):
        self.commands.append(' '.join([*(number(v) for p in points for v in p), operator]))

    def _moveTo(self, p): self.emit('m', p)
    def _lineTo(self, p): self.emit('l', p)
    def _curveToOne(self, a, b, c): self.emit('c', a, b, c)
    def _closePath(self): self.commands.append('h')
    def _endPath(self): pass


def prepare(mapping, output, font_dirs=(), bitmap_templates=None):
    raw = mapping.read_bytes()
    data = json.loads(raw)
    keys, paths, sources, fonts = {}, {}, {}, {}
    bitmap_fonts = {}
    if bitmap_templates is not None:
        from prepare_bitmap_glyphs import font_geometry
        for path in bitmap_templates.glob('*.pdf'):
            bitmap_fonts[path.stem] = font_geometry(path)
            sources['bitmap-template/' + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='vkf-pdf-fonts-') as temp:
        # Read only PFB members, using the basename; never extract archive paths.
        bundled = Path(temp)
        for archive in ['esint-type1-source.zip', 'bbold-type1-source.zip', 'rsfs-source.zip']:
            # Optical profiles share the prepared font-source archives with
            # their parent resource directory; they need no article inputs.
            candidates = [directory / archive for directory in [mapping.parent, *mapping.parent.parents]]
            location = next((p for p in candidates if p.is_file()), None)
            if location is None:
                raise ValueError('Missing prepared font source archive: ' + archive)
            with zipfile.ZipFile(location) as z:
                for member in z.namelist():
                    if member.endswith('.pfb'):
                        (bundled / Path(member).name).write_bytes(z.read(member))
        directories = [*map(Path, font_dirs), mapping.parent / 'cm-super-source', bundled]

        def find(name):
            for directory in directories:
                matches = sorted(directory.rglob(name))
                if matches:
                    return matches[0]
            result = subprocess.run(['kpsewhich', name], capture_output=True, text=True)
            if result.returncode or not result.stdout.strip():
                raise ValueError('Missing vector font source: ' + name)
            return Path(result.stdout.strip())

        def font(name):
            companion = name.startswith('tcrm')
            program = ('sfrm' + name[4:] if companion else name) + '.pfb'
            if program not in fonts:
                path = find(program)
                f = T1Font(str(path))
                encoding = f['Encoding']
                if companion:
                    enc = find('cm-super-ts1.enc')
                    text = re.sub(r'%[^\n]*', '', enc.read_text())
                    encoding = re.findall(r'/([^\s/\[\]]+)', text[text.index('[')+1:text.index(']')])
                    sources[enc.name] = hashlib.sha256(enc.read_bytes()).hexdigest()
                fonts[program] = (f.getGlyphSet(), encoding)
                sources[program] = hashlib.sha256(path.read_bytes()).hexdigest()
            return fonts[program]

        symbols = {style+'/'+key: s for style, m in data['maps'].items() for key, s in m['symbols'].items()}
        for table in data.get('documentFonts', {}).values():
            for s in table['symbols'].values():
                # Document roles can reuse math metadata but have their own size.
                symbols[s['key']] = {**s, 'glyphParts': [{
                    'fontName': s['fontName'], 'fontCode': s['fontCode'],
                    'fontSize': table['size'], 'x': 0, 'y': 0}]}
        for key, symbol in symbols.items():
            pen, bounds = PdfPen(), BoundsPen(None)
            def rectangle(values):
                if len(values) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values) or values[2] <= 0 or values[3] <= 0:
                    raise ValueError('Invalid prepared bitmap font rectangle: ' + key)
                x, y, width, height = values
                pen.commands.append(' '.join(map(number, values)) + ' re')
                bounds.moveTo((x, y)); bounds.lineTo((x+width, y+height)); bounds.closePath()
            parts = symbol.get('glyphParts')
            rectangles = data.get('bitmapGlyphRects', {}).get(key)
            if rectangles is not None:
                # Preserve the real PK font pixels as vector rectangles. These
                # are reusable font geometry, not an image of text or a page.
                for values in rectangles:
                    rectangle(values)
            elif parts:
                for part in parts:
                    if part['fontName'] in bitmap_fonts:
                        factor, glyphs = bitmap_fonts[part['fontName']]
                        if part['fontCode'] not in glyphs:
                            raise ValueError('Missing prepared bitmap font character: ' + key)
                        scale = factor * round(part['fontSize'], 4)
                        for x, y, width, height in glyphs[part['fontCode']]:
                            rectangle([part['x']+x*scale, part['y']+y*scale, width*scale, height*scale])
                        continue
                    glyphs, encoding = font(part['fontName'])
                    glyph = glyphs[encoding[part['fontCode']]]
                    size = part['fontSize'] / 1000
                    transform = (size, 0, 0, -size, part['x'], part['y'])
                    glyph.draw(TransformPen(pen, transform))
                    glyph.draw(TransformPen(bounds, transform))
            elif key.endswith('/@text:_'):
                # This native LaTeX symbol is a rule, rather than a font glyph.
                l, t, r, b = symbol['inkBounds']
                pen.commands.append(' '.join(map(number, [l, t, r-l, b-t])) + ' re')
                bounds.bounds = (l, t, r, b)
            else:
                raise ValueError('No vector provenance for ' + key)
            vector = {'bounds': list(bounds.bounds or (0, 0, 0, 0)), 'operators': '\n'.join(pen.commands)}
            digest = hashlib.sha256(json.dumps(vector, sort_keys=True).encode()).hexdigest()
            keys[key] = digest
            paths[digest] = vector
    missing = set(data['tiles']) - keys.keys()
    if missing:
        raise ValueError('Unmapped vector tiles: ' + repr(sorted(missing)))
    result = {'schema': 'vkf.pdf-vectors/1', 'mappingSha256': hashlib.sha256(raw).hexdigest(),
              'keys': keys, 'paths': paths, 'fontSources': sources}
    if data.get('bitmapGlyphRects'):
        result['bitmapGlyphPolicy'] = data.get('bitmapGlyphPolicy')
        result['bitmapGeometrySha256'] = hashlib.sha256(json.dumps(data['bitmapGlyphRects'], sort_keys=True).encode()).hexdigest()
        bitmap_archive = mapping.parent / 'bbm-source.zip'
        if bitmap_archive.is_file():
            sources[bitmap_archive.name] = hashlib.sha256(bitmap_archive.read_bytes()).hexdigest()
    payload = json.dumps(result, separators=(',', ':')).encode()
    output.write_bytes(gzip.compress(payload, mtime=0) if output.suffix == '.gz' else payload)
    return {'keys': len(keys), 'paths': len(paths), 'bytes': output.stat().st_size}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mapping', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--font-dir', type=Path, action='append', default=[])
    p.add_argument('--bitmap-templates', type=Path)
    a = p.parse_args()
    print(json.dumps(prepare(a.mapping, a.output, a.font_dir, a.bitmap_templates)))
