#!/usr/bin/env python3
"""Read-only original-obligation identity check. No subprocesses or file writes."""
import collections
import hashlib
import json
from pathlib import Path
import sys


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify(pin):
    path = Path(pin['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != pin['sha256']:
        raise ValueError('Changed pinned input: ' + str(path))


def check(path):
    manifest = json.loads(Path(path).read_text())
    if any(manifest[k] is not False for k in ('executed', 'execution_authorized', 'release_qualified')):
        raise ValueError('Preparation cannot authorize execution or claim acceptance')
    verify(manifest['ledger'])
    ledger = json.loads(Path(manifest['ledger']['path']).read_text())
    original = {row['key']: row for row in ledger['rows'] if not row.get('current_closure_credit')}
    if len(ledger['rows']) != 419 or len(original) != 126 or ledger['current_closed'] != 293:
        raise ValueError('Original ledger counts changed; explicit reconciliation required')
    rows = manifest['rows']
    if len(rows) != 126 or len({r['id'] for r in rows}) != 126 or set(original) != {r['id'] for r in rows}:
        raise ValueError('Original identity set changed')
    tools = manifest['toolchain']
    for pin in [manifest['pin_provenance'], tools['compiler'], *tools['runtime'], *tools['stdlib'], *manifest['policy_evidence']]:
        verify(pin)
    verified_sources = 0
    unavailable = []
    oracle_forms = collections.Counter()
    for row in rows:
        identity = row['id']
        record = original[identity]
        if row['original_record'] != record or row['original_record_sha256'] != digest(record):
            raise ValueError('Changed original record: ' + identity)
        if row['executable'] is not False or row['status'] != 'held' or not row['policy_holds']:
            raise ValueError('Execution/scope authorization must not be inferred: ' + identity)
        if row['backend'] != record['backend']:
            raise ValueError('Changed original backend: ' + identity)
        supplemental = record.get('supplemental_identity', {})
        case = supplemental.get('original_case', {})
        source_path = record.get('fixture') or record.get('supplemental_fixture') or supplemental.get('fixture')
        source_hash = record.get('original_source_sha256') or record.get('supplemental_source_sha256') or supplemental.get('original_source_sha256')
        expected_source = {'path': source_path, 'sha256': source_hash, 'embedded_text': case.get('source') if not source_path else None}
        if row['source'] != expected_source:
            raise ValueError('Changed original source locator/hash: ' + identity)
        if source_hash and source_path:
            if Path(source_path).is_file():
                verify({'path': source_path, 'sha256': source_hash})
                verified_sources += 1
            else:
                unavailable.append({'id': identity, 'reason': 'Original source file unavailable', 'path': source_path})
        elif source_hash and isinstance(expected_source['embedded_text'], str):
            if hashlib.sha256(expected_source['embedded_text'].encode()).hexdigest() != source_hash:
                raise ValueError('Changed embedded original source: ' + identity)
            verified_sources += 1
        else:
            unavailable.append({'id': identity, 'reason': 'No independent exact source locator/hash; original null/contract identity preserved'})
        payload = {k: record[k] for k in ('oracle', 'original_benchmark_oracle', 'original_command', 'original_properties', 'original_contract_row', 'original_camera_pair_oracles') if k in record}
        if case:
            payload['supplemental_original_case'] = case
        if row['oracle_evidence'] != payload or row['oracle_evidence_sha256'] != digest(payload):
            raise ValueError('Changed original oracle evidence: ' + identity)
        if 'oracle' in record:
            if digest(record['oracle']) != record['oracle_sha256']:
                raise ValueError('Original oracle hash mismatch: ' + identity)
            oracle_forms['explicit_hashed_oracle'] += 1
        else:
            oracle_forms['retained_contract_or_evidence_not_executable_oracle'] += 1
    counts = dict(collections.Counter(row['category'] for row in rows))
    if counts != manifest['category_counts']:
        raise ValueError('Category counts changed')
    return {'identity_metadata_valid': True, 'original_rows': len(rows), 'verified_source_hashes': verified_sources,
            'held_unavailable_source_identity': unavailable, 'oracle_forms': dict(oracle_forms),
            'executable_rows': 0, 'native_processes_started': 0, 'acceptance_credit': 0,
            'limitation': 'A successful metadata check is not an executable gate, source availability waiver, or permission to retry excluded scopes.'}


if __name__ == '__main__':
    try:
        print(json.dumps(check(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name('manifest.json')), indent=2))
    except (KeyError, ValueError, OSError, TypeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
