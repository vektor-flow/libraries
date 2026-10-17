#!/usr/bin/env python3
"""Independent bounded source review. No VKF execution or source mutation.

Writes receipts only beside this script. Model cases are Python arithmetic checks,
not compiler/runtime results. Run with python3 -B source_check.py.
"""
from pathlib import Path
import difflib
import hashlib
import itertools
import json
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SRC = ROOT / 'examples/gpu-math/native-vkf'
PRIOR = OUT.parent / 'reference-repair'
BASE = 'e4df9851f6c9973b78d784da45e094703f972762'
inputs = {}
checks = []


def read(path):
    path = Path(path)
    b = path.read_bytes()
    inputs[str(path)] = hashlib.sha256(b).hexdigest()
    return b.decode()


def check(label, condition, **details):
    checks.append(dict(check=label, passed=bool(condition), **details))
    if not condition:
        raise AssertionError(label)


def declaration(text, name):
    return re.search(r'^' + name + r':\((.*)\)$', text, re.M)[1]


def imports(text):
    return re.findall(r'^\w+:\.(\w+)\s*$', text, re.M)


def rows(value):
    if isinstance(value, dict):
        if 'path' in value and 'sha256' in value:
            yield value
        for v in value.values():
            yield from rows(v)
    elif isinstance(value, list):
        for v in value:
            yield from rows(v)


def run():
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    check('exact review base', head == BASE, head=head)
    for name in ('HANDOFF.txt', 'PROPOSAL.txt', 'review.patch', 'prepare.py', 'artifact-pins.json'):
        read(PRIOR / name)
    for name in ('HANDOVER.txt', 'COORDINATOR-STATUS.txt'):
        read(OUT.parent / name)
    read(ROOT.parent.parent / '.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/reference-review-02-visible-chat-grant.json')
    read(OUT.parent / 'native-gates/entries/typed_packet_reference_harness_tests.vkf')
    read(OUT.parent / 'native-gates/prepare.py')
    read(OUT.parent / 'native-gates/manifest.json')
    provenance = json.loads(read(PRIOR / 'provenance.json'))
    reported = json.loads(read(PRIOR / 'static-checks.json'))
    for rel, digest in provenance['current_source_pins'].items():
        read(ROOT / rel)
        check('current pin ' + rel, inputs[str(ROOT / rel)] == digest)
    for rel, digest in provenance['candidate_pins'].items():
        read(PRIOR / rel)
        check('proposal candidate pin ' + rel, inputs[str(PRIOR / rel)] == digest)
    receipts = {}
    for path, digest in provenance['historical_receipts'].items():
        receipts[Path(path).name] = json.loads(read(path))
        check('historical receipt pin ' + Path(path).name, inputs[path] == digest)
    receipt_lists = [list(rows(receipts['plan.json']['renderer_source_pins'])),
                     list(rows(receipts['manifest.json']['inputs'])),
                     list(rows(receipts['posthashes.json']))]
    frozen = {}
    for item in provenance['historical_sources']:
        path, digest = item['path'], item['sha256']
        name = Path(path).stem
        original = read(path)
        check('historical source ' + name, inputs[path] == digest)
        for i, receipt in enumerate(receipt_lists):
            matches = [r for r in receipt if r['path'] == path]
            check(f'triple receipt {name}/{i}', bool(matches) and all(
                r['sha256'] == digest and (i != 2 or r.get('unchanged') is True) for r in matches))
        check('preserved original ' + name, read(PRIOR / 'original-reference' / (name + '.vkf')) == original)
        expected = re.sub(r'^(\w+:\.)(\w+)(\s*)$',
                          lambda m: m[1] + 'ref_f303_' + m[2] + m[3], original, flags=re.M)
        candidate = read(OUT / 'candidate' / ('ref_f303_' + name + '.vkf'))
        check('import targets only ' + name, candidate == expected)
        frozen['ref_f303_' + name] = candidate
    check('ten frozen modules', len(frozen) == reported['frozen_reference_modules'] == 10)
    for name, text in frozen.items():
        check('closed independent imports ' + name, all(i in frozen for i in imports(text)))
    reached = set()
    pending = ['ref_f303_document_scene_paragraph', 'ref_f303_document_scene_export']
    while pending:
        name = pending.pop()
        if name not in reached:
            reached.add(name)
            pending.extend(imports(frozen[name]))
    check('complete reachable reference/export closure', reached == set(frozen))
    c278 = provenance['c278_identity']
    c278_text = read(c278['path'])
    historical = read(PRIOR / 'original-reference/document_scene_paragraph.vkf')
    for alias, name in re.findall(r'^(\w+):\.(\w+)\s*$', historical, re.M):
        historical = re.sub(r'\b' + alias + r'\b', name, historical)
    check('C278 canonical source identity', historical == c278_text and inputs[c278['path']] == c278['sha256'])

    adapter = read(OUT / 'candidate/typed_packet_reference_adapter.vkf')
    harness = read(OUT / 'candidate/typed_packet_reference_harness_tests.vkf')
    original_harness = read(SRC / 'typed_packet_reference_harness_tests.vkf')
    linear = read(SRC / 'document_scene_paragraph_linear.vkf')
    legacy_fields = declaration(adapter, 'LegacyPacket')
    packet_fields = declaration(adapter, 'Packet')
    check('exact 31-field input alignment', len(legacy_fields.split(',')) == 31 and
          legacy_fields == declaration(harness, 'Packet') == declaration(frozen['ref_f303_document_scene_paragraph'], 'Packet'))
    check('exact 40-field current consumer declaration', len(packet_fields.split(',')) == 40 and
          packet_fields == declaration(linear, 'Packet'))
    for module in ('paragraph_scene_store', 'paragraph_scene_legacy', 'document_scene_paragraph_linear'):
        current = read(SRC / (module + '.vkf'))
        for name in ('Metadata', 'Paint', 'Payload', 'Leaf', 'Arena', 'Scene', 'Store'):
            check('recursive ABI ' + module + '/' + name,
                  declaration(adapter, name) == declaration(current, name))
    for name in ('Paint', 'Payload', 'Arena'):
        check('frozen exporter ABI ' + name, declaration(frozen['ref_f303_document_scene'], name) ==
              declaration(frozen['ref_f303_document_scene_export'], name))
    returned = re.search(r'^    @:\((.*)\)$', adapter, re.M)[1].split(',')
    returned = [part.split(':', 1) for part in returned]
    check('return order and count', [k for k, v in returned] == [f.split(':')[0] for f in packet_fields.split(',')])
    return_map = dict(returned)
    check('all 30 non-scene legacy fields forwarded exactly', all(
        return_map[name] == 'input.' + name for name in
        [f.split(':')[0] for f in legacy_fields.split(',')] if name != 'scenes'))
    check('absent authored origin and paired unknown arrays', return_map['a260_text'] == '""' and
          return_map['a260_starts'] == 'unknown_starts' and return_map['a260_stops'] == 'unknown_stops' and
          '[int] unknown_starts:[-1:operations]' in adapter and '[int] unknown_stops:[-1:operations]' in adapter)
    check('six empty event columns', all(return_map[n] == 'no_events' for n in
          ('a272_anchor_operations', 'a277_anchor_scenes', 'a280_anchor_leaves', 'a280_anchor_slots', 'a282_anchor_points')) and
          return_map['a272_anchor_ids'] == 'no_ids' and '[int] no_events:[0:0]' in adapter and
          adapter.index('no_ids:scenes.anchor_ids') < adapter.index('.scenes:legacy.append_legacy'))
    # All guards must precede allocation/indexing; retain original lower bounds.
    prefix = adapter.split('    operations:0')[0]
    for count, columns in [('glyph_count', ['keys', 'xs', 'ys', 'flow_lines', 'glyph_operations']),
                           ('scene_count', ['scenes', 'scene_xs', 'scene_ys', 'scene_lines', 'scene_operations'])]:
        check('nonnegative ' + count, 'input.' + count + '>=0' in prefix)
        for col in columns:
            check('active prefix guard ' + col, f'input.{count}<=input.{col}.length()' in prefix)
    # Evaluate exactly the simple source guard terms (no VKF execution).
    terms = re.findall(r'input\.(\w+)(>=0|<=input\.(\w+)\.length\(\))', prefix)
    def accepts(counts, lengths):
        return all(counts[count] >= 0 if op == '>=0' else counts[count] <= lengths[col]
                   for count, op, col in terms)
    lengths = {col: 2 for _, _, col in terms if col}
    counts = dict(glyph_count=2, scene_count=2)
    check('source guard valid prefixes', accepts(counts, lengths))
    malformed_cases = 0
    for col in lengths:
        short = dict(lengths, **{col: 1})
        check('source guard rejects short ' + col, not accepts(counts, short))
        malformed_cases += 1
    for name in counts:
        check('source guard rejects negative ' + name, not accepts(dict(counts, **{name: -1}), lengths))
        malformed_cases += 1
    check('zero active counts allow empty columns', accepts(dict(glyph_count=0, scene_count=0), dict.fromkeys(lengths, 0)))
    check('only active ordinals scanned', 'at<input.glyph_count?>' in adapter and 'at<input.scene_count?>' in adapter and
          adapter.count('(op>= -1)?!') == 2 and adapter.count('op>=operations? .operations:op+1') == 2)
    # Small independent arithmetic model; not a VKF interpreter or execution.
    def capacity(glyphs, gc, scenes, sc):
        if not (0 <= gc <= len(glyphs) and 0 <= sc <= len(scenes)):
            raise ValueError('bounds')
        active = glyphs[:gc] + scenes[:sc]
        if any(op < -1 for op in active):
            raise ValueError('domain')
        size = 0
        for op in active:
            if op >= size:
                size = op + 1
        return size
    model_cases = 0
    for ops in itertools.product((-2, -1, 0, 2, 5), repeat=4):
        for gc, sc in itertools.product(range(3), repeat=2):
            active = ops[:gc] + ops[2:2 + sc]
            try:
                got = capacity(ops[:2], gc, ops[2:], sc)
            except ValueError:
                assert any(op < -1 for op in active)
            else:
                assert got == max((op + 1 for op in active if op >= 0), default=0)
                assert all(-1 <= op <= got for op in active)
            model_cases += 1
    check('bounded independent ordinal model', model_cases == 5625, cases=model_cases)
    check('fixture capacities', [capacity((1, 5), gc, (2, 4), sc) for gc, sc in
          ((2, 2), (2, 0), (0, 2), (0, 0))] == [6, 6, 5, 0])
    check('current unknown spans accepted in source', '(start= -1 /\\ stop= -1)' in linear and
          'glyphs.(at)>starts.length()' in linear and 'q.a260_starts.(a260_op)>=0?' in linear)
    check('current consumer path retains rendered anchors', '@:a278_from_paragraph_mapped(q).scene' in linear and
          'anchor_count:flat.anchor_count' in linear and 'anchor_ids.(i):source_anchor_ids.(i)' in linear)

    assertions = lambda s: [line for line in s.splitlines() if '?!' in line]
    old_asserts = assertions(original_harness)
    expected_asserts = [l.replace('metadata_json.encode(a.metadata,a.metadata_roots.(i))', 'a.extras.(i)') for l in old_asserts]
    check('all assertion predicates preserved except declared representation operand', assertions(harness) == expected_asserts and len(old_asserts) == 286)
    check('harness otherwise exactly reviewed proposal', harness == read(PRIOR / 'candidate/typed_packet_reference_harness_tests.vkf'))
    original_js = read(SRC / 'document_scene_paragraph_linear_reference_tests.vkf')
    js_lines = [l for l in original_js.splitlines() if '?! "actual JS' in l]
    fixture_lines = [l for l in original_js.splitlines() if re.match(r'    index=\d\? values', l)]
    check('225 original literal JS assertions exact', len(js_lines) == 225 and all(l in harness.splitlines() for l in js_lines))
    check('five original JSON fixtures exact', len(fixture_lines) == 5 and all(l in harness.splitlines() for l in fixture_lines))
    check('four synthetic cases retained', all(f'compare(fixture({i}))?!' in harness for i in range(4)))

    # Explicitly expose, do not repair/normalize, a known equality failure.
    metadata = read(SRC / 'scene_metadata_json.vkf')
    check('source witness of strict metadata incompatibility', 'extra:""' in frozen['ref_f303_document_scene'] and
          'extras.(i):leaves.(i).extra' in frozen['ref_f303_document_scene'] and
          '[int] metadata_roots:[-1:count]' in linear and 'root<0? @:"{}"' in metadata and
          '(a.extras.(i)=metadata_json.encode(b.metadata,b.metadata_roots.(i)))?! "column extras exact"' in harness)
    # Deterministic full patch construction is independently compared; no apply.
    expected_patch = ''
    for path in sorted((OUT / 'candidate').glob('*.vkf')):
        rel = 'examples/gpu-math/native-vkf/' + path.name
        old = ROOT / rel
        expected_patch += ''.join(difflib.unified_diff(read(old).splitlines(True) if old.exists() else [],
                                 read(path).splitlines(True), fromfile='a/' + rel if old.exists() else '/dev/null', tofile='b/' + rel))
    check('self-contained exact twelve-file patch', read(OUT / 'final.patch') == expected_patch and
          len(list((OUT / 'candidate').glob('*.vkf'))) == 12)
    apply_check = subprocess.run(['git', '-C', str(ROOT), 'apply', '--check', str(OUT / 'final.patch')], capture_output=True, text=True)
    check('git apply --check only', apply_check.returncode == 0,
          exit_code=apply_check.returncode, stdout=apply_check.stdout, stderr=apply_check.stderr)
    # Confirm inputs did not change while checking them.
    check('all reviewed inputs unchanged during checks', all(
        hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest for path, digest in inputs.items()))
    return dict(status='source_checks_passed_with_acceptance_blocker',
                native_execution=False, acceptance_ready=False, base_commit=head,
                verified_current_pins=len(provenance['current_source_pins']),
                frozen_modules=10, historical_triple_pins=10,
                preserved_harness_assertions=286, preserved_JS_assertions=225,
                preserved_JSON_fixtures=5, ordinal_model_cases=model_cases,
                malformed_prefix_cases=malformed_cases,
                known_acceptance_blocker={'assertion': 'column extras exact',
                    'frozen_ordinary_extra': '', 'current_absent_metadata_encoding': '{}',
                    'evidence_kind': 'source derivation; no native execution'},
                checks=checks)


if __name__ == '__main__':
    try:
        result = run()
    except Exception as error:
        result = dict(status='source_check_failed', native_execution=False,
                      error=f'{type(error).__name__}: {error}', checks=checks)
    (OUT / 'source-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'input-pins.json').write_text(json.dumps(inputs, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, indent=2))
    raise SystemExit(1 if result['status'] == 'source_check_failed' else 0)
