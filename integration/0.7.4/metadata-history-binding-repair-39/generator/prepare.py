#!/usr/bin/env python3
"""Neutral incremental preparation. Native execution lives in payload.py, under future grants."""
import argparse, copy, hashlib, json, os, re, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode=True
from authenticate import HERE, REPO, REPAIR, CACHE, D, read, save, sha, pin, md
HELD='8ff80f95d154585cc0966cfb2b9b06ae441cb357017eb524c8b750616ae6161d'
BASELINE='6c9f9cf5d2b60c426f88402c0ae32c294191c26880614e71907354613e27c5bd'
TAG='compiler-build-preparation-03'
IMPORT=re.compile(r'^([A-Za-z_]\w*)\s*:\s*\.([A-Za-z_]\w*)\s*(?:#.*)?$',re.M)

def require(ok,reason):
    if not ok:raise ValueError(reason)
def verify(p):
    require(sha(p['path'])==p['sha256'],'changed/missing input '+p['path'])
def freeze_check(auth):
    require(not auth['failures'],'authentication failures')
    for p in auth['inputs']:verify(p)
def checked_copy(ref,dest):
    verify(ref);dest.parent.mkdir(parents=True,exist_ok=True)
    with Path(ref['path']).open('rb') as src,dest.open('xb') as out:
        while b:=src.read(262144):out.write(b)
    require(sha(dest)==ref['sha256'],'copy changed '+str(dest))
def current_head():
    return subprocess.check_output(['/usr/bin/git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()
def identity(parent,source_hashes,tag):
    # Exact D288 prepare.py algorithm: parent + ordered source hashes + iteration tag.
    return hashlib.sha256((parent+''.join(source_hashes)+tag).encode()).hexdigest()
def review(path):
    r=read(path);verify(r['candidate']);verify(r['regression'])
    require(r['baseline_sha256']==BASELINE,'wrong compiler baseline')
    require(r['changed_units']==[53],'only core53 is permitted')
    require(r['identity_tag']==TAG,'unexpected identity tag')
    # A future approval must explicitly exclude the rejected whole-record behavior.
    r['executable']=(r.get('accepted') is True and r['candidate']['sha256']!=HELD
                     and r.get('whole_record_projection_regression_reviewed') is True)
    return r

def maps(u):
    mapping={}
    for j,a in enumerate(u['argv']):
        if a=='-ivfsoverlay':
            v=read(u['argv'][j+1]);require(v['version']==0,'VFS version')
            for r in v['roots']:
                require(r['type']=='file','VFS directory unsupported')
                mapping[r['name']]=r['external-contents']
    # Same source-map composition recipe as D288, preserving original aliases.
    mapping.update({d['nominal']:d['effective'] for d in u['dependencies']})
    return mapping

def compile_command(u,out,vfs,source=None):
    cmd=[];skip=False
    for a in u['argv']:
        if skip:skip=False;continue
        if a=='-ivfsoverlay':skip=True;continue
        cmd.append(a)
    cmd[1:1]=['-ivfsoverlay',str(vfs)]
    cmd[cmd.index('-o')+1]=str(out)
    cmd[cmd.index('-MF')+1]=str(out)+'.d'
    if source:cmd[cmd.index('-c')+1]=str(source)
    return cmd

def link_command(original,out,replacements,driver=None):
    cmd=[]
    original_driver=next(a for a in original if a.endswith('.o'))
    for j,a in enumerate(original):
        if j and original[j-1]=='-o':a=str(out)
        elif a.startswith('--dependency-file='):a='--dependency-file='+str(out)+'.d'
        elif driver and a==original_driver:a=str(driver)
        else:a=str(replacements.get(a,a))
        cmd.append(a)
    return cmd

def build_plan(out,r,auth):
    require(out.is_absolute(),'absolute charged attempt required')
    require(not out.exists(),'fresh attempt only; no reuse')
    out.mkdir(parents=True)
    for name in ['tmp','cache','home','logs','objects','sources']: (out/name).mkdir()
    prereq=read(REPAIR/'build-prerequisites.json');d288=read(prereq['D288_profile']['path'])
    units={str(i):read(REPAIR/n) for i,n in [(53,'build-input-unit53.json'),(90,'build-input-identity90.json')]}
    checked_copy(r['candidate'],out/'sources/layouts_1.cpp')
    checked_copy(r['regression'],out/'sources/regression_layouts.cpp')
    new_id=identity(d288['identity'],[r['candidate']['sha256']],TAG)
    header=out/'sources/vkf_compiler_build_identity.generated.hpp'
    header.write_text('#pragma once\n#define VKF_COMPILER_BUILD_IDENTITY "'+new_id+'"\n')
    replacements={units['53']['dependencies'][0]['effective']:str(out/'sources/layouts_1.cpp')}
    old_header=next(d['effective'] for d in units['90']['dependencies'] if Path(d['effective']).name==header.name)
    replacements[old_header]=str(header)
    stages=[];expected={};mappings={}
    for key,u in units.items():
        mapping=maps(u)
        for name,effective in list(mapping.items()):
            if effective in replacements:mapping[name]=replacements[effective]
            if key=='90' and Path(name).name==header.name:mapping[name]=str(header)
        if key=='53':mapping[u['argv'][u['argv'].index('-c')+1]]=str(out/'sources/layouts_1.cpp')
        vfs=out/('vfs-'+key+'.json')
        # Keep all original aliases and include search flags. Only reviewed53 and identity header change.
        save(vfs,dict(version=0,roots=[{'type':'file','name':n,'external-contents':e} for n,e in sorted(mapping.items())]))
        mappings[key]=mapping
        expected[key]=[dict(nominal=d['nominal'],effective=replacements.get(d['effective'],d['effective']),sha256=sha(replacements.get(d['effective'],d['effective']))) for d in u['dependencies']]
        obj=out/('objects/core-'+key+'.o')
        stages.append(dict(name='compile-'+key,argv=compile_command(u,obj,vfs),timeout=180,md=str(obj)+'.d',md_mode='exact',expected=expected[key],mapping=mapping,outputs=[str(obj)]))
    object_replacements={units[k]['object']['path']:str(out/('objects/core-'+k+'.o')) for k in units}
    original=prereq['ordered_link_argv']
    allowed_link=[p for p in auth['inputs'] if 'implicit/actual link input' in p['roles']]
    link_expected=[dict(path=object_replacements.get(p['path'],p['path']),sha256=p['sha256'] if p['path'] not in object_replacements else None) for p in allowed_link]
    stages.append(dict(name='link-compiler',argv=link_command(original,out/'vkf-strict',object_replacements),timeout=180,md=str(out/'vkf-strict.d'),md_mode='link',expected=link_expected,outputs=[str(out/'vkf-strict')]))
    # Real C++ test compilation uses unit53's original headers, macros and search order.
    # Additional iostream is a known test-only dependency; anything else new stops.
    regression=out/'sources/regression_layouts.cpp';robj=out/'objects/regression.o'
    test_expected=[d for d in units['53']['dependencies'][1:]]+[
        dict(nominal=str(regression),effective=str(regression),sha256=sha(regression)),
        dict(nominal='/usr/include/c++/15/iostream',effective='/usr/include/c++/15/iostream',sha256=sha('/usr/include/c++/15/iostream'))]
    stages.append(dict(name='compile-regression',argv=compile_command(units['53'],robj,out/'vfs-53.json',regression),timeout=180,md=str(robj)+'.d',md_mode='subset',expected=test_expected,mapping=mappings['53'],outputs=[str(robj)]))
    driver=next(a for a in original if a.endswith('.o'))
    for kind,repl in [('baseline',{}),('candidate',object_replacements)]:
        expected_link=[dict(path=str(robj) if p['path']==driver else repl.get(p['path'],p['path']),sha256=None if p['path']==driver or p['path'] in repl else p['sha256']) for p in allowed_link]
        exe=out/('regression-'+kind)
        stages.append(dict(name='link-regression-'+kind,argv=link_command(original,exe,repl,robj),timeout=180,md=str(exe)+'.d',md_mode='link',expected=expected_link,outputs=[str(exe)]))
        stages.append(dict(name='run-regression-'+kind,argv=[str(exe)],timeout=30,expected_exit='nonzero' if kind=='baseline' else 0,stderr_contains=r['baseline_failure_marker'] if kind=='baseline' else None,stdout=None if kind=='baseline' else r['candidate_success_stdout'],outputs=[]))
    plan=dict(schema=1,kind='compiler',out=str(out),candidate_review=r,application_head_at_preparation=current_head(),identity=new_id,parent_identity=d288['identity'],identity_recipe=pin(D/'prepare.py'),units=units,stages=stages,inputs=auth['inputs'],executable=r['executable'],generated=[])
    plan['generated']=[pin(p) for p in sorted(out.rglob('*')) if p.is_file()]
    save(out/'plan.json',plan);return plan

def imports(text):
    for line in text.splitlines():
        if re.match(r'^\w+\s*:\s*\.',line):require(IMPORT.fullmatch(line) is not None,'unsupported import: '+line)
    return [m[2] for m in IMPORT.finditer(text)]

def entry(text):
    # Existing native-gates/prepare.py entry rules, scoped to F364 selected suites.
    if re.search(r'^main\(\):',text,re.M):return re.sub(r'^main\(\):','native_gate_main():',text,flags=re.M)+'\nnative_gate_main()\n'
    if re.search(r'^\(run\(\)\)\?!',text,re.M):return text
    if re.search(r'^(renderer_tests|tests)\(\)$',text,re.M):return re.sub(r'^(renderer_tests|tests)\(\)$',r'(\1())?! "Native gate entry returned false"',text,flags=re.M)
    raise ValueError('unknown current suite entry')

def closure(root_texts):
    source=REPO/'examples/gpu-math/native-vkf';texts=dict(root_texts);pins={};active=set()
    external={'io','math'}
    def visit(name):
        if name in external:return
        if name in active:return
        active.add(name)
        if name not in texts:
            path=source/(name+'.vkf');texts[name]=path.read_text();pins[name]=pin(path)
        for dep in imports(texts[name]):visit(dep)
    for name in list(texts):visit(name)
    return texts,pins

def tests_plan(out,r,auth,compiler_receipt,selection):
    require(not out.exists(),'fresh attempt only');out.mkdir(parents=True)
    for n in ['tmp','cache','home','logs']: (out/n).mkdir()
    head=current_head();recipe=read(CACHE/'Frontend/experiments/independent-worker-A/iteration347/recipe.json')
    verify(compiler_receipt['compiler']);require(compiler_receipt['candidate_sha256']==r['candidate']['sha256'],'wrong compiler candidate')
    require(compiler_receipt['native_build_passed'] is True,'compiler build not passed')
    require(compiler_receipt.get('core_regression_passed') is True,'core regression not passed')
    require(compiler_receipt.get('candidate_review')==r,'compiler regression review mismatch')
    expected_id=identity(read(read(REPAIR/'build-prerequisites.json')['D288_profile']['path'])['identity'],[r['candidate']['sha256']],TAG)
    require(compiler_receipt['identity']==expected_id,'compiler identity mismatch')
    normalizer=next(p for p in recipe['tools'] if Path(p['path']).name=='normalize_module_aliases.py')
    verify(normalizer)
    for p in recipe['stdlib']:
        verify(p);target=out/'home'/Path(p['path']).relative_to(recipe['environment']['VKF_HOME']);target.parent.mkdir(parents=True,exist_ok=True);target.symlink_to(p['path'])
    cases=[];source_pins={};stages=[]
    def case(name,root_texts,runs,entry_name=None,normalize=True):
        base=out/name;base.mkdir();raw=base/'raw';raw.mkdir()
        texts,pins=closure(root_texts);source_pins.update(pins)
        for n,t in sorted(texts.items()):(raw/(n+'.vkf')).write_text(t)
        assertions={n:t.count('?!') for n,t in texts.items()}
        entry_name=entry_name or name
        if normalize:
            stages.append(dict(name=name+'-normalize',argv=['/usr/bin/python3','-B',normalizer['path'],'--source-dir',str(raw),'--output-dir',str(base/'normalized')],timeout=30,outputs=[]))
            src=base/'normalized/source'/(entry_name+'.vkf')
        else:src=raw/(entry_name+'.vkf')
        exe=base/'case.exe'
        compile_argv=([compiler_receipt['compiler']['path'],'-b',str(src),'-o',str(exe),'--diagnostics'] if normalize else [compiler_receipt['compiler']['path'],str(src),'-o',str(exe)])
        stages.append(dict(name=name+'-compile',argv=compile_argv,cwd=str(base),timeout=1800 if name in ['A347','full-app','F364'] else 180,outputs=[str(exe)]))
        for i,run in enumerate(runs):
            run=copy.deepcopy(run);stdin=run.pop('stdin','')
            if 'report' in run:
                report=base/run['report'];stdin=stdin.replace('${REPORT}',str(report));run['report']=str(report)
            stdin_path=base/f'run-{i}.stdin';stdin_path.write_text(stdin)
            valgrind=run.pop('valgrind',False)
            cmd=(['/usr/bin/valgrind','--tool=memcheck','--leak-check=full','--show-leak-kinds=all','--errors-for-leak-kinds=definite,indirect','--error-exitcode=97'] if valgrind else [])+[str(exe)]
            stages.append(dict(name=name+'-run-'+str(i),argv=cmd,cwd=str(base),stdin=str(stdin_path),timeout=60,outputs=[],valgrind=valgrind,**run))
        cases.append(dict(name=name,modules=sorted(texts),assertions=assertions))
    if selection=='d288':
        for folder in [D,CACHE/'Proof/tests/independent-worker-D/iteration288-ownership02']:
            for c in read(folder/'plan.json')['cases']:
                case(c['name'],{c['name']:Path(c['source']).read_text()},[dict(stdin='0\n',expected_exit=0,stdout=c['oracle'],valgrind=True)],normalize=False)
    elif selection=='metadata':
        p=REPAIR/'regressions/metadata_actual_lengths.vkf'
        text=p.read_text()
        require(text.endswith('\ntrue\n'),'metadata final expression changed; review required')
        # Bare top-level values are discarded; emit the unchanged success value.
        case('metadata',{'metadata':text[:-5]+'::true\n'},[dict(expected_exit=0,stdout='true\n')])
    elif selection=='a345':
        p=next((REPAIR/'regressions').glob('*small*'));case('A345',{'A345':p.read_text()},[dict(expected_exit=0)])
    elif selection=='f364':
        f=CACHE/'Integrator/independent-worker-F/iteration364-scene-ten01';historical=read(f/'execution-plan.json')['suites'][0]
        roots={'02_scene_provider':Path(historical['derivative']['path']).read_text()}
        # Historical dispatcher unchanged; current suites regenerated, preserving every body/assertion.
        import importlib.util
        sp=importlib.util.spec_from_file_location('relocate',f/'prepare_group.py');module=importlib.util.module_from_spec(sp);sp.loader.exec_module(module)
        for run in historical['runs'][:-1]:
            name=run['id'];p=REPO/'examples/gpu-math/native-vkf'/(name+'.vkf');source_pins[name]=pin(p)
            wrapped=entry(p.read_text());relocated,calls=module.prepare(wrapped)
            require(relocated.count('?!')==wrapped.count('?!'),'assertion loss');roots[name]=relocated
        runs=[dict(stdin=Path(x['stdin']).read_text(),expected_exit=x['expected_exit'],stdout=x['expected_stdout'],stderr=x['expected_stderr']) for x in historical['runs']]
        case('F364',roots,runs,entry_name='02_scene_provider')
    elif selection=='a347':
        p=next((REPAIR/'regressions').glob('*real*'));base=CACHE/'Frontend/experiments/independent-worker-A/iteration347/attempt01';runs=[]
        for name in ['unowned','owned']:
            lines=(base/(name+'.stdin')).read_text().splitlines();require(len(lines)==5,'original A347 stdin shape')
            lines[4]='${REPORT}';runs.append(dict(stdin='\n'.join(lines)+'\n',expected_exit=0,report=name+'.report'))
        case('A347',{'A347':p.read_text()},runs)
    elif selection=='full-app':
        p=REPO/'examples/gpu-math/native-vkf/native_document_cli.vkf';source_pins['native_document_cli']=pin(p)
        case('full-app',{'native_document_cli':p.read_text()},[],entry_name='native_document_cli')
    else:raise ValueError('unknown selection')
    require(current_head()==head,'shared HEAD changed during materialization')
    for p in source_pins.values():verify(p)
    # The new closure is authenticated at each phase, never inherited from this packet's HEAD.
    plan=dict(schema=1,kind='vkf',selection=selection,out=str(out),candidate_review=r,compiler_receipt=compiler_receipt,executable=r['executable'],application_head_at_preparation=head,application_inputs=list(source_pins.values()),inputs=auth['inputs']+[compiler_receipt['compiler']],cases=cases,stages=stages,generated=[])
    plan['generated']=[pin(p) for p in sorted(out.rglob('*')) if p.is_file() and not p.is_symlink()]
    save(out/'plan.json',plan);return plan

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['compiler','vkf']);p.add_argument('--out',required=True,type=Path);p.add_argument('--candidate-review',type=Path,default=HERE/'candidate-held.json');p.add_argument('--compiler-receipt',type=Path);p.add_argument('--selection',choices=['d288','metadata','a345','f364','a347','full-app']);a=p.parse_args()
    auth=read(HERE/'authentication.json');freeze_check(auth);r=review(a.candidate_review)
    if a.action=='compiler':plan=build_plan(a.out.resolve(),r,auth)
    else:
        require(a.compiler_receipt and a.selection,'receipt and selection required');plan=tests_plan(a.out.resolve(),r,auth,read(a.compiler_receipt),a.selection)
    print(json.dumps(dict(plan=str(a.out/'plan.json'),executable=plan['executable'],stages=len(plan['stages']))))
if __name__=='__main__':main()
