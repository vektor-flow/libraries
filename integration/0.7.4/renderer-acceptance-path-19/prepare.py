"""Read current sources and pinned original40; write only this grant's fixtures.

No compiler, renderer, controller, normalization, or native executable is run.
The import graph is conservative source closure, not a linked dependency receipt.
"""
import ast
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
D301 = Path('/home/viktor/.cache/vkf-s0-runtimes-20261012/Proof/tests/independent-worker-D/iteration301')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def check(ref):
    if sha(ref['path']) != ref['sha256']:
        raise ValueError('Input hash mismatch: ' + ref['path'])


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def make_edit(source):
    needle = b'\\title{Idempotents and homology of diagram algebras}'
    if source.count(needle) != 1:
        raise ValueError('Unique original title required')
    start = source.index(needle) + len(needle) - 2
    updated = source[:start] + b'x' + source[start + 1:]
    units = len(source[:start].decode('utf-8').encode('utf-16-le')) // 2
    return updated, {'sourceId': 'main.tex', 'startByte': start, 'stopByte': start + 1,
                     'startUTF16': units, 'stopUTF16': units + 1, 'old': 's', 'text': 'x',
                     'description': 'One actual title character; full original40 body/includes/resources retained'}


def stdin_text(binding, source, attempt, layout=False):
    lines = [x['value'] for x in binding['ordered_lines'][:8]]
    lines[0] = str(source)
    lines += [str(attempt / 'document.pdf'), str(attempt / 'report.json'),
              str(attempt / 'layout.json') if layout else '']
    if any('\n' in line or '\r' in line for line in lines):
        raise ValueError('Invalid line-framed path')
    return '\n'.join(lines) + '\n'


def main():
    binding_path = D301 / 'binding.json'
    binding = json.loads(binding_path.read_text())
    refs = [binding['original_stdin'], *binding['inputs'], binding['oracle'],
            binding['layout'], binding['report'], binding['parity_binding'],
            binding['historical_verification']]
    for ref in refs:
        check(ref)
    original_lines = Path(binding['original_stdin']['path']).read_text().splitlines()
    if original_lines != [x['value'] for x in binding['ordered_lines']]:
        raise ValueError('Original stdin/binding mismatch')
    native = REPO / 'examples/gpu-math/native-vkf'
    normalizer = native / 'normalize_module_aliases.py'
    tree = ast.parse(normalizer.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'mask')
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(normalizer), 'exec'), namespace)
    sources = {p.stem: p for p in native.glob('*.vkf')}
    visited, external, edges = set(), set(), []
    pending = ['native_document_cli']
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        masked = namespace['mask'](sources[name].read_text())
        for alias, target in re.findall(r'^([A-Za-z_]\w*)\s*:\s*\.([A-Za-z_]\w*)\s*$', masked, re.M):
            edges.append({'from': name, 'alias': alias, 'to': target})
            if target in sources:
                pending.append(target)
            else:
                external.add(target)
    source_refs = [pin(sources[name]) for name in sorted(visited)]
    fixture = HERE / 'fixtures'
    fixture.mkdir(exist_ok=False)
    original = Path(binding['ordered_lines'][0]['value'])
    edited, edit = make_edit(original.read_bytes())
    edit_path = fixture / 'original40-title-edit.tex'
    edit_path.write_bytes(edited)
    edit.update(baseSource=pin(original), updatedSource=pin(edit_path))
    save(fixture / 'edit.json', edit)
    # Placeholders are replaced by write_stdin.py only after root assigns an attempt.
    for case, source in [('original', original), ('edited-full', edit_path)]:
        for layout in (False, True):
            name = case + ('-layout' if layout else '')
            (fixture / (name + '.stdin.template')).write_text(stdin_text(binding, source, Path('@ADMITTED_RUN_DIR@'), layout))
    save(HERE / 'source-closure.json', {'entry': 'native_document_cli.vkf',
         'kind': 'conservative unnormalized local import graph', 'sources': source_refs,
         'edges': edges, 'external_module_names': sorted(external),
         'linked_closure_qualified': False,
         'required_actual_build_evidence': 'peer18 normalized hashes + actual compiler/runtime/stdlib/link receipts'})
    context = [pin(binding_path), pin(D301 / 'driver.py'), pin(normalizer),
               pin(REPO / 'integration/0.7.4/compiler-native-17/root-acceptance.json')]
    save(HERE / 'input-pins.json', context + [pin(x['path']) for x in refs] + source_refs)
    save(HERE / 'fixtures.json', {'binding': pin(binding_path), 'original': pin(original),
         'edited': pin(edit_path), 'edit': pin(fixture / 'edit.json'),
         'expected_pages': 40, 'expected_blocks': 430, 'legacy_pdf': binding['oracle'],
         'legacy_report': binding['report'], 'legacy_layout': binding['layout'],
         'edited_output_oracle': None, 'updated_40_pages_is_acceptance_requirement_not_observed': True,
         'source_closure': pin(HERE / 'source-closure.json'),
         'native_execution': False, 'native_pdf_qualified': False})
    print(json.dumps({'local_closure_modules': len(visited), 'external_modules': sorted(external),
                      'edit': edit, 'native_execution': False}))


if __name__ == '__main__':
    main()
