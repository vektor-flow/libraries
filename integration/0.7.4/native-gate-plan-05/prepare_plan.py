"""Read-only source/receipt reconciliation; writes only this directory. No launcher."""
import hashlib
import json
import pathlib
import re
import struct
import subprocess
import time

OUT = pathlib.Path(__file__).resolve().parent
REPO = OUT.parents[2]
PROJECT = REPO.parent.parent
SRC = REPO / 'examples/gpu-math/native-vkf'
F = pathlib.Path('/home/viktor/.cache/vkf-s0-runtimes-20261012/Integrator/independent-worker-F')
BASE = '5747ff8008ccd580b1b45ebc26560ffb0cda33fa'
started = time.monotonic()
pins = {}
checks = []

def pin(path):
    p = pathlib.Path(path).absolute()
    with p.open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    v = dict(path=str(p), sha256=sha, bytes=p.stat().st_size)
    pins[str(p)] = v
    return v

def read(path):
    pin(path)
    return json.loads(pathlib.Path(path).read_text())

def write(name, obj):
    (OUT/name).write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n')

def check(label, value):
    assert value, label
    checks.append(label)

def references(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get('path'), str) and isinstance(obj.get('sha256'), str):
            yield obj
        for v in obj.values():
            yield from references(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from references(v)

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
check('exact authorized HEAD', head == BASE)
branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=REPO, text=True).strip()
check('authorized branch', branch == 'consolidate/0.7.4-shared-base-20261017')
manifest_path = OUT.parent/'native-gates/manifest.json'
m = read(manifest_path)
for p in references(m):
    check('current manifest SHA256 '+p['path'], pin(p['path'])['sha256'] == p['sha256'])
for rel in ['HANDOVER.txt','COORDINATOR-STATUS.txt','serialization-boundary-04/HANDOFF.txt',
            'serialization-boundary-04/REVIEW.txt','pdf-api-integration-01/HANDOFF.txt',
            'native-gates/README.txt','native-gates/prepare.py','pdf-api-acceptance/ACCEPTANCE.txt']:
    pin(OUT.parent/rel)
coord = PROJECT/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb'
for name in ['native-gate-plan-05-visible-chat-grant.json','storage-live-04-visible-chat-grant.json']:
    pin(coord/name)
pin(PROJECT/'.coordination/0136/Proof/original419-reconciliation.json')
pin('/home/viktor/Projects/AGENTS.md')
pin(REPO/'STATUS.md')
pin(__file__)

cases = {c['id']: c for c in m['cases']}
passed = {}
history_checks = []
stages = []
controls = []
attempts = ['iteration355-rejections01','iteration356-routes01','iteration357-grouped04',
            'iteration359-provenance01','iteration364-scene-ten01']
for attempt in attempts:
    directory = F/attempt
    review = read(directory/'reviewed-results.json')
    results = read(directory/'results.json')
    # Reverify exact pins embedded in original reviews, preserving historical missing/drift status.
    for p in references(review):
        path = pathlib.Path(p['path'])
        actual = pin(path)['sha256'] if path.is_file() else None
        history_checks.append(dict(attempt=attempt, **p, actual_sha256=actual,
                                   matches=actual == p['sha256']))
    if attempt == 'iteration355-rejections01':
        for i, c in enumerate(results['cases']):
            if c.get('passed'):
                row = c['stages'][-1]
                passed[c['id']] = dict(attempt=attempt, result_pointer=f'/cases/{i}',
                    receipt=pin(directory/'results.json'), run=row)
                check('F355 exact exit '+c['id'], row['exit'] == c['expected_exit'])
                for stream in ['stdout','stderr']:
                    p = row[stream]
                    check('F355 raw '+stream+' '+c['id'], pin(p['path'])['sha256'] == p['sha256']
                          and pathlib.Path(p['path']).read_text() == c['expected_'+stream])
        rows = [s for c in results['cases'] for s in c['stages']]
    else:
        planfile = 'plan.json' if attempt in attempts[1:3] else 'execution-plan.json'
        plan = read(directory/planfile)
        rows = results['rows']
        for s in plan['suites']:
            for index, run in enumerate(s['runs']):
                cid = run['id']
                if cid not in results.get('passed', []):
                    continue
                row_index, row = next((i, row) for i,row in enumerate(rows)
                                      if row['suite'] == s['id'] and row['name'] == f'run{index}')
                check('exact historical exit '+cid, row['exit'] == run['expected_exit'])
                for stream in ['stdout','stderr']:
                    p = row[stream]
                    check('historical output pin '+cid+' '+stream, pin(p['path'])['sha256'] == p['sha256'])
                    if run.get('expected_'+stream) is not None:
                        check('historical output contract '+cid+' '+stream,
                              pathlib.Path(p['path']).read_text() == run['expected_'+stream])
                if cid in cases:
                    passed[cid] = dict(attempt=attempt, result_pointer=f'/rows/{row_index}',
                        receipt=pin(directory/'results.json'), plan=pin(directory/planfile), run=row,
                        expected_exit=run['expected_exit'], expected_stdout=run.get('expected_stdout'),
                        expected_stderr=run.get('expected_stderr'))
                else:
                    controls.append(dict(id=cid, attempt=attempt, credited_to_native47=False))
    for row in rows:
        check('original row joined '+attempt+' '+row['name'], row['join']['no_live_descendants']
              and not row['join']['timed_out'] and not row['join'].get('remaining_identities'))
        stages.append(dict(attempt=attempt, name=row['name'], suite=row.get('suite'),
                           exit=row['exit'], elapsed_seconds=row['elapsed_seconds'],
                           deadline_seconds=row['deadline_seconds'], join=row['join']))

blocked_plan = read(F/'iteration364-scene-ten01/execution-plan.json')
blocked = [r['id'] for s in blocked_plan['suites'] for r in s['runs'] if r['id'] in cases]
reference = 'typed_packet_reference_harness_tests'
remaining = [c for c in cases if c not in passed and c not in blocked and c != reference]
check('18 unique historical passes', len(passed) == 18)
check('10 exact F364 requested positives', len(blocked) == 10)
check('18 not yet run positives', len(remaining) == 18 and all(cases[c]['kind']=='positive' for c in remaining))
check('disjoint complete 47 partition', len(set(passed)|set(blocked)|set(remaining)|{reference}) == 47)
check('remaining closure overlap only, not observed failure', all('document_scene' in cases[c]['closure'] for c in remaining))
reconciliation = dict(native47_passed=18, native47_unqualified=29, original419_credited=293,
    historical_passes=passed, known_F364_group_compile_blocked=blocked,
    separately_held_reference=reference, not_yet_run_positive=remaining,
    controls_not_credited=controls, historical_pin_rechecks=history_checks,
    original_stage_timings_and_joins=stages,
    caveat='Historical receipt mapping only: no new credit or rebasing old binaries onto current source. F364 observed one grouped compile failure, not ten individual failures. Remaining18 share imports; their individual compiler outcome is unknown.')
write('reconciliation.json', reconciliation)

inventory = []
for cid,c in cases.items():
    entry=pathlib.Path(c['entry_source']['path'])
    state = 'historical_pass' if cid in passed else 'F364_group_blocked' if cid in blocked else 'reference_held' if cid==reference else 'not_yet_run_overlap_held'
    inventory.append(dict(**c, disposition=state, application_launch_eligible=False,
        exact_entry_assertions=[dict(line=i,text=line) for i,line in enumerate(entry.read_text().splitlines(),1) if '?!' in line],
        source_closure_pins={name:m['modules'][name] for name in c['closure']},
        stdin_sha256=hashlib.sha256(c['stdin'].encode()).hexdigest(),
        artifact_estimate_bytes=None,
        estimate_reason='No application launch proposed; shared-import overlap is not disjointness proof. No closure variants investigated.'))
write('application-inventory.json', inventory)

numeric = pin(SRC/'test_json_binary64.vkf')
imports = re.findall(r'^\w+\s*:\s*\.(\w+)', (SRC/'test_json_binary64.vkf').read_text(), re.M)
check('numeric module has no imports', imports == [])
specs=[('int64.vkf','int64 literal/rank arithmetic and exact integer digit extraction'),
       ('extraction.vkf','binary64 scaling and int significand extraction against literal IEEE-754 ranks'),
       ('unicode.vkf','UTF-8 byte offsets, scalar cursor, chr/int and exact scalar equality')]
entries=[]
for i,(name, oracle) in enumerate(specs,1):
    p=OUT/name
    text=p.read_text()
    check('primitive exact import '+name, re.findall(r'^\w+\s*:\s*\.(\w+)',text,re.M)==['test_json_binary64'])
    entries.append(dict(order=i,id=p.stem,entry_source=pin(p),source_closure=[numeric],oracle=oracle,
        assertions=[dict(line=j,text=line) for j,line in enumerate(text.splitlines(),1) if '?!' in line]))
syntax=OUT.parent/'pdf-api-acceptance/named-syntax.vkf'
check('actual syntax fixture no imports', not re.findall(r'^\w+\s*:\s*\.',syntax.read_text(),re.M))
entries.append(dict(order=4,id='native_named_syntax_dependency',entry_source=pin(syntax),source_closure=[],
    oracle='Existing exact fixture: combine(2,second:3)=5 and combine(2)=2. Syntax/default dependency only; no latex API/resources/PDF acceptance.',
    assertions=[dict(line=j,text=line) for j,line in enumerate(syntax.read_text().splitlines(),1) if '?!' in line]))
components=dict(raw_normalized_snapshots_and_metadata=8*2**20,compiler_temporaries_and_diagnostics=512*2**20,
    executable_and_link_outputs=128*2**20,private_tmp_home_cache=64*2**20,
    logs_receipts_join_evidence=16*2**20,allocated_block_slack_and_uncertainty=296*2**20)
for e in entries:
    e.update(preparation_only=True,native_executed=False,launch_authority=False,
        disjointness='Imports only test_json_binary64 (which imports nothing), or no imports for syntax; no renderer/provider/scene/compose or excluded implementation scope. Toolchain/runtime primitives remain shared and unqualified.',
        stdin='',stdin_sha256=hashlib.sha256(b'').hexdigest(),expected_exit=0,expected_stdout='',expected_stderr='',
        deadlines_seconds=dict(normalize=30,compile=30,run=30),
        inclusive_artifact_estimate_bytes=sum(components.values()),artifact_components_bytes=components,
        estimate_basis='Provisional conservative planning allowance, not measured demand or admission. F355 underestimated 512MiB and retained 927752192 allocated bytes; F359 retained about429MB. Account every fresh raw/normalized/temp/cache/compiler/link/log/receipt path, including failures. No refund assumed.',
        admission_dependencies=['Storage-live-04 operational qualification reviewed by coordinator','Fresh exact owner/source/tool/output/resource grant','One entry at a time; stop on first unexpected result; no unchanged retry','Independent pre/posthashes, binary hash, actual stdout/stderr, PID/starttime descendant and service joins; retain all artifacts'])
write('plan.json',dict(source_commit=BASE,branch=branch,owner='01a1490c-d8e7-7d01-9b40-acbb03942e2a',
    manifest=pin(manifest_path),application_eligible_order=[],independent_order=entries,
    toolchain={k:m[k] for k in ['recipe','tools','runtime','stdlib','external','environment','unset']},
    sequential_total_provisional_artifact_bytes=sum(e['inclusive_artifact_estimate_bytes'] for e in entries),
    native47_credit_effect=0,original419_credit_effect=0,grant_issued=False,
    exclusions=['D267 allocator','D289 typedArena/fixedspread','A333 compiler-body','all other rejected scopes','scene/compose retry or variant'],
    scope_limit='No whole test_ordered_json lowering, from_token search or renderer tests included. Primitive evidence alone cannot qualify those modules or metadata/reference/application/API gates.'))

# Independent host calculation checks literal oracles only; never invokes VKF.
values=[(0.0,0,False),(-0.0,0,False),(1.0,4607182418800017408,False),
    (-2.5,4612811918334230528,True),(1/10,4591870180066957722,False),
    (1+2**-52,4607182418800017409,False),(2**-1074,1,False),
    (2**-1022,4503599627370496,False),(2**-1022-2**-1074,4503599627370495,False),
    ((2-2**-52)*2.0**1023,9218868437227405311,False)]
for value,rank,negative in values:
    bits=struct.unpack('>Q',struct.pack('>d',value))[0]
    check('host IEEE literal oracle '+repr(value), (bits & ((1<<63)-1))==rank and (value<0)==negative)
check('host scaled int oracle',int((1+2**-52)*2**52)==4503599627370497)
check('host UTF8 byte positions', 'Aé😀'.encode()==b'A\xc3\xa9\xf0\x9f\x98\x80')
check('host Unicode scalar oracle',ord('é')==233 and ord('😀')==128512 and 'é'!='é')
for p in list(pins.values()):
    check('final input stable '+p['path'],pin(p['path'])['sha256']==p['sha256'])
write('input-pins.json',list(pins.values()))
write('checks.json',dict(checks_passed=len(checks),checks=checks,
    elapsed_seconds=time.monotonic()-started,source_commit=head,native_executions=0,
    historical_pin_mismatches=[p for p in history_checks if not p['matches']],
    owned_joins='Two synchronous git children waited; this Python process exits normally; no native/controller/service/background children.',
    limitations='Host calculations verify planned constants, not VKF parsing/lowering/execution. No native pass/failure inferred.'))
print(json.dumps(dict(checks=len(checks),historical_pin_mismatches=sum(not p['matches'] for p in history_checks),
    elapsed_seconds=time.monotonic()-started,partition=[18,10,1,18],independent_entries=len(entries))))
