"""Read retained evidence only; never loads or executes a native artifact."""
import collections, hashlib, json, resource, time
from pathlib import Path

H = Path(__file__).resolve().parent
R = H.parents[2]
C = Path('/home/viktor/.cache/vkf-s0-runtimes-20261012')
A = Path('/mnt/development/CompilerOptimization/owner-01a14893-cb1e-7203-97dd-de3da44dcf31/A/direct-v2-20261017')
M = A/'metadata-native29-01/metadata'
N = A/'compiler-native17-01/compiler'
pins = {}
def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
def pin(p):
    p = Path(p).resolve(); ref = dict(path=str(p), sha256=sha(p))
    pins[str(p)] = ref
    return ref
def read(p):
    pin(p)
    return json.loads(Path(p).read_text())
def verify(ref):
    assert pin(ref['path'])['sha256'] == ref['sha256'], ref['path']
def save(name, value):
    (H/name).write_text(json.dumps(value, indent=2)+'\n')
def main():
    resource.setrlimit(resource.RLIMIT_AS, (512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CPU, (50,50))
    resource.setrlimit(resource.RLIMIT_CORE, (0,0))
    started = time.monotonic()
    historical = read(H.parent/'metadata-native-29/attempt-artifact-pins.json')
    for ref in historical: verify(ref)
    receipt = read(N/'compiler-receipt.json')
    for key in ['compiler','plan','results']: verify(receipt[key])
    assert receipt['compiler']['sha256'] == '52116e581d041836505756fcde17d504422429e410f0c84cb353409e121948d9'
    assert receipt['identity'] == '340d32d743bfcd6da076840963974462ed590852314ae483bbde5b4cc20c2e74'
    native_results = read(N/'results.json')
    native_plan = read(N/'plan.json')
    assert native_results[2]['name'] == 'link-compiler'
    assert native_results[2]['argv'] == native_plan['stages'][2]['argv']
    for ref in native_results[2]['actual_dependencies']: verify(ref)
    driver_info = read(H.parent/'metadata-control-preparation-27/packet-verification.json')['driver']
    verify(driver_info['profile'])
    profile = read(driver_info['profile']['path'])
    units = [next(x for x in profile['drivers'] if x['label']=='driver-0')]
    units += [x for x in profile['objects'] if x['index'] in [41,48,182,233]]
    provenance = []
    sources = {}
    for u in units:
        assert u['object'] in native_results[2]['actual_dependencies']
        verify(u['object']); verify(u['actual_MD'])
        for dep in u['dependencies']:
            verify(dict(path=dep['effective'],sha256=dep['sha256']))
        source = u['dependencies'][0]
        key = str(u.get('index', 'driver'))
        sources[key] = Path(source['effective']).read_text()
        provenance.append(dict(unit=key, object=u['object'], MD=u['actual_MD'],
                               source=pin(source['effective']), dependencies=len(u['dependencies']),
                               actual_native17_link_match=True, argv=u.get('argv')))
    driver = sources['None'] if 'None' in sources else sources['driver']
    assert 'if (build_only) args.run = false;' in driver
    assert 'if (ran_program) parsed_args.run = false;' in driver
    assert 'node("emit")' in sources['233']
    assert 'if (kind == "emit")' in sources['182']
    assert 'stdlib_function("io", "print")' in sources['182']
    assert 'function_tail && index + 1 == body.size()' in sources['41']
    assert 'builder.emit({Opcode::Drop});' in sources['41']
    assert 'lower_statements(single_statement, entry, false, signatures, strings);' in sources['48']
    assert 'OutputKind output_kind = OutputKind::None;' in sources['48']
    assert 'output_tokens.push_back({OutputTokenKind::Text, "\\n"});' in sources['48']
    excerpts = []
    for key, ranges in {'None':[(3633,3642),(3692,3706),(4826,4855)],
                        'driver':[(3633,3642),(3692,3706),(4826,4855)],
                        '233':[(733,749)], '182':[(35,56),(80,87)],
                        '41':[(176,224)], '48':[(750,763),(1047,1097),(1123,1150)]}.items():
        if key not in sources: continue
        source = next(x['source'] for x in provenance if x['unit']==key)
        for lo,hi in ranges:
            excerpts.append(dict(source=source,first_line=lo,last_line=hi,
                                 text='\n'.join(sources[key].splitlines()[lo-1:hi])))
    plan = read(M/'plan.json'); results = read(M/'results.json')
    for stage,row in zip(plan['stages'],results):
        assert stage['argv']==row['argv'] and stage['name']==row['name']
    assert plan['stages'][-1]['stdout'] == 'true\n'
    assert (M/'logs/metadata-run-0.stdout').read_bytes() == b''
    assert (M/'logs/metadata-run-0.stderr').read_bytes() == b''
    original = R/'integration/0.7.4/compiler-renderer-repair-02/regressions/metadata_actual_lengths.vkf'
    raw = M/'metadata/raw/metadata.vkf'; normalized = M/'metadata/normalized/source/metadata.vkf'
    assert original.read_bytes()==raw.read_bytes()
    for p in [original,raw,normalized,R/'examples/gpu-math/native-vkf/normalize_module_aliases.py']:
        pin(p)
    for name in ['scene_metadata','text_chunks']:
        p=R/f'examples/gpu-math/native-vkf/{name}.vkf'; pin(p)
        assert p.read_bytes()==(M/f'metadata/raw/{name}.vkf').read_bytes()
    assertions = [line for line in raw.read_text().splitlines() if '?!' in line]
    assert len(assertions)==6
    assert assertions == [line for line in normalized.read_text().splitlines() if '?!' in line]
    ir = M/'metadata/normalized/source/.vkfbuild/metadata'
    ast = read(ir/'ast.json'); typed = read(ir/'typed-ir.json'); machine = read(ir/'machine-ir.json')
    manifest = read(ir/'x64-manifest.json'); diagnostics = read(M/'logs/metadata-compile.stdout')
    assert ast['body'][-1]['kind']=='bool_literal' and ast['body'][-1]['value'] is True
    assert sum(x['kind']=='assert_expr' for x in ast['body'])==6
    assert typed['body'][16]['expr']['value'] is True
    assert typed['body'][16]['expr']['type']=='bit'
    assert all(x['kind']=='function' for x in typed['body'][17:])
    assert machine['output_kind']=='none' and machine['output_count']==0
    assert machine['outputs']==machine['output_tokens']==[]
    instructions=machine['entry']['instructions']
    assert instructions[-1]==dict(kind='return_values',result_count=0)
    assert manifest['result_transport']=='none' and manifest['output_count']==0
    assert diagnostics['status']=='compiled' and diagnostics['artifact_fallback'] is False
    dplan=read(A/'d288-native24-01/d288/plan.json')
    dresults=read(A/'d288-native24-01/d288/results.json')
    comparisons=[]
    for stage,row in zip(dplan['stages'],dresults):
        assert stage['argv']==row['argv']
        if stage['name'].endswith('-compile'):
            source=Path(stage['argv'][1]);pin(source)
            assert '-b' not in stage['argv'] and '::' in source.read_text()
            comparisons.append(dict(name=stage['name'],argv=stage['argv'],source=pin(source),
                                    emit_lines=[l for l in source.read_text().splitlines() if l.startswith('::')]))
        else:
            assert stage['stdout']=='true\n' and row['exit']==0
            for ref in row['logs']: verify(ref)
            assert Path(row['logs'][0]['path']).read_bytes()==b'true\n'
    state=read(H.parent/'metadata-native-29/final-state.json')
    latest=state['phases']['A:metadata-native29-01']
    assert latest['sequence']==15 and latest['stage']=='joined' and latest['phase_bytes']==1073741824
    verify(latest['join'])
    future={}
    for phase in ['a345','f364','a347','full-app']:
        p=H.parent/f'compiler-controls-preparation-18/staging/{phase}/plan.json';d=read(p)
        future[phase]=dict(plan=pin(p),stages=[{k:v for k,v in s.items() if k in
            ['name','argv','expected_exit','stdout','stderr','report','timeout']} for s in d['stages']])
    save('source-proof.json',dict(passed=True,seconds=time.monotonic()-started,
        historical_attempt_pins_verified=len(historical),native17=receipt['compiler'],identity=receipt['identity'],
        linked_source_provenance=provenance,source_excerpts=excerpts,
        original_assertions=assertions,actual_ast_tail=ast['body'][-1],actual_typed_tail=typed['body'][16],
        typed_following_functions=[x['name'] for x in typed['body'][17:]],
        machine_summary={k:machine[k] for k in ['output_kind','output_count','output_tokens','outputs']},
        machine_instruction_counts=dict(collections.Counter(x['kind'] for x in instructions)),
        actual_compile_diagnostics=diagnostics,actual_stages=plan['stages'],D288=comparisons,future_plans=future,
        latest_A={k:latest[k] for k in ['owner','sequence','stage','join','phase_bytes']},
        memory=[l for l in Path('/proc/self/status').read_text().splitlines() if l.startswith(('VmHWM:','VmPeak:'))],
        native_execution=False,children=[],overlap=0))
    save('input-pins.json',list(pins.values()))
    print(json.dumps(dict(passed=True,pins=len(pins),seconds=time.monotonic()-started,
                         max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))
if __name__=='__main__': main()
