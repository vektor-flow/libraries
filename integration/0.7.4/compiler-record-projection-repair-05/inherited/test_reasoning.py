"""NON-NATIVE branch model, not a compiler or a renderer qualification.

Models only ordinary primitive-vector layout joins and full field projection.
Inputs come from the retained real F364 typed IR, extracted by capture.py.
The pre-patch assertions intentionally demonstrate a bad storage decision;
the post-patch oracle requires the declared counted ABI for every call order.
"""
import itertools
import json
import unittest
from dataclasses import dataclass, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Layout:
    kind: str
    width: int
    items: tuple = ()
    element: object = None
    tuple_leaf: bool = False
    canonical: bool = True
    shared: bool = False


NUM = Layout("Numeric", 1)
STRING = Layout("String", 2)
COMPLEX = Layout("Complex", 2)


def fixed(element, count):
    return Layout("Aggregate", element.width * count, (element,) * count)


def counted(element):
    return Layout("DynamicF64List", 1, element=element)


def preserve(current, candidate):
    return (
        current.kind == "DynamicF64List" and current.width == 1
        and not current.items and not current.tuple_leaf and not current.shared
        and candidate.kind == "Aggregate" and not candidate.tuple_leaf
        and candidate.element is None and not candidate.shared
        and candidate.canonical and current.element in (NUM, STRING)
        and all(item == current.element for item in candidate.items)
    )


def merge(current, candidate, patched=False):
    # The exact relevant branches of core53 merge_inferred_layout. Other
    # compiler value kinds are deliberately outside this small host model.
    if current == candidate or (patched and preserve(current, candidate)):
        return current
    if current.kind == "Aggregate" and candidate.kind == "DynamicF64List":
        if all(item.kind in ("Numeric", "Complex") and
               candidate.element.kind in ("Numeric", "Complex") and
               (item == candidate.element or
                (item == NUM and candidate.element == COMPLEX))
               for item in current.items):
            return candidate
    if current.kind == candidate.kind == "DynamicF64List":
        return replace(current, element=merge(current.element, candidate.element, patched))
    if current.kind == candidate.kind == "Aggregate":
        items = [merge(a, b, patched) for a, b in zip(current.items, candidate.items)]
        items += list(current.items[len(items):])
        items += list(candidate.items[len(items):])
        return Layout("Aggregate", sum(x.width for x in items), tuple(items))
    if current == NUM and candidate.kind != "Numeric":
        return candidate
    if candidate.width > current.width or (
        candidate.width == current.width and len(candidate.items) > len(current.items)
    ):
        return candidate
    return current


def full_projection(current, candidate, patched=False):
    if patched and preserve(current, candidate):
        return current
    # Relevant differing-kind path at the terminal full projection:
    # compatible_numeric_shape rejects different kinds, then current=candidate.
    if current.kind != candidate.kind:
        return candidate
    return merge(current, candidate, patched)


def ordinary_call(current, candidate, patched=False):
    return merge(full_projection(current, candidate, patched), candidate, patched)


class Reasoning(unittest.TestCase):
    def test_real_ir_has_zero_one_and_nine_metadata_vectors(self):
        data = json.loads((HERE / "real-ir-evidence.json").read_text())
        counts = {x["lengths"]["texts"] for x in data["literal_metadata"]
                  if "texts" in x["lengths"]}
        self.assertTrue({1, 9} <= counts)
        empty = [x for x in data["literal_metadata"] if x["function"].endswith("__empty")]
        self.assertTrue(empty)
        self.assertEqual(empty[0]["lengths"]["numbers"], 0)
        self.assertTrue(all(x["declared_metadata"] == data["metadata_type"]
                            for x in data["append_parameters"]))

    def test_baseline_merge_narrows_counted_fields(self):
        for element in (NUM, STRING):
            for n in (1, 9):
                with self.subTest(element=element.kind, n=n):
                    self.assertEqual(merge(counted(element), fixed(element, n)), fixed(element, n))

    def test_baseline_full_projection_also_narrows_empty(self):
        for element in (NUM, STRING):
            self.assertEqual(full_projection(counted(element), fixed(element, 0)), fixed(element, 0))

    def test_baseline_string_join_cannot_recover_counted(self):
        inline = merge(counted(STRING), fixed(STRING, 9))
        self.assertEqual(merge(inline, counted(STRING)), inline)
        # In a record, numeric_1's conversion accepts fixed->counted, but
        # rejects counted->fixed. This pair is the wrong-direction boundary.
        self.assertEqual((counted(STRING).kind, inline.kind), ("DynamicF64List", "Aggregate"))

    def test_patch_preserves_counted_for_every_actual_order(self):
        for element in (NUM, STRING):
            choices = (fixed(element, 0), fixed(element, 1), fixed(element, 9), counted(element))
            for order in itertools.permutations(choices):
                current = counted(element)
                for actual in order:
                    current = ordinary_call(current, actual, True)
                    self.assertEqual(current, counted(element))

    def test_patch_does_not_certify_other_storage(self):
        bad = [fixed(COMPLEX, 1), fixed(Layout("Record", 3), 1),
               replace(fixed(NUM, 1), tuple_leaf=True),
               replace(fixed(NUM, 1), canonical=False),
               replace(fixed(NUM, 1), shared=True), counted(NUM)]
        for actual in bad:
            self.assertFalse(preserve(counted(NUM), actual))
        self.assertFalse(preserve(counted(COMPLEX), fixed(NUM, 1)))
        self.assertFalse(preserve(fixed(NUM, 9), fixed(NUM, 1)))

    def test_fixed_extent_and_numeric_promotion_decisions_unchanged(self):
        cases = [(fixed(NUM, 9), fixed(NUM, 1)), (NUM, COMPLEX),
                 (counted(NUM), fixed(COMPLEX, 1)),
                 (fixed(NUM, 1), counted(COMPLEX))]
        for current, actual in cases:
            self.assertEqual(merge(current, actual), merge(current, actual, True))
            self.assertEqual(full_projection(current, actual), full_projection(current, actual, True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
