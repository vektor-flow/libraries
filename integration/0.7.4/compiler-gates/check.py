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



def check_registered_supplement(path, manifest):
    # Exact reviewed supplemental artifact; never replace authoritative source nulls.
    verify({'path': str(path), 'sha256': '4357b885572e61043d9e2d780dfb20151a6c267e741ab7fa5ad4e54392166271'})
    supplement = json.loads(Path(path).read_text())
    if (supplement['schema'] != 1 or supplement['acceptance_credit'] != 0
            or any(supplement[k] is not False for k in
                   ('executed', 'execution_authorized', 'release_qualified'))):
        raise ValueError('Supplement cannot authorize execution or acceptance')
    verify(supplement['gate_manifest'])
    if json.loads(Path(supplement['gate_manifest']['path']).read_text()) != manifest:
        raise ValueError('Supplement belongs to another gate manifest')
    if supplement['ledger'] != manifest['ledger']:
        raise ValueError('Supplement belongs to another original ledger')
    for name in ('frozen_inventory', 'registration', 'ctest'):
        verify(supplement[name])
    inventory = json.loads(Path(supplement['frozen_inventory']['path']).read_text())
    registration = Path(supplement['registration']['path']).read_text().splitlines()
    ctest = Path(supplement['ctest']['path']).read_text().splitlines()
    expected = {r['id']: r for r in manifest['rows'] if r['category'] == 'registered-contract'}
    rows = supplement['rows']
    if len(rows) != 7 or len(expected) != 7 or {r['id'] for r in rows} != set(expected):
        raise ValueError('Supplement must cover exactly the seven registered identities')
    pins = []
    for recovered in rows:
        row = expected[recovered['id']]
        record = row['original_record']
        if (recovered['original_record_sha256'] != digest(record)
                or recovered['oracle_evidence_sha256'] != row['oracle_evidence_sha256']
                or recovered['original_source_sha256'] is not None
                or record['original_source_sha256'] is not None
                or recovered['status'] != 'held' or recovered['executable'] is not False
                or recovered['acceptance_credit'] != 0
                or recovered['policy_holds'] != row['policy_holds']):
            raise ValueError('Changed original identity/null/oracle/hold: ' + row['id'])
        if supplement['ctest'] != {'path': record['original_ctest_file'],
                                   'sha256': record['original_ctest_sha256']}:
            raise ValueError('Changed original CTest provenance: ' + row['id'])
        for name, line_key in (('original_command', 'ctest_command_line'),
                               ('original_properties', 'ctest_properties_line')):
            if (recovered[name] != record[name] or ctest.count(record[name]) != 1
                    or ctest[recovered[line_key] - 1] != record[name]):
                raise ValueError('Changed original registration: ' + row['id'])
        for span in recovered['registration_spans']:
            if '\n'.join(registration[span['first_line'] - 1:span['last_line']]) + '\n' != span['text']:
                raise ValueError('Changed original CMake registration: ' + row['id'])
        for source in recovered['sources']:
            verify(source)
            data = Path(source['path']).read_bytes()
            git = source['git']
            if (git['blob_sha256'] != source['sha256'] or
                    hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != git['blob_oid']):
                raise ValueError('Changed recovered Git blob: ' + source['path'])
            if 'inventory_key' in source:
                if (inventory['commit'] != git['commit'] or
                        inventory['files_sha256'][source['inventory_key']] != source['sha256']):
                    raise ValueError('Changed frozen inventory identity: ' + source['path'])
            else:
                provenance = record['supplemental_original_checker_provenance']
                if (provenance['seed_revision'] != git['commit'] or
                        provenance['fixture_sha256'] != source['sha256']):
                    raise ValueError('Changed ledger-pinned seed fixture')
            pins.append(source['path'])
    return {'verified_registered_contract_identities': len(rows),
            'verified_source_role_pins': len(pins), 'unique_source_files': len(set(pins)),
            'all_rows_held': True, 'authoritative_source_nulls_preserved': True,
            'acceptance_credit': 0,
            'limitation': 'Source/command identity only; helper dependencies, runtime provenance and execution remain unqualified.'}


def check(path, supplement_path=None):
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
    supplemental_result = check_registered_supplement(supplement_path, manifest) if supplement_path else None
    return {'registered_contract_source_supplement': supplemental_result, 'identity_metadata_valid': True, 'original_rows': len(rows), 'verified_source_hashes': verified_sources,
            'held_unavailable_source_identity': unavailable, 'oracle_forms': dict(oracle_forms),
            'executable_rows': 0, 'native_processes_started': 0, 'acceptance_credit': 0,
            'limitation': 'A successful metadata check is not an executable gate, source availability waiver, or permission to retry excluded scopes.'}


if __name__ == '__main__':
    try:
        print(json.dumps(check(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name('manifest.json'),
                               sys.argv[2] if len(sys.argv) > 2 else None), indent=2))
    except (KeyError, ValueError, OSError, TypeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
