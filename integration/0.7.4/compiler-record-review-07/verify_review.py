"""Independent bounded text/hash verification; NEVER executes compiler logic."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import resource
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPAIR = ROOT / "compiler-record-projection-repair-05"
OLD = ROOT / "compiler-renderer-repair-02"
REVIEW = ROOT / "compiler-candidate-review-04"
PROJECT = Path("/home/viktor/Projects/Vektor Flow")
GRANT = PROJECT / ".coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/compiler-record-review-07-visible-chat-grant.json"
OWNER = "01a14961-866a-7d10-a11f-704b6579bf75"
BASE = "6c9f9cf5d2b60c426f88402c0ae32c294191c26880614e71907354613e27c5bd"
HELD = "8ff80f95d154585cc0966cfb2b9b06ae441cb357017eb524c8b750616ae6161d"
FIXED = "226bb513fec0c2e1d9443fd9ac61d6ab863e9a3a136ab2238cf7d9346130307f"


def run():
    started = time.perf_counter()
    pins = {}

    def read(path, expected=None):
        path = Path(path)
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        if expected is not None:
            assert sha == expected, str(path)
        pins[str(path)] = {"path": str(path), "sha256": sha, "bytes": len(data)}
        return data.decode()

    grant = json.loads(read(GRANT))
    assert grant["owner_thread"] == OWNER
    assert grant["output_directory"] == str(HERE)
    assert grant["repository"] == str(ROOT.parent.parent)
    assert grant["source_commit"] == "84689e30101b6e5f8b6e1da6c1f36bbbb4345255"
    assert grant["native_execution"] is False
    for manifest in [REPAIR / "input-pins.json", REVIEW / "pins.json"]:
        for pin in json.loads(read(manifest)):
            source = read(pin["path"], pin["sha256"])
            assert len(source.encode()) == pin["bytes"]

    baseline = read(REPAIR / "baseline/layouts_1.cpp", BASE)
    held = read(OLD / "candidate/layouts_1.cpp", HELD)
    candidate = read(REPAIR / "candidate/layouts_1.cpp", FIXED)
    old_regression = read(OLD / "regression_layouts.cpp")
    review_regression = read(REVIEW / "regression_layouts_supplemented.cpp")
    regression = read(REPAIR / "regression_layouts.cpp")
    patches = []
    for before, after, file in [
        (baseline, candidate, REPAIR / "compiler.patch"),
        (held, candidate, REPAIR / "held-candidate-delta.patch"),
        (old_regression, review_regression, REVIEW / "regression-supplement.patch"),
        (review_regression, regression, REPAIR / "regression-additions.patch"),
    ]:
        patch = read(file)
        headers = patch.splitlines()
        regenerated = "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=headers[0][4:], tofile=headers[1][4:]))
        assert regenerated == patch, str(file)
        patches.append({"path": str(file), "exact_regenerated_diff": True,
                        "hunks": sum(x.startswith("@@ ") for x in headers)})

    inherited = []
    for original, copy in [
        *[(OLD / name, REPAIR / "inherited" / name) for name in
          ["regression_layouts.cpp", "test_reasoning.py", "real-ir-evidence.json"]],
        *[(p, REPAIR / "inherited/regressions" / p.name)
          for p in sorted((OLD / "regressions").glob("*.vkf"))],
        (REVIEW / "regression_layouts_supplemented.cpp",
         REPAIR / "inherited/regression_layouts_supplemented.cpp"),
    ]:
        assert read(original) == read(copy)
        inherited.append(str(copy))
    additions = read(REPAIR / "additional_cases.inc")
    assert review_regression.replace("int main() {", additions +
        "\nint main() {\n    repair05_record_controls();\n    repair05_canonical_and_alias_controls();", 1) == regression

    # Verify the semantic-review boundary: only the new helpers and replacement
    # fallback differ from review04's held source, including unchanged explicit
    # path traversal, numeric compatibility, and ordinary merge implementation.
    begin = candidate.index("namespace {\nusing ProjectionRecordFields")
    end = candidate.index("void refine_full_projection_path(", begin)
    restored = candidate[:begin] + candidate[end:]
    fallback = """else {
                const auto projected = counted_record_projection(current, candidate);
                current = projected ? *projected : candidate;
            }"""
    assert restored.count(fallback) == 1
    assert restored.replace(fallback, "else current = candidate;") == held
    for path in [REPAIR / "HANDOFF.txt", REPAIR / "SOURCE-REVIEW.txt",
                 REVIEW / "HANDOFF.txt", REVIEW / "FINDINGS.txt"]:
        read(path)
    # Re-read every input after checks to detect concurrent change.
    for pin in list(pins.values()):
        read(pin["path"], pin["sha256"])
    (HERE / "input-pins.json").write_text(json.dumps(list(pins.values()), indent=2) + "\n")
    result = {
        "owner": OWNER, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "result": "PASS", "scope": "source identity and textual invariants only",
        "unique_input_pins": len(pins), "all_inputs_unchanged_on_final_reread": True,
        "patches": patches, "inherited_files_identical": inherited,
        "review04_27_cases_and_negatives_unchanged": True,
        "held_source_restored_exactly": True, "candidate_sha256": FIXED,
        "native_executed": False, "model_executed": False,
        "seconds": time.perf_counter() - started,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "proc_self_vm_hwm": next(line.strip() for line in
            Path("/proc/self/status").read_text().splitlines() if line.startswith("VmHWM:")),
        "children_spawned_by_verifier": 0,
    }
    (HERE / "checks.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
