#!/usr/bin/env python3
"""Prepare pinned native regression cases. Never starts a native process."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE = REPO / 'examples/gpu-math/native-vkf'
INVENTORY = Path('/mnt/development/CompilerOptimization/latex074-integrated-20261017/integration-config.json')
IMPORT = re.compile(r'^([A-Za-z_]\w*)\s*:\s*\.([A-Za-z_]\w*)\s*(?:#.*)?$', re.M)
ASSERTION_CONTROL = {'path': '/home/viktor/.cache/vkf-s0-runtimes-20261012/Integrator/independent-worker-F/iteration354-assertion01/reviewed-contract.json', 'sha256': 'e0d84d1e59853a55061da727c113071e51223758a523ab6388bf4a67f9b701ce'}
OWNER = '01a14893-cb1e-7203-97dd-de3da44dcf31'
ROUTES = {
    'latex_document_routes_regression_tests_b347_adapter': 'routes_tests',
    'latex_label_routes_regression_tests_b347_adapter': 'label_routes_tests',
    'latex_outer_routes_regression_tests_b347_adapter': 'outer_routes_tests',
}
REJECTIONS = {
    'reject_changed_source': 'Unbound resolved parser source',
    'reject_duplicate': 'Duplicate provenance route',
    'reject_missing_column': 'Provenance route column mismatch',
    'reject_out_of_range': 'Invalid provenance route',
    'reject_label_text': 'Unbound resolved parser source',
    'reject_label_duplicate': 'Duplicate provenance route',
    'reject_unknown_producer': 'Unknown provenance producer kind',
    'reject_kind_length': 'Provenance kind column mismatch',
    'reject_outer_source': 'Unbound resolved parser source',
    'reject_outer_duplicate': 'Duplicate provenance route',
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha(path.read_bytes())}

def verify(p):
    if pin(p['path'])['sha256'] != p['sha256']:
        raise ValueError('input changed: ' + p['path'])

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def imports(text):
    for line in text.splitlines():
        if re.match(r'^\w+\s*:\s*\.', line) and not IMPORT.fullmatch(line):
            raise ValueError('unsupported import spelling: ' + line)
    return [m[2] for m in IMPORT.finditer(text)]

def prepare():
    verify(ASSERTION_CONTROL)
    old = json.loads(INVENTORY.read_text())
    recipe_path = Path(json.loads((REPO/'integration/0.7.4/toolchain-pins.json').read_text())['recipe'])
    recipe = json.loads(recipe_path.read_text())
    modules = {}
    texts = {}
    external = recipe['external']
    if isinstance(external, list):
        external = {Path(p['path']).stem: p for p in external}
    for n, historical in old['reference'].items():
        current = pin(SOURCE/(n+'.vkf'))
        if current['sha256'] != historical['sha256']:
            raise ValueError('independent frozen reference changed: ' + n)
    closure_cache = {}
    def visit(n, active):
        if n in closure_cache:
            return closure_cache[n].copy()
        if n in external:
            verify(external[n]); return set()
        if n in active:
            return set()
        path = SOURCE/(n+'.vkf')
        if not path.is_file():
            raise ValueError('missing shared-source module: '+n)
        text = path.read_text()
        if n.startswith('frozen285_') and n not in old['reference']:
            raise ValueError('unauthenticated frozen reference: '+n)
        deps = imports(text)
        if n.startswith('frozen285_') and any(not d.startswith('frozen285_') and d not in external for d in deps):
            raise ValueError('reference leaks into candidate: '+n)
        modules[n] = {**pin(path), 'imports': deps, 'reference': n.startswith('frozen285_')}
        texts[n] = text
        found = {n}
        for d in deps:
            found |= visit(d, active | {n})
        closure_cache[n] = found.copy()
        return found
    cases = []
    equivalent_sources = {}
    wrappers = HERE/'entries'
    wrappers.mkdir(exist_ok=True)
    for suite in old['suites']:
        try:
            closure = sorted(visit(suite, set()))
            text = texts[suite]
            error = None
        except (ValueError, OSError) as exc:
            closure = []; text = (SOURCE/(suite+'.vkf')).read_text(); error = str(exc)
        # Each generated derivative retains every assertion in the source suite.
        # Rename a main definition so there is exactly one explicit invocation,
        # independent of compiler implicit-main conventions.
        if suite in ROUTES:
            entry = ROUTES[suite] + '()'
            derivative = text + '\n(' + entry + ')?! "Native gate entry returned false"\n'
        elif re.search(r'^main\(\):', text, re.M):
            entry = 'native_gate_main()'
            derivative = re.sub(r'^main\(\):', 'native_gate_main():', text, flags=re.M) + '\n' + entry + '\n'
        elif re.search(r'^\(run\(\)\)\?!', text, re.M):
            entry = 'run() (existing checked top-level invocation)'; derivative = text
        elif re.search(r'^(renderer_tests|tests)\(\)$', text, re.M):
            entry = re.search(r'^(renderer_tests|tests)\(\)$', text, re.M)[0]
            derivative = re.sub(r'^(renderer_tests|tests)\(\)$', r'(\1())?! "Native gate entry returned false"', text, flags=re.M)
        else:
            entry = None; derivative = text; error = error or 'No established executable assertion entry'
        negative = suite in ('paragraph_scene_store_malformed_tests', 'paragraph_scene_store_invalid_id_tests')
        wrapper = wrappers/(suite+'.vkf')
        wrapper.write_text(derivative)
        case = {'id': suite, 'suite': suite, 'kind': 'rejection' if negative else 'positive',
                'status': 'blocked' if error else 'ready', 'blocked_reason': error,
                'entry': entry, 'entry_source': pin(wrapper), 'closure': closure,
                'stdin': old['stdin'][suite], 'assertion_count': text.count('?!'),
                'expected_exit': 1 if negative else 0, 'expected_stdout': '' if negative else None, 'expected_stderr': None, 'timeout_seconds': 30}
        if negative:
            case['expected_diagnostic'] = 'Invalid retained scene ID' if 'invalid_id' in suite else 'Invalid retained scene JSON'
            case['expected_stderr'] = case['expected_diagnostic'] + '\n'
        digest = sha(text.encode())
        case['identical_source_to'] = equivalent_sources.get(digest)
        equivalent_sources.setdefault(digest, suite)
        cases.append(case)
        for name in re.findall(r'^(reject_\w+)\(', text, re.M):
            name_path = wrappers/(suite+'__'+name+'.vkf')
            name_path.write_text(text+'\n'+name+'()\n')
            cases.append({'id': suite+'__'+name, 'suite': suite, 'kind': 'rejection',
                'status': 'blocked' if error or name not in REJECTIONS else 'ready', 'blocked_reason': error or (None if name in REJECTIONS else 'Unknown rejection diagnostic'),
                'entry': name+'()', 'entry_source': pin(name_path), 'closure': closure,
                'stdin': '', 'expected_exit': 1, 'expected_diagnostic': REJECTIONS.get(name), 'expected_stdout': '', 'expected_stderr': REJECTIONS.get(name, '')+'\n',
                'timeout_seconds': 30})
    tools = recipe['tools'] + recipe['runtime'] + recipe['stdlib']
    for p in tools + old['assets']:
        verify(p)
    result = {'schema': 1, 'owner': OWNER, 'source_root': str(SOURCE),
        'suite_count': len(old['suites']), 'case_count': len(cases), 'executed': False,
        'release_qualified': False, 'origin_inventory': pin(INVENTORY),
        'recipe': pin(recipe_path), 'preparer': pin(__file__), 'assertion_control': ASSERTION_CONTROL,
        'environment': recipe['environment'], 'unset': recipe['unset'],
        'tools': recipe['tools'], 'runtime': recipe['runtime'], 'stdlib': recipe['stdlib'],
        'external': external, 'assets': old['assets'], 'modules': modules, 'cases': cases,
        'summary': {'ready_cases': sum(c['status']=='ready' for c in cases),
                    'blocked_cases': sum(c['status']=='blocked' for c in cases), 'passed': 0},
        'execution_policy': 'External coordinator guarded launch only; fresh admission must pin this manifest, all inputs and output paths. No native execution is provided by this tool.'}
    write(HERE/'manifest.json', result)
    print(json.dumps(result['summary']))

def check(manifest):
    m = json.loads(Path(manifest).read_text())
    pins = [m['origin_inventory'], m['recipe'], m['preparer'], m['assertion_control']] + m['tools'] + m['runtime'] + m['stdlib'] + m['assets'] + list(m['external'].values())
    pins += list(m['modules'].values()) + [c['entry_source'] for c in m['cases']]
    for p in pins: verify(p)
    for c in m['cases']:
        if c['status']=='ready' and (not c['entry'] or (c['kind']=='positive' and c['assertion_count']<1)):
            raise ValueError('empty assertion entry: '+c['id'])
        for n in c['closure']:
            for d in m['modules'][n]['imports']:
                if d not in c['closure'] and d not in m['external']:
                    raise ValueError('incomplete closure: '+c['id']+' -> '+d)
    return m

def plan(manifest, output):
    m = check(manifest)
    root = Path(output).resolve()
    normalizers = [p for p in m['tools'] if Path(p['path']).resolve() == SOURCE/'normalize_module_aliases.py']
    compilers = [p for p in m['tools'] if Path(p['path']).name == 'vkf-strict']
    if len(normalizers) != 1 or len(compilers) != 1:
        raise ValueError('Expected exactly one pinned shared normalizer and strict compiler')
    normalizer, compiler = normalizers[0], compilers[0]
    stages=[]
    for c in m['cases']:
        if c['status'] != 'ready': continue
        base=root/c['id']; raw=base/'raw'; normalized=base/'normalized'
        stages.append({'id': c['id'], 'timeout_seconds': 30,
            'cwd': str(base),
            'stdlib_symlinks': [{'source': q, 'destination': str(base/Path(q['path']).relative_to(m['environment']['VKF_HOME']))} for q in m['stdlib']],
            'materialize': [{'source': m['modules'][n], 'destination': str(raw/(n+'.vkf'))} for n in c['closure'] if n != c['suite']] + [{'source': c['entry_source'], 'destination': str(raw/(c['suite']+'.vkf'))}],
            'normalize': ['/usr/bin/python3','-B',normalizer['path'],'--source-dir',str(raw),'--output-dir',str(normalized)],
            'compile': [compiler['path'],'-b',str(normalized/'source'/(c['suite']+'.vkf')),'-o',str(base/'case.exe'),'--diagnostics'],
            'run': [str(base/'case.exe')], 'stdin': c['stdin'], 'expected_exit': c['expected_exit'], 'expected_stdout': c['expected_stdout'], 'expected_stderr': c['expected_stderr']})
    print(json.dumps({'manifest': pin(manifest), 'output_root': str(root),
        'environment': m['environment'], 'unset': m['unset'],
        'required_stdlib_symlinks': m['stdlib'], 'stages': stages,
        'guard_required': True, 'executed': False},indent=2))

def assess(manifest, receipt):
    m=check(manifest); r=json.loads(Path(receipt).read_text())
    if r['manifest'] != pin(manifest) or r['owner'] != OWNER:
        raise ValueError('foreign execution receipt')
    # The receipt is evidence from the external guard, not execution permission.
    seen={}
    for row in r['cases']:
        if row['id'] in seen: raise ValueError('duplicate result')
        seen[row['id']]=row
    ids={c['id'] for c in m['cases']}
    if set(seen)-ids: raise ValueError('unknown result')
    passed=[]; failed=[]; blocked=[]
    for c in m['cases']:
        if c['status']!='ready': blocked.append(c['id']); continue
        row=seen.get(c['id'],{})
        ok=True
        for stage in ('normalize','compile','run'):
            s=row.get(stage,{})
            ok &= (s.get('exit')==(c.get('expected_exit',0) if stage=='run' else 0) and s.get('timed_out') is False and
                   s.get('no_live_descendants') is True and
                   isinstance(s.get('elapsed_seconds'),(float,int)) and
                   0 <= s['elapsed_seconds'] <= 30)
        for field in ('stdout','stderr'):
            expected=c.get('expected_'+field)
            if expected is not None:
                log=row.get('run',{}).get(field)
                if not isinstance(log,dict): ok=False; continue
                verify(log)
                ok &= Path(log['path']).read_bytes()==expected.encode()
        ok &= row.get('posthash_match') is True and row.get('binary_produced') is True
        (passed if ok else failed).append(c['id'])
    summary={'reported_success_cases_UNVERIFIED':passed,'failed_or_missing_cases':failed,'blocked_cases':blocked,
        'execution_verified':False, 'pass_totals':None, 'all37_pass':False,'release_qualified':False,
        'limitation':'Untrusted summary only: external controller/guard receipt, terminal join, executable hash, actual argv/stdin and source binding must be authenticated by coordinator before any real pass claim.'}
    print(json.dumps(summary,indent=2))
    # There is deliberately no successful qualification exit without a pinned
    # external guard evidence contract. A fabricated summary can never pass.
    return 1

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','check','plan','assess'])
    p.add_argument('--manifest',default=str(HERE/'manifest.json'))
    p.add_argument('--output-root');p.add_argument('--receipt')
    a=p.parse_args()
    if a.action=='prepare': prepare()
    elif a.action=='check': check(a.manifest); print('Pins, entries and closures verified; no native execution.')
    elif a.action=='plan':
        if not a.output_root:p.error('--output-root required')
        plan(a.manifest,a.output_root)
    else:
        if not a.receipt:p.error('--receipt required')
        return assess(a.manifest,a.receipt)
    return 0
if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,KeyError,OSError) as error:
        print(str(error),file=sys.stderr);sys.exit(2)
