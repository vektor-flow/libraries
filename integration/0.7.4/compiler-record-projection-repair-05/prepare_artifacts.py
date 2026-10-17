"""Deterministic text-only packaging; never applies compiler sources or runs native code."""
from pathlib import Path
import difflib

HERE = Path(__file__).resolve().parent
review = (HERE / 'inherited/regression_layouts_supplemented.cpp').read_text()
add = (HERE / 'additional_cases.inc').read_text()
final = review.replace('int main() {', add + '\nint main() {\n    repair05_record_controls();\n    repair05_canonical_and_alias_controls();', 1)
(HERE / 'regression_layouts.cpp').write_text(final)
for before, after, name, af, bf in [
    (HERE / 'baseline/layouts_1.cpp', HERE / 'candidate/layouts_1.cpp', 'compiler.patch', 'a/compiler/native/value_layout/layouts_1.cpp', 'b/compiler/native/value_layout/layouts_1.cpp'),
    (HERE.parent / 'compiler-renderer-repair-02/candidate/layouts_1.cpp', HERE / 'candidate/layouts_1.cpp', 'held-candidate-delta.patch', 'a/compiler/native/value_layout/layouts_1.cpp', 'b/compiler/native/value_layout/layouts_1.cpp'),
    (HERE / 'inherited/regression_layouts_supplemented.cpp', HERE / 'regression_layouts.cpp', 'regression-additions.patch', 'a/regression_layouts.cpp', 'b/regression_layouts.cpp')]:
    (HERE / name).write_text(''.join(difflib.unified_diff(before.read_text().splitlines(True), after.read_text().splitlines(True), fromfile=af, tofile=bf)))
