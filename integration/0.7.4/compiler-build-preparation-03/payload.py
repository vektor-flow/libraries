#!/usr/bin/env python3
"""Future guarded payload. Refuses held candidate; never creates operational admission."""
import argparse, importlib.util, json, os, resource, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
from authenticate import HERE, REPO, read, save, sha, pin, md
from prepare import require, verify, current_head, freeze_check, HELD

def canonical(path):return os.path.realpath(path)
def validate_md(stage,generated_pins):
    actual=md(stage['md']);expected=stage['expected'];mode=stage['md_mode'];mapping=stage.get('mapping',{})
    allowed={canonical(x.get('effective',x.get('path'))):x['sha256'] for x in expected}
    got={}
    for nominal in actual:
        effective=mapping.get(nominal,nominal);key=canonical(effective)
        require(key in allowed,'new dependency drift: '+nominal)
        digest=sha(effective);want=allowed[key] or generated_pins.get(key)
        require(want is not None and digest==want,'dependency bytes changed: '+effective)
        got[key]=digest
    if mode in ('exact','link'):require(set(got)==set(allowed),'missing expected MD dependencies')
    if mode=='subset':
        source=stage['argv'][stage['argv'].index('-c')+1]
        require(canonical(mapping.get(source,source)) in got,'missing regression source in MD')
    if mode=='link':
        # Every explicit provider must appear; implicit linker scripts may appear repeatedly.
        explicit={canonical(a) for a in stage['argv'] if a.endswith(('.o','.a'))}
        require(explicit<=set(got),'link omitted explicit provider')
    require(bool(got),'empty MD')
    return [dict(path=k,sha256=v) for k,v in sorted(got.items())]

def check_result(stage,code,stdout,stderr):
    wanted=stage.get('expected_exit',0)
    require(code!=0 if wanted=='nonzero' else code==wanted,'unexpected exit for '+stage['name']+': '+str(code))
    for key,actual in [('stdout',stdout),('stderr',stderr)]:
        if stage.get(key) is not None:require(actual==stage[key],key+' oracle mismatch: '+stage['name'])
    if stage.get('stderr_contains'):require(stage['stderr_contains'] in stderr,'baseline did not demonstrate specified defect')
    if stage.get('valgrind'):
        require('ERROR SUMMARY: 0 errors' in stderr and 'All heap blocks were freed' in stderr,'Valgrind ownership failure')
    if stage.get('report'):
        report=Path(stage['report']).read_text().split('\n',1)
        require(len(report)==2 and int(report[0])>0 and report[1]=='','A347 original count/diagnostics oracle failed')

def validate_admission(plan,admission,plan_pin):
    # Root-produced binding to an ACTUAL qualified external controller grant/receipt.
    # This schema is a payload binding, not a replacement for any operational grant.
    require(plan['executable'] is True,'candidate held: no execution')
    r=plan['candidate_review']
    require(r['accepted'] is True and r['candidate']['sha256']!=HELD and r.get('whole_record_projection_regression_reviewed') is True,'unaccepted candidate')
    verify(r['candidate']);verify(r['regression'])
    require(admission['coordinator']=='01a14893-cb1e-7203-97dd-de3da44dcf31','wrong coordinator')
    require(admission['plan']==plan_pin,'admission does not bind exact plan')
    require(admission['charged_attempt']==plan['out'],'wrong charged attempt')
    require(admission['native_execution'] is True and admission['environment_qualified'] is True,'native/environment not admitted')
    require(admission['phase']==plan.get('selection',plan['kind']),'wrong phase')
    for key in ['grant','controller_receipt','environment_qualification','candidate_review']:
        verify(admission[key])
    require(read(admission['candidate_review']['path'])['candidate']==r['candidate'],'candidate approval binding mismatch')
    require(read(admission['candidate_review']['path']).get('accepted') is True,'candidate approval held')
    require(admission['ram_bytes']>0 and admission['disk_bytes']>0 and admission['timeout_seconds']>0,'missing real budget')

def environment(out,plan):
    env={'PATH':'/home/viktor/.local/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1',
         'HOME':str(out/'home'),'TMPDIR':str(out/'tmp'),'TMP':str(out/'tmp'),'TEMP':str(out/'tmp'),
         'XDG_CACHE_HOME':str(out/'cache'),'CLANG_MODULE_CACHE_PATH':str(out/'cache/clang'),
         'VKF_HOME':str(out/'home')}
    runtimes=[p for p in plan['inputs'] if Path(p['path']).name=='libvkf-concurrent-runtime.so']
    require(len(runtimes)==1,'runtime binding ambiguous');env['LD_LIBRARY_PATH']=str(Path(runtimes[0]['path']).parent)
    return env

def execute(plan,admission,run_override=None):
    """run_override only used by host unit tests; no CLI substitution for native tools."""
    out=Path(plan['out']);results=[];generated_pins={};started=time.monotonic()
    require(not (out/'execution-started.json').exists(),'attempt already started: no automatic retry')
    require(current_head()==plan['application_head_at_preparation'],'stale application HEAD; regenerate closure in fresh attempt')
    freeze_check(dict(inputs=plan['inputs'],failures=[]))
    for p in plan.get('application_inputs',[])+plan['generated']:verify(p)
    # Reject accidental path escape before launching even one child.
    for s in plan['stages']:
        for path in s.get('outputs',[])+([s['md']] if 'md' in s else []):
            require(Path(path).is_relative_to(out) and Path(path).resolve().is_relative_to(out),'output escapes charged attempt')
    save(out/'execution-started.json',dict(native_execution=run_override is None,plan=pin(out/'plan.json')))
    owned=None
    if run_override is None:
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))  # Baseline aborts must not create external core dumps.
        p=next(p for p in plan['inputs'] if Path(p['path']).name=='owned-processes.py');verify(p)
        spec=importlib.util.spec_from_file_location('owned',p['path']);owned=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned);owned.enable_subreaper()
    env=environment(out,plan)
    def guard():
        require(time.monotonic()-started<admission['timeout_seconds'],'phase timeout')
        used=sum(p.lstat().st_blocks*512 for p in out.rglob('*'))+out.stat().st_blocks*512
        require(used<=admission['disk_bytes'],'inclusive charged-attempt disk estimate exceeded')
    error=None
    try:
        for s in plan['stages']:
            guard();t=time.monotonic();name=s['name'];log=out/'logs'/name
            if run_override is not None:
                code,stdout,stderr,join=run_override(s);Path(str(log)+'.stdout').write_text(stdout);Path(str(log)+'.stderr').write_text(stderr)
            else:
                with open(str(log)+'.stdout','xb') as stdout_file,open(str(log)+'.stderr','xb') as stderr_file:
                    stdin_file=open(s['stdin'],'rb') if s.get('stdin') else None
                    try:
                        child=subprocess.Popen(s['argv'],cwd=s.get('cwd',out),env=env,stdin=stdin_file if stdin_file else subprocess.DEVNULL,stdout=stdout_file,stderr=stderr_file,start_new_session=True)
                        code,join=owned.wait_owned(child,min(s['timeout'],max(1,admission['timeout_seconds']-(time.monotonic()-started))),guard=guard)
                    finally:
                        if stdin_file:stdin_file.close()
                require(Path(str(log)+'.stdout').stat().st_size<=8*1024*1024 and Path(str(log)+'.stderr').stat().st_size<=8*1024*1024,'oversized logs retained; stop')
                stdout=Path(str(log)+'.stdout').read_text(errors='replace');stderr=Path(str(log)+'.stderr').read_text(errors='replace')
            row=dict(name=name,argv=s['argv'],exit=code,join=join,seconds=time.monotonic()-t,usage=list(resource.getrusage(resource.RUSAGE_CHILDREN)))
            results.append(row);save(out/'results.json',results)
            require(join.get('no_live_descendants') is True and not join.get('timed_out') and not join.get('guard_error'),'child not cleanly joined')
            check_result(s,code,stdout,stderr)
            if 'md' in s:row['actual_dependencies']=validate_md(s,generated_pins)
            for path in s.get('outputs',[]):
                require(Path(path).is_file(),'missing expected output '+path);generated_pins[canonical(path)]=sha(path)
            save(out/'results.json',results)
        for p in plan.get('application_inputs',[])+plan['inputs']:verify(p)
        require(current_head()==plan['application_head_at_preparation'],'HEAD advanced during execution; closure result unqualified')
        guard()
        if plan['kind']=='compiler':
            # Must bind the emitted identity; use bounded streaming with overlap.
            marker=plan['identity'].encode();tail=b'';found=False
            with (out/'vkf-strict').open('rb') as f:
                while b:=f.read(262144):
                    found|=marker in tail+b;tail=b[-len(marker):]
            require(found,'rebuilt ELF lacks new identity')
            save(out/'compiler-receipt.json',dict(compiler=pin(out/'vkf-strict'),identity=plan['identity'],candidate_sha256=plan['candidate_review']['candidate']['sha256'],native_build_passed=run_override is None,core_regression_passed=run_override is None))
    except BaseException as exc:
        error=str(exc);raise
    finally:
        save(out/'execution-summary.json',dict(error=error,completed=len(results),planned=len(plan['stages']),native_execution=run_override is None,all_recorded_children_joined=all(r['join'].get('no_live_descendants') is True for r in results),seconds=time.monotonic()-started,release_qualified=False))

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True,type=Path);p.add_argument('--binding',required=True,type=Path);p.add_argument('--binding-sha256',required=True);a=p.parse_args()
    verify(dict(path=str(a.binding),sha256=a.binding_sha256));plan=read(a.plan);admission=read(a.binding)
    validate_admission(plan,admission,pin(a.plan));execute(plan,admission)
if __name__=='__main__':main()
