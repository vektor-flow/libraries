"""Refresh only TFM kern metadata; preserve all outline/atlas/font provenance."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from tex_font_metrics import load_tex_tfm


def repair(source, output, extras=None):
    if output.exists():
        raise ValueError('Use a fresh output path')
    import os
    env = os.environ.copy()
    if extras:
        env['TFMFONTS'] = str(extras.resolve()) + '//:'
    data = json.loads(source.read_text())
    fonts, changes = {}, []
    def update(symbol, key):
        name, code = symbol.get('fontName'), symbol.get('fontCode')
        if name is None or code is None or symbol.get('advance') is None:
            return
        if name not in fonts:
            path = subprocess.check_output(['kpsewhich', name + '.tfm'], text=True, env=env).strip()
            fonts[name] = load_tex_tfm(path)
        tfm = fonts[name]
        scale = symbol['advance'] / tfm.chars[code]['width'] if tfm.chars[code]['width'] else symbol.get('glyphParts', [{}])[0].get('fontSize', 0)
        if not scale and tfm.kerning.get(code):
            raise ValueError('Cannot infer font scale: ' + key)
        kerns = {str(k): v * scale for k, v in tfm.kerning.get(code, {}).items()}
        if symbol.get('kerns', {}) != kerns:
            changes.append({'key': key, 'before': symbol.get('kerns', {}), 'after': kerns})
            symbol['kerns'] = kerns
    for style, mapping in data['maps'].items():
        for token, symbol in mapping['symbols'].items():
            update(symbol, style + '/' + token)
    for role, table in data.get('documentFonts', {}).items():
        for code, symbol in table['symbols'].items():
            update(symbol, '@document:' + role + ':' + code)
    output.write_text(json.dumps(data, separators=(',', ':')))
    receipt = {'inputSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
               'outputSha256': hashlib.sha256(output.read_bytes()).hexdigest(),
               'changes': changes, 'fonts': sorted(fonts),
               'scope': 'Only kern metadata changed; outlines, UVs, atlas and glyph provenance preserved.'}
    output.with_suffix('.kerns.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'changedSymbols': len(changes), 'fonts': len(fonts)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--oracle-extras', type=Path)
    a = p.parse_args()
    repair(a.source, a.output, a.oracle_extras)
