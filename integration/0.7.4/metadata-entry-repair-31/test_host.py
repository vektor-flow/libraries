"""Sequential source preparation and exact-oracle regressions; no native commands."""
import ast, copy, difflib, importlib.util, json, os, resource, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
R=H.parents[2]
sys.path.insert(0,str(H.parent/'compiler-build-preparation-03'))
import prepare as baseline, payload
from investigate import A, M, N, pin, read, save, sha

def main():
    resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,)*2)
    resource.setrlimit(resource.RLIMIT_CPU,(50,50))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    start=time.monotonic();checks=[];children=[]
    def check(ok,name):
        assert ok,name
        checks.append(name)
    def run(argv):
        # Only known host tools below. Timeout kills/waits the single child;
        # normalizer and patch do not themselves launch children.
        t=time.monotonic()
        child=subprocess.Popen(argv,cwd=H,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                               env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        try: out,err=child.communicate(timeout=20)
        except BaseException:
            child.kill();child.communicate();raise
        children.append(dict(argv=argv,pid=child.pid,exit=child.returncode,
                             seconds=time.monotonic()-t,joined=True))
        assert child.returncode==0,(argv,err)
        return out
    spec=importlib.util.spec_from_file_location('candidate_prepare',H/'prepare.py')
    candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)
    receipt=read(N/'compiler-receipt.json');auth=read(H.parent/'compiler-build-preparation-03/authentication.json')
    review=baseline.review(H.parent/'compiler-native-binding-08/corrected-review.json')
    old_path=Path(baseline.__file__)
    # Actual patch application, restricted to an explicitly named own-output file.
    applied=H/'patch-reconstruction.py';applied.write_bytes(old_path.read_bytes())
    run(['/usr/bin/patch','--batch',str(applied),str(H/'prepare.py.patch')])
    check(applied.read_bytes()==(H/'prepare.py').read_bytes(),'unified patch reconstructs candidate exactly')
    old=baseline.tests_plan(H/'host-original',review,auth,receipt,'metadata')
    new=candidate.tests_plan(H/'host-candidate',review,auth,receipt,'metadata')
    # tests_plan uses synchronous check_output for HEAD only; those children are
    # waited by subprocess. No payload.execute or plan command is called here.
    def relocated(value,root):
        return json.loads(json.dumps(value).replace(str(root),'${OWN_TEST_ROOT}'))
    check(relocated(old['stages'],H/'host-original')==relocated(new['stages'],H/'host-candidate'),
          'all three stage argv/cwd/deadlines/stdin/exit/stdout oracles unchanged')
    check(old['cases']==new['cases'],'same three modules and all assertion counts')
    check(new['cases'][0]['assertions']['metadata']==6,'six original fixture assertions retained')
    check(new['stages'][-1]['stdout']=='true\n','exact five-byte success oracle retained')
    check(new['stages'][1]['argv'][1]=='-b','build-only flag retained')
    raw_before=H/'host-original/metadata/raw';raw_after=H/'host-candidate/metadata/raw'
    original=(raw_before/'metadata.vkf').read_bytes();changed=(raw_after/'metadata.vkf').read_bytes()
    check(changed==original[:-5]+b'::true\n','only change is two colons before final true')
    check(changed==(H/'metadata_actual_lengths.vkf').read_bytes(),'review fixture equals actual generator output')
    check(original==(M/'metadata/raw/metadata.vkf').read_bytes(),'baseline equals retained failed actual raw source')
    check([l for l in original.splitlines() if b'?!' in l]==[l for l in changed.splitlines() if b'?!' in l],
          'six assertions byte-identical in order')
    for name in ['scene_metadata.vkf','text_chunks.vkf']:
        check((raw_before/name).read_bytes()==(raw_after/name).read_bytes(),name+' production unchanged')
    for plan in [old,new]:
        s=plan['stages'][0]
        check(s['argv'][0:2]==['/usr/bin/python3','-B'],'normalizer is sole executed plan stage')
        out=run(s['argv']); label=Path(plan['out']).name
        (H/(label+'-normalize.stdout')).write_bytes(out)
    norm_before=H/'host-original/metadata/normalized/source'
    norm_after=H/'host-candidate/metadata/normalized/source'
    for name in ['metadata.vkf','scene_metadata.vkf','text_chunks.vkf']:
        b=(norm_before/name).read_bytes();a=(norm_after/name).read_bytes()
        check(b==(M/'metadata/normalized/source'/name).read_bytes(),name+' original normalization reproduces actual bytes')
        check(a==(b[:-5]+b'::true\n' if name=='metadata.vkf' else b),name+' normalized delta exact')
    check([l for l in (norm_after/'metadata.vkf').read_bytes().splitlines() if b'?!' in l]==
          [l for l in original.splitlines() if b'?!' in l],'normalization preserves all six exact assertions')
    for value in ['', 'true', 'false\n', 'true\n\n', ' true\n']:
        try:payload.check_result(new['stages'][-1],0,value,'')
        except ValueError:checks.append('existing oracle rejects '+repr(value))
        else:raise AssertionError('weakened stdout oracle')
    try:payload.check_result(new['stages'][-1],1,'true\n','')
    except ValueError:checks.append('existing oracle rejects nonzero even with correct stdout')
    else:raise AssertionError('weakened exit oracle')
    payload.check_result(new['stages'][-1],0,'true\n','')
    checks.append('existing oracle accepts only exact success in tested boundary cases')
    # Isolate the actual metadata branch for malformed-input rejection tests.
    def metadata_branch(source):
        tree=ast.parse(source)
        return next(n for n in ast.walk(tree) if isinstance(n,ast.If) and
            ast.unparse(n.test)=="selection == 'metadata'")
    old_tree=ast.parse(old_path.read_text());new_tree=ast.parse((H/'prepare.py').read_text())
    old_branch=metadata_branch(old_path.read_text());new_branch=metadata_branch((H/'prepare.py').read_text())
    def replace_branch(tree):
        for n in ast.walk(tree):
            if isinstance(n,ast.If) and ast.unparse(n.test)=="selection == 'metadata'":
                n.body=[ast.Pass()]
        return ast.dump(tree,include_attributes=False)
    check(replace_branch(old_tree)==replace_branch(new_tree),'every non-metadata branch/function unchanged, including four future phases')
    bad_root=H/'negative-inputs';(bad_root/'regressions').mkdir(parents=True)
    code=compile(ast.fix_missing_locations(ast.Module(body=new_branch.body,type_ignores=[])),'metadata-branch','exec')
    for tail in ['false\n','true','::true\n','true\n# moved tail\n']:
        (bad_root/'regressions/metadata_actual_lengths.vkf').write_text(original.decode()[:-5]+tail)
        captured=[]
        try:exec(code,dict(REPAIR=bad_root,require=baseline.require,case=lambda *a,**k:captured.append(a)))
        except ValueError:check(not captured,'changed fixture tail rejected before case generation: '+repr(tail))
        else:raise AssertionError('unreviewed tail accepted')
    # Successor is explicitly authorized by the root's steering message.
    head=run(['/usr/bin/git','-C',str(R),'rev-parse','HEAD']).decode().strip()
    check(head=='ec06152933f89bee0c25298744a100bdbb3da37a','authorized successor HEAD')
    initial='58b9edb2ea430610397fc606a5f496a9a5f75007'
    delta=run(['/usr/bin/git','-C',str(R),'diff','--name-status',initial,head]).decode().splitlines()
    check(all(l.startswith('A\t') for l in delta),'successor consists only of additions')
    protected=read(H/'input-pins.json')
    changed_names={l.split('\t')[-1] for l in delta}
    paths={str(Path(x['path']).relative_to(R)) for x in protected if Path(x['path']).is_relative_to(R)}
    check(not paths & changed_names,'successor additions do not intersect exact investigation input pins')
    for ref in protected:check(sha(ref['path'])==ref['sha256'],'posthash '+ref['path'])
    # Compare central tracked inputs directly with the originally granted commit.
    tracked=['integration/0.7.4/compiler-build-preparation-03/prepare.py',
             'integration/0.7.4/compiler-renderer-repair-02/regressions/metadata_actual_lengths.vkf',
             'examples/gpu-math/native-vkf/normalize_module_aliases.py',
             'examples/gpu-math/native-vkf/scene_metadata.vkf','examples/gpu-math/native-vkf/text_chunks.vkf']
    for rel in tracked:
        check(run(['/usr/bin/git','-C',str(R),'show',initial+':'+rel])==(R/rel).read_bytes(),
              'exact original HEAD bytes '+rel)
    save('successor.json',dict(original_head=initial,authorized_successor=head,delta=delta,
                              exact_tracked_inputs=tracked,all_evidence_pins_unchanged=True))
    report=dict(passed=True,checks=checks,seconds=time.monotonic()-start,children=children,
        synchronous_plan_git_children_joined=True,all_children_joined=True,overlap=0,
        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_max_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        address_space_limit_bytes=512*1024**2,outer_timeout_seconds=60,
        native_execution=False,normalizer_executions=2,compiler_or_executable_executions=0,
        memory=[l for l in Path('/proc/self/status').read_text().splitlines() if l.startswith(('VmHWM:','VmPeak:'))])
    save('host-results.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['checks','children'] }|{'checks':len(checks)}))
if __name__=='__main__':main()
