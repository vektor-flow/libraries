#!/usr/bin/env python3
"""Read-only source/selected-input verification; writes receipts only beside this file."""
import collections
import difflib
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import time

OUT = Path(__file__).resolve().parent
PEER = OUT.parent / 'compiler-build-preparation-03'
REPO = OUT.parents[2]

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(262144), b''):
            h.update(b)
    return h.hexdigest()

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2) + '\n')

def main():
    resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
    start = time.monotonic()
    pins = json.loads((OUT / 'input-pins.json').read_text())
    for p in pins:
        assert sha(p['path']) == p['sha256'], p['path']
    auth = json.loads((PEER / 'authentication.json').read_text())
    assert not auth['failures']
    rows = auth['inputs']
    assert len(rows) == 727
    by_real = collections.defaultdict(list)
    total = 0
    for row in rows:
        assert sha(row['path']) == row['sha256'], row['path']
        assert Path(row['path']).stat().st_size == row['bytes']
        total += row['bytes']
        if row['authority']:
            assert row['authority']['sha256'] == row['sha256']
            assert row['classification'] == 'recorded-pin-match'
            by_real[str(Path(row['path']).resolve())].append(row)
        else:
            assert row['classification'] == 'observed-only'
    observed = [r for r in rows if not r['authority']]
    assert len(observed) == 36
    groups = collections.Counter()
    classifications = []
    for row in observed:
        group = 'elf-dependency' if 'tool/runtime ELF dependency' in row['roles'] else 'tool' if 'tool' in row['roles'] else 'metadata-authority'
        groups[group] += 1
        aliases = [dict(path=r['path'], sha256=r['sha256'], authority=r['authority'])
                   for r in by_real[str(Path(row['path']).resolve())]
                   if r['sha256'] == row['sha256']]
        classifications.append(dict(**row, group=group, recorded_aliases=aliases))
    assert groups == {'metadata-authority': 10, 'tool': 7, 'elf-dependency': 19}
    assert sum(bool(r['recorded_aliases']) for r in classifications) == 1
    save('observed-only-classification.json', dict(literal_observed_only=36,
         group_counts=dict(groups), corroborated_by_recorded_alias=1,
         remaining_without_selected_path_or_alias_authority=35,
         historical_provenance_not_inferred=True, rows=classifications))

    changes = []
    names = ['prepare.py', 'payload.py', 'SPEC.txt', 'test_preparation.py']
    for name in names:
        before = (PEER / name).read_text().splitlines(keepends=True)
        after = (OUT / 'candidate' / name).read_text().splitlines(keepends=True)
        rel = str((PEER / name).relative_to(REPO))
        changes.extend(difflib.unified_diff(before, after, fromfile='a/'+rel, tofile='b/'+rel))
    patch = OUT / 'orchestration.patch'
    patch.write_text(''.join(changes))
    # --check never applies or writes the patch to the peer package.
    check = subprocess.run(['/usr/bin/git', 'apply', '--check', str(patch)],
                           cwd=REPO, text=True, capture_output=True, timeout=10)
    assert check.returncode == 0, check.stderr
    head = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    for p in pins:
        assert sha(p['path']) == p['sha256'], 'peer changed during review: '+p['path']
    save('verification.json', dict(assigned_head='84689e30101b6e5f8b6e1da6c1f36bbbb4345255',
         observed_head=head, input_pins_unchanged=len(pins), authenticated_inputs=len(rows),
         bytes_stream_hashed=total, hash_chunk_bytes=262144,
         recorded_pin_match=691, observed_only=36,
         patch_apply_check=dict(exit=check.returncode, stdout=check.stdout, stderr=check.stderr,
                                joined=True),
         seconds=time.monotonic()-start,
         address_space_limit_bytes=512*1024*1024,
         process_memory=[line for line in Path('/proc/self/status').read_text().splitlines()
                         if line.startswith(('VmPeak:', 'VmHWM:', 'VmRSS:'))],
         native_execution=False, outside_output_writes=False))
    print('PASS: source pins unchanged; 727 selected inputs; 36 rows classified; exact patch applies')

if __name__ == '__main__':
    main()
