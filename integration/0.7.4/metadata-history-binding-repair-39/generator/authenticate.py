#!/usr/bin/env python3
"""Read-only authentication, streaming file hashes; no compiler/tool execution."""
import hashlib, json, os, shlex, struct, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
REPAIR=HERE.parents[1]/'compiler-renderer-repair-02'
CACHE=Path('/home/viktor/.cache/vkf-s0-runtimes-20261012')
D=CACHE/'Proof/tests/independent-worker-D/iteration288-record01'
F=CACHE/'Integrator/independent-worker-F/iteration303-compose01'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(262144),b''): h.update(b)
    return h.hexdigest()
def read(path):
    p=Path(path)
    if p.stat().st_size>4*1024*1024: raise ValueError('JSON exceeds bounded reader: '+str(p))
    return json.loads(p.read_text())
def save(path,obj): Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def pin(path): return dict(path=str(path),sha256=sha(path))
def md(path):
    # GNU linker adds phony rules after the first rule. Parse only that rule.
    s=Path(path).read_text().replace('\\\n',' ')
    rule=s.split('\n',1)[0]
    return shlex.split(rule.split(':',1)[1])
def elf_needs(path):
    with Path(path).open('rb') as f:
        h=f.read(64)
        if h[:4]!=b'\x7fELF': return [],None,[]
        if h[4:6]!=b'\x02\x01': raise ValueError('unsupported ELF '+str(path))
        off=struct.unpack_from('<Q',h,40)[0]; size,count,idx=struct.unpack_from('<HHH',h,58)
        f.seek(off); sections=[struct.unpack('<IIQQQQIIQQ',f.read(size)) for _ in range(count)]
        names=sections[idx]; f.seek(names[4]); ns=f.read(names[5])
        table={ns[s[0]:].split(b'\0',1)[0].decode():s for s in sections}
        def data(name):
            s=table[name];f.seek(s[4]);return f.read(s[5])
        interp=data('.interp').rstrip(b'\0').decode() if '.interp' in table else None
        if '.dynamic' not in table:return [],interp,[]
        strings=data('.dynstr'); needs=[];search=[]
        for tag,val in struct.iter_unpack('<qQ',data('.dynamic')):
            if tag in (1,15,29):
                text=strings[val:].split(b'\0',1)[0].decode()
                if tag==1:needs.append(text)
                else:search.extend(text.split(':'))
        return needs,interp,search

def main():
    start=time.monotonic(); rows={}; authorities={}; failures=[]
    def authority(path,h,origin):
        key=str(path);old=authorities.get(key)
        if old and old['sha256']!=h: raise ValueError('conflicting authority: '+key)
        authorities[key]=dict(sha256=h,origin=origin)
    def add(path,role,h=None,origin=None):
        path=str(path)
        if h: authority(path,h,origin)
        if path not in rows:
            try:
                s=Path(path).stat();actual=sha(path)
                rows[path]=dict(path=path,sha256=actual,bytes=s.st_size,roles=[role])
            except OSError as e:
                failures.append(dict(path=path,error=str(e)));return
        elif role not in rows[path]['roles']:rows[path]['roles'].append(role)
    prereq=read(REPAIR/'build-prerequisites.json')
    for key in ['unit53','D288_profile','D285_profile','F303_base_profile','source_VFS']:
        x=prereq[key];add(x['path'],'recipe authority',x['sha256'],str(REPAIR/'build-prerequisites.json'))
    # Compact historical pin maps only; no compiler-body/graph inspection.
    for source in [D/'manifest.json',D/'actual-link.json',D/'ordered-providers.json',D/'posthash.json',CACHE/'Proof/tests/independent-worker-D/iteration288-ownership02/manifest.json']:
        add(source,'historical pins')
        doc=read(source);items=doc['inputs'] if isinstance(doc,dict) else doc
        for x in items:
            if 'path' in x and 'sha256' in x:authority(x['path'],x['sha256'],str(source))
    for name in ['HANDOFF.txt','CAUSE.txt','QUALIFICATION.txt','root-review.json','compiler.patch','build-prerequisites.json','build-input-unit53.json','build-input-identity90.json','regression_layouts.cpp','candidate/layouts_1.cpp']:
        add(REPAIR/name,'reviewed packet')
    add(REPAIR/'candidate/layouts_1.cpp','reviewed candidate','8ff80f95d154585cc0966cfb2b9b06ae441cb357017eb524c8b750616ae6161d','reviewed repair02 HANDOFF')
    for name in ['prepare.py','run.py','plan.json','vfs-90.json','vkf_compiler_build_identity.generated.hpp']:
        add(D/name,'original identity/source-map recipe')
    units={}
    for index,name in [(53,'build-input-unit53.json'),(90,'build-input-identity90.json')]:
        u=read(REPAIR/name); units[str(index)]=u
        add(u['actual_MD']['path'],'original MD',u['actual_MD']['sha256'],str(REPAIR/name))
        actual=md(u['actual_MD']['path'])
        if actual != [d['nominal'] for d in u['dependencies']]:raise ValueError('MD list differs '+str(index))
        mapping={}
        for j,arg in enumerate(u['argv']):
            if arg=='-ivfsoverlay':
                vf=u['argv'][j+1]; add(vf,'original VFS')
                v=read(vf)
                for r in v['roots']:
                    if r['type']!='file':raise ValueError('unsupported VFS root')
                    mapping[os.path.normpath(r['name'])]=r['external-contents']
        for dep in u['dependencies']:
            mapped=mapping.get(os.path.normpath(dep['nominal']),dep['nominal'])
            if os.path.realpath(mapped)!=os.path.realpath(dep['effective']):raise ValueError('VFS/MD mismatch '+str(dep))
            add(dep['effective'],'effective dependency '+str(index),dep['sha256'],str(REPAIR/name))
        add(u['object']['path'],'replaced old provider',u['object']['sha256'],str(REPAIR/name))
    argv=prereq['ordered_link_argv']; ordered=[x for x in argv if x.endswith(('.o','.a'))]
    if len(ordered)!=240:raise ValueError('link count')
    for path in ordered:add(path,'ordered link input')
    for x in read(D/'actual-link.json'):add(x['path'],'implicit/actual link input',x['sha256'],str(D/'actual-link.json'))
    recipepath=CACHE/'Frontend/experiments/independent-worker-A/iteration347/recipe.json'
    recipe=read(recipepath);add(recipepath,'VKF recipe')
    for x in recipe['tools']+recipe['runtime']+recipe['stdlib']:add(x['path'],'VKF tool/runtime/stdlib',x['sha256'],str(recipepath))
    a347=CACHE/'Frontend/experiments/independent-worker-A/iteration347/attempt01'
    am=read(a347/'manifest.json');add(a347/'manifest.json','A347 asset authority')
    for x in am['inputs']:
        authority(x['path'],x['sha256'],str(a347/'manifest.json'))
    for case in ['owned','unowned']:
        add(a347/(case+'.stdin'),'A347 original stdin')
        for line in (a347/(case+'.stdin')).read_text().splitlines()[:2]:add(line,'A347 font/language asset')
    add('/usr/include/c++/15/iostream','test-only C++ dependency')
    f364=CACHE/'Integrator/independent-worker-F/iteration364-scene-ten01'
    add(f364/'execution-plan.json','F364 exact control recipe')
    add(f364/'prepare_group.py','F364 exact entry relocation')
    fp=read(f364/'execution-plan.json')['suites'][0]
    add(fp['derivative']['path'],'F364 dispatcher',fp['derivative']['sha256'],str(f364/'execution-plan.json'))
    for run in fp['runs']:add(run['stdin'],'F364 exact runtime stdin')
    for p in sorted((REPAIR/'regressions').glob('*.vkf')):add(p,'focused control')
    for base in [D,CACHE/'Proof/tests/independent-worker-D/iteration288-ownership02']:
        p=read(base/'plan.json');add(base/'plan.json','D288 control recipe')
        for case in p['cases']:add(case['source'],'D288 control source')
    for p in ['/usr/bin/clang++-19','/usr/bin/ld','/usr/bin/as','/usr/bin/valgrind','/usr/bin/valgrind.bin','/usr/libexec/valgrind/memcheck-amd64-linux','/usr/libexec/valgrind/vgpreload_core-amd64-linux.so','/usr/libexec/valgrind/vgpreload_memcheck-amd64-linux.so','/usr/bin/python3','/usr/bin/git']:
        add(p,'tool')
    queue=[Path(p) for p,r in rows.items() if any('tool' in role or 'runtime' in role for role in r['roles'])];seen=set();edges=[]
    while queue:
        path=queue.pop();real=str(path.resolve())
        if real in seen:continue
        seen.add(real)
        needs,interp,rpaths=elf_needs(path)
        if interp:add(interp,'ELF interpreter');queue.append(Path(interp))
        search=[Path(s.replace('$ORIGIN',str(path.resolve().parent))) for s in rpaths]+[Path('/usr/lib/x86_64-linux-gnu'),Path('/lib/x86_64-linux-gnu'),Path('/usr/lib/llvm-19/lib')]
        for name in needs:
            matches=[p/name for p in search if (p/name).is_file()]
            if not matches:raise ValueError('unresolved ELF dependency '+str(path)+' '+name)
            target=matches[0];add(target,'tool/runtime ELF dependency');queue.append(target);edges.append(dict(source=str(path),needed=name,target=str(target)))
    # Compare selected inputs to additional exact historical authorities. Never inspect unrelated bodies.
    artifact=REPAIR/'artifact-pins.json';add(artifact,'reviewed packet hash authority')
    for x in read(artifact):
        path=str(REPAIR/x['path'])
        if path in rows:authority(path,x['sha256'],str(artifact))
    fmanifest=f364/'manifest.json';add(fmanifest,'F364 input authority')
    for x in read(fmanifest)['inputs']:
        if x['path'] in rows:authority(x['path'],x['sha256'],str(fmanifest))
    original=CACHE/'Proof/tests/independent-worker-D/iteration69-A57-build03/manifest.json'
    add(original,'original unit53 input authority')
    for x in read(original)['inputs']:
        row=rows.get(x['path'])
        if row and ('effective dependency 53' in row['roles'] or 'original VFS' in row['roles']):
            authority(x['path'],x['sha256'],str(original))
    for p,r in rows.items():
        auth=authorities.get(p)
        r['authority']=auth or None;r['classification']='recorded-pin-match' if auth else 'observed-only'
        if auth and auth['sha256']!=r['sha256']:failures.append(dict(path=p,expected=auth['sha256'],actual=r['sha256']))
    result=dict(schema=1,preparation_only=True,hash_chunk_bytes=262144,inputs=list(rows.values()),failures=failures,ordered_link_inputs=ordered,elf_edges=edges,seconds=time.monotonic()-start)
    save(HERE/'authentication.json',result)
    print(json.dumps(dict(files=len(rows),bytes_streamed=sum(r['bytes'] for r in rows.values()),recorded=sum(r['authority'] is not None for r in rows.values()),failures=failures,seconds=result['seconds'])))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
