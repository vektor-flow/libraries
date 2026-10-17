"""Bounded source/packaging checks ONLY. Does not execute or model new C++ helpers."""
from pathlib import Path
import hashlib
import json
import re
import time

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'compiler-renderer-repair-02'
REVIEW = HERE.parent / 'compiler-candidate-review-04'


def apply_in_memory(original, patch):
    lines = original.splitlines(keepends=True)
    changes = patch.splitlines(keepends=True)
    assert changes[0].startswith('--- ') and changes[1].startswith('+++ ')
    result, cursor, index, hunks = [], 0, 2, 0
    while index < len(changes):
        match = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@\n', changes[index])
        assert match, changes[index]
        start = int(match[1]) - 1
        assert start >= cursor
        result += lines[cursor:start]
        cursor = start
        consumed = produced = 0
        index += 1
        while index < len(changes) and not changes[index].startswith('@@ '):
            line = changes[index]
            assert line[0] in ' +-'
            if line[0] in ' -':
                assert lines[cursor] == line[1:]
                cursor += 1
                consumed += 1
            if line[0] in ' +':
                result.append(line[1:])
                produced += 1
            index += 1
        assert consumed == int(match[2] or 1)
        assert produced == int(match[4] or 1)
        hunks += 1
    return ''.join(result + lines[cursor:]), hunks


def verify():
    started = time.perf_counter()
    inputs = json.loads((HERE / 'input-pins.json').read_text())
    for pin in inputs:
        data = Path(pin['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == pin['sha256'], pin['path']
        assert len(data) == pin.get('bytes', len(data)), pin['path']
    patches = []
    for original, patch, wanted in [
        (HERE / 'baseline/layouts_1.cpp', HERE / 'compiler.patch', HERE / 'candidate/layouts_1.cpp'),
        (OLD / 'candidate/layouts_1.cpp', HERE / 'held-candidate-delta.patch', HERE / 'candidate/layouts_1.cpp'),
        (REVIEW / 'regression_layouts_supplemented.cpp', HERE / 'regression-additions.patch', HERE / 'regression_layouts.cpp')]:
        result, hunks = apply_in_memory(original.read_text(), patch.read_text())
        assert result == wanted.read_text(), patch
        patches.append({'patch': patch.name, 'hunks': hunks, 'exact_byte_match': True})
    inherited = []
    for name in ['regression_layouts.cpp', 'test_reasoning.py', 'real-ir-evidence.json']:
        assert (HERE / 'inherited' / name).read_bytes() == (OLD / name).read_bytes()
        inherited.append(name)
    for origin in sorted((OLD / 'regressions').glob('*')):
        assert origin.is_file()
        assert origin.read_bytes() == (HERE / 'inherited/regressions' / origin.name).read_bytes()
        inherited.append('regressions/' + origin.name)
    assert (HERE / 'inherited/regression_layouts_supplemented.cpp').read_bytes() == (REVIEW / 'regression_layouts_supplemented.cpp').read_bytes()
    inherited.append('regression_layouts_supplemented.cpp')
    candidate = (HERE / 'candidate/layouts_1.cpp').read_text()
    start = candidate.index('namespace {\nusing ProjectionRecordFields')
    end = candidate.index('void refine_full_projection_path(', start)
    restored = candidate[:start] + candidate[end:]
    replacement = '''else {
                const auto projected = counted_record_projection(current, candidate);
                current = projected ? *projected : candidate;
            }'''
    assert restored.count(replacement) == 1
    restored = restored.replace(replacement, 'else current = candidate;', 1)
    assert restored == (OLD / 'candidate/layouts_1.cpp').read_text()
    # Thus leaf guards, numeric compatibility, merge, and explicit path recursion
    # are byte-identical to the reviewed candidate; only named helpers/fallback differ.
    review = (REVIEW / 'regression_layouts_supplemented.cpp').read_text()
    additions = (HERE / 'additional_cases.inc').read_text()
    integrated = review.replace('int main() {', additions + '\nint main() {\n    repair05_record_controls();\n    repair05_canonical_and_alias_controls();', 1)
    assert integrated == (HERE / 'regression_layouts.cpp').read_text()
    result = {'scope': 'SOURCE/PACKAGING ONLY, no new helper execution',
              'input_pins': len(inputs), 'patches': patches,
              'byte_identical_inherited_files': inherited,
              'held_candidate_reconstructed_by_removing_only_helpers_and_fallback': True,
              'reviewer_cases_and_negative_controls_unchanged': True,
              'native_executed': False, 'seconds': time.perf_counter() - started,
              'candidate_sha256': hashlib.sha256(candidate.encode()).hexdigest()}
    return result


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
