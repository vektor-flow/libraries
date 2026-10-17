"""Final read-only posthash; write review35 acceptance evidence only."""
import hashlib,json,os,resource,signal,subprocess,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_AS,(512*2**20,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(50,50))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('55s')))
signal.alarm(55)
O=Path(__file__).resolve().parent;H=O.parent/'metadata-repaired-binding-32';repo=O.parents[2]
start=time.monotonic()
def read(p):return json.loads(Path(p).read_bytes())
def pin(p):
    with Path(p).open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(path=str(p),sha256=d)
def save(name,value):
    with (O/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
children=[]
def git(*args):
    c=subprocess.Popen(['/usr/bin/git','-C',str(repo),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:out,err=c.communicate(timeout=5)
    except BaseException:
        c.kill();c.communicate();raise
    children.append(dict(pid=c.pid,argv=c.args,exit=c.returncode,joined=True,absent=not Path('/proc',str(c.pid)).exists()))
    assert c.returncode==0,err
    return out
grantpath=Path('/home/viktor/Projects/Vektor Flow/.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/metadata-binding-review-35-visible-chat-grant.json')
grant=read(grantpath)
assert grant['output_directory']==str(O) and grant['repository']==str(repo)
assert grant['native_execution'] is False and grant['operational_mutation'] is False
assert git('rev-parse','HEAD').decode().strip()==grant['source_commit']
assert git('diff','HEAD','--')==b''
inputs=read(O/'review-input-pins.json')
for ref in inputs:assert pin(ref['path'])==ref,ref['path']
delivery=read(H/'delivery.json')
for key in ('manifest','handoff','plan','recipe','result','source_contract'):assert pin(delivery[key]['path'])==delivery[key]
mask=Path('/run/user/1000/systemd/user/vkf-s0-synchronized-contexts.service')
assert os.readlink(mask)=='/dev/null'
runners=[read(O/(n+'-runner.json')) for n in ('tests','packet','independent','repair-proof','native-provenance','audit')]
assert all(x['passed'] and x['all_children_joined'] for x in runners)
allchildren=[c for r in runners for c in r['children']]+children
assert all(c['joined'] and c['absent'] and not Path('/proc',str(c['pid'])).exists() for c in allchildren)
assert not list(O.glob('TEST_ONLY_*'))
audit=read(O/'audit-result.json')
for ref in (audit['current_ledger'],audit['current_owners']):assert pin(ref['path'])==ref
save('grant.snapshot.json',grant)
save('final-posthash.json',dict(passed=True,verified_paths=len(inputs),children=children,all_children_joined=True,
    source_head=grant['source_commit'],tracked_diff_empty=True,packet_delivery=pin(H/'delivery.json'),
    ledger=audit['current_ledger'],owners=audit['current_owners'],dispatcher_mask=dict(path=str(mask),readlink='/dev/null'),
    seconds=time.monotonic()-start,memory=[s for s in Path('/proc/self/status').read_text().splitlines() if s.startswith(('VmPeak:','VmHWM:'))],
    native_execution=False,operational_actions=False,live_join_reauthentication=False))
result=dict(id='metadata-binding-review-35',owner=grant['owner_thread'],coordinator=grant['coordinator'],
    result='ACCEPT_EXACT_PINNED_PACKET_FOR_ROOT_ADMISSION_REVIEW',blockers=[],corrective_patch=None,
    grant=pin(grantpath),source_commit=grant['source_commit'],packet_delivery=pin(H/'delivery.json'),
    packet_artifact_manifest=delivery['manifest'],source_contract=delivery['source_contract'],plan=delivery['plan'],recipe=delivery['recipe'],
    scope='source-only independent final review; repaired native metadata remains unqualified',
    validation=dict(unit_tests=13,packet_checks=66,succession_oracle_checks=43,independent_audit_checks=audit['check_count'],
        independent_rehashed_paths=len(inputs),runtime_elf_edges=104,repair31_original_input_pins=841,native29_actual_artifacts=62,native17_actual_stages=8,
        stdlib_regular_single_link_copies=30,materialized_allocated_bytes=1204224,normalized_synthetic_retained_bytes=1257472),
    memory=dict(AS_limit_bytes=512*2**20,wall_limit_seconds=55,max_host_RSS_KiB=249452,max_host_VmPeak_KiB=269040,
        max_successful_runner_seconds=max(r['seconds'] for r in runners),recorded_host_children=len(allchildren),all_children_joined=True,
        task_overlap=0,peer_write_overlap=0,offload_by_task=0,live_RAM_observation='unlocked ledger active_rows zero; not admission'),
    latest_USED_predecessor=audit['latest_A'],minimum_future_iteration=33,
    charges=dict(A=24159510528,F=19821273088,failed_native29_retained=1073741824,tiny_attempts=12,tiny_bytes=50331648),
    D267_D289_excluded=True,dispatcher_hold_preserved=True,operational_grant=False,native_execution=False,
    operational_actions=0,live_locks=0,shared_or_peer_writes=0,commits=0,subagents=0,
    reviewer_checker_correction='One retained failed host check confused two A/F storage policies with seven loaded confinement profiles. Corrected only audit.py; packet unchanged. first-audit.* and first-audit-runner.json retained.',
    root_remaining=['independent actual Controller.verify_join immediately before succession','fresh decision/grant/owner with integer iteration >32',
        'current boot, seven loaded enforce profiles, owners/empty lanes/floors/high/dispatcher and installed guards',
        'existing in-lock rotation/publication/admission, empty-attempt ordering, and at most one separately authorized actual attempt',
        'terminal stage/oracle/allocation/descendant join verification and A high restoration'],
    duplicate_tiny_qualification_required=False,broader_gate_credit=False)
save('result.json',result)
handoff=f'''METADATA BINDING REVIEW35 — ACCEPT EXACT PINNED PACKET FOR ROOT ADMISSION REVIEW
2026-10-17. ID {grant['owner_thread']}; coordinator {grant['coordinator']}.
Exact grant: {grantpath}
Current HEAD {grant['source_commit']}; tracked source diff empty.

DECISION
No concrete source/packet blocker found. Accept only the exact binding32 delivery,
plan, source contract and artifact manifest pinned in result.json. This is no
operational grant and no repaired-native success claim. No corrective patch or
duplicate tiny qualification is required. Root owns admission and one actual attempt.

AUTHENTICATED IMPLEMENTATION AND EVIDENCE
Read inherited project instructions, repository STATUS/HANDOVER and coordinator
status. No repository AGENTS.md exists. The original shared-base handover describes
an older checkpoint; dated native17/D288 appendices and native29/repair31/binding32
handoffs govern this narrow current review; the exact review35 grant governs scope.
Read actual adapter/root_steps/build/seal/check implementations and source proofs,
not only reports. Verified all119 delivered artifact rows and1074 binding input
rows. Independently rehashed1542 unique paths and posthashed them again at closure.
Source seal 06b0ea3dd3c3ecbeea37bb4ddc6f969ef1cc86b9758f3b72d5d3a87a15d18710
Plan 49553ec2c6f775144656e4e4440f706ac0a010f1b158f840915ae24564241b87
Artifact manifest 987f2641ebfa74979a91ff52ba5abb1d68e2f23eb2a95a873ace6a13e378e9a4

Integrated prepare.py equals repair31's reviewed candidate; reverse-delta/patch
checks preserve all other generator bytes. Exact generated raw/normalized delta
is two colons before the final true. All six original assertions, bytes/order and
production modules are intact. ::true occurs once after all six. Exit0, empty stdin,
five-byte true-newline747275650a and unspecified stderr remain exact. Complete
three-stage fields match ACTUAL native29 after relocation, including home compile
cwd and30/180/60s deadlines. Full-plan tamper and malformed-tail controls reject.

Repair31 source proof re-executed read-only: actual AST/typed/machine artifacts,
62native29 artifacts,841original inputs and actual linked driver/core41/48/182/233
plus lexer232 provider evidence authenticate bare-value discard and explicit emit.
Native17's actual eight stages, argv/oracles/logs/dependencies/MDs and retained joins
rechecked without executing compiler or ELF. ELF52116e581d041836505756fcde17d504422429e410f0c84cb353409e121948d9
identity340d32d743bfcd6da076840963974462ed590852314ae483bbde5b4cc20c2e74 unchanged.
262static pins/732plan inputs/924canonical runtime inputs; all104ELF edges recomputed.
Runtime imports/cache pins and installed confinement inputs match the exact seal.

All30 stdlib sources materialize as regular single-link exact copies in OWN scratch;
staging symlinks are specifications, not runtime files. Actual Python normalization
preserves assertions and exact delta. Installed allocated() accepts1204224B tree,
1257472B with real normalization and SYNTHETIC compiler/run artifacts. No native tool
or synthetic artifact executed. Actual native17 driver resolves io/errors via home cwd.
Adapter is byte-identical to preparation27: bounded10s shared lock, validation inside
lock, local remaining outer timeout, complete plan equality and prior-ELF-only DATA
exception intact. Only own temporary test lock used; no live capacity lock acquired.

SUCCESSION AND ROOT BOUNDARY
Unlocked current ledger equals retained metadata29 terminal state exactly. Latest
USED row A:metadata-native29-01 sequence15 stagejoined; authenticated owner chain
and published owner/grant agree on01a14a3a-d0d8-7a10-a188-717e31a22e31.
Actual join4a1ed5938463632747f40aba82b60beca7af7de4d676ed7e96ab9b01ea55f002
matches ledger grant/manifest/custody/service/inner result; retained invocation and
independent terminal report agree. Native29 exit0/emptystdout remains oracle FAILURE.
No new live service/cgroup/Controller.verify_join performed; that belongs to root.
Actual root predicates reject staleD288/native17/wrongowner/wrongjoin/unjoined/
interveningrow/sameowner/failedindependentjoin and iteration<=32. Null decision
rejects before operational imports. Exact fresh owner plus integeriteration>32 is
required; installed rotate_owner revalidates latest priorjoin under capacity lock.
No arbitrary latest-row fallback. Existing publication and F-preservation guards
remain intact. No operational packet/root-inputs/grant/manifest issued by binding32.

VALIDATION / RESOURCE / OVERLAP
13tests+66packetchecks+43succession/oraclechecks and4031inventory/evidence checks pass.
Peak hostRSS249452KiB/VmPeak269040KiB, <=512MiB AS/55s per runner; successful runner
max{result['memory']['max_successful_runner_seconds']:.3f}s. {len(allchildren)}recorded host children joined/absent; other shell
inspection children synchronous and joined. All phases sequential; no task overlap,
offload, subagents, compiler/native/TeX/services/namespaces or operational actions.
Only review35 directory written. Expansion33/lexer-preparation34 untouched.
One reviewer check initially confused two storage policies with seven loaded enforce
profiles. Original source/log/runner retained as first-audit.*; corrected own check
only. Live seven-profile enforcement remains root preflight, no packet defect.

PRESERVED LIMITS / NEXT
Failednative29 permanent1GiB; A24159510528/F19821273088; tiny12/50331648B and earlier
failednative13/recovery history unchanged. Dispatcher mask still/dev/null; no service
action. D267/D289 excluded; no guard/cap/reset/refund changes or broadened gate credit.
Root reauthenticates actual join/boot/policies/owners/emptylanes/floors/high/dispatcher,
issues fresh authority and follows exact ROOT-RECIPE for existing guarded rotation,
publication and one actual attempt, stopping on first unexpected error.8GiB/1GiB/300s
remain proposals requiring root decision. No native47/original419/PDF/API/readers/
release/performance credit. Any source/HEAD/path drift requires fresh packet review.

Evidence: result.json, audit-result.json, final-posthash.json, review-input-pins.json,
replay.py/audit.py/finalize.py, raw logs, replay reports and runner child/memory records.
ONE DONE with this ID/result/HANDOFF, then stop.
'''
with (O/'HANDOFF.txt').open('x') as f:f.write(handoff)
save('artifact-pins.json',[pin(p) for p in sorted(O.iterdir()) if p.is_file() and p.name not in ('artifact-pins.json','finalize.stdout','finalize.stderr')])
print(json.dumps(dict(result=result['result'],id=grant['owner_thread'],children=len(allchildren),all_children_joined=True,seconds=time.monotonic()-start)))
