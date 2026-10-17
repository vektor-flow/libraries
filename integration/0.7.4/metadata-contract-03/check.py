#!/usr/bin/env python3
"""Source checks and a bounded Python model; never executes VKF/native code.
Only writes receipts under this script's granted directory.
"""
from pathlib import Path
from types import SimpleNamespace
import difflib
import hashlib
import json
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SRC = ROOT / 'examples/gpu-math/native-vkf'
BASE = '84ebd6d761b61e544dd304859ac33fcd94064fa3'
pins = {}
checks = []
def read(path):
    path = Path(path)
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return data.decode()
def check(label, condition):
    checks.append({'check': label, 'passed': bool(condition)})
    if not condition:
        raise AssertionError(label)
def write(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def formatter(value):
    # Independent host model of the documented 17-significant-digit contract.
    # Not a translation/execution of the VKF formatter or parser.
    value = float(value)
    if value == 0:
        return '0'
    mantissa, exponent = format(value, '.16e').split('e')
    return mantissa.rstrip('0').rstrip('.')+'e'+str(int(exponent))
def encode(a, root):
    if root < 0:
        return '{}'
    kind = a.kinds[root]
    if kind == 1:
        parts = []
        at = root+1
        while at < a.ends[root]:
            parts.append(json.dumps(a.texts[at])+':'+encode(a, at+1))
            at = a.ends[at+1]
        return '{'+','.join(parts)+'}'
    if kind == 4:
        return formatter(a.numbers[root])
    if kind == 7:
        return 'null'
    raise AssertionError('Model only needs object/number/null for these authored records')
def model_function(body):
    # Translate only this helper's straight-line guards, not the VKF language.
    expressions=[]
    for line in body.splitlines():
        line=line.strip()
        if not line:
            continue
        if '? @:' in line:
            condition, value=line.split('? @:',1)
            expressions.append('    if '+pyexpr(condition)+': return '+pyexpr(value))
        elif line.startswith('@:'):
            expressions.append('    return '+pyexpr(line[2:]))
        else:
            raise AssertionError('Unexpected helper syntax: '+line)
    namespace={'metadata_json':SimpleNamespace(encode=encode)}
    exec('def extra_matches(original,metadata,root):\n'+'\n'.join(expressions), namespace)
    return namespace['extra_matches']
def pyexpr(text):
    # Do not rewrite punctuation inside string literals.
    tokens=re.split(r'("(?:\\.|[^"\\])*")',text)
    for i in range(0,len(tokens),2):
        tokens[i]=re.sub(r'(?<![<>=!])=(?!=)','==',tokens[i]).replace('false','False').replace('true','True').replace('~','not ')
    return ''.join(tokens).strip()
def contract_cases(block, fn):
    namespace={'extra_matches':fn, 'metadata_json':SimpleNamespace(encode=encode)}
    outcomes=[]
    for line in block.splitlines():
        if '?! ' in line:
            expr,label=line.strip().split('?! ',1)
            outcomes.append((json.loads(label), bool(eval(pyexpr(expr), {'__builtins__':{}},namespace))))
        elif re.match(r'    \w+:\(kinds:',line):
            name,record=line.strip().split(':',1)
            fields={}
            for key,value in re.findall(r'(\w+):(\[[^\]]*\]|document_scene.strings\(0\)|\d+)',record):
                if value=='document_scene.strings(0)': value='[]'
                if re.match(r'\[[\d.]+:0\]',value): value='[]'
                fields[key]=json.loads(value)
            namespace[name]=SimpleNamespace(**fields)
    return outcomes

def run():
    observed_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    check('authorized base is ancestor of observed HEAD',subprocess.run(['git','merge-base','--is-ancestor',BASE,observed_head],cwd=ROOT).returncode==0)
    check('metadata source directory unchanged since authorized base',not subprocess.check_output(['git','diff','--name-only',BASE,'--','examples/gpu-math/native-vkf'],cwd=ROOT,text=True).strip())
    name='typed_packet_reference_harness_tests.vkf'
    before=read(SRC/name); after=read(OUT/'candidate'/name)
    for rel in ['HANDOVER.txt','COORDINATOR-STATUS.txt','reference-review-02/HANDOFF.txt','reference-review-02/REVIEW.txt','reference-review-02/root-integration.json','native-gates/README.txt']:
        read(OUT.parent/rel)
    read(ROOT.parent.parent/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/metadata-contract-03-visible-chat-grant.json')
    for name2 in ['document_scene','document_scene_json','document_scene_paragraph_linear','paragraph_scene_legacy','paragraph_scene_store','paragraph_scene_export','scene_metadata','scene_metadata_json','resource_json','resource_numbers','json_numbers','document_scene_export','document_scene_export_tests','scene_metadata_regression_tests','scene_metadata_export_regression_tests','scene_metadata_edit_regression_tests','typed_packet_reference_adapter']:
        read(SRC/(name2+'.vkf'))
    for name2 in ['TYPED_OUTPUT_HANDOVER.txt','verify_json_numbers.py']:
        read(SRC/name2)
    read(ROOT/'examples/gpu-math/VKF_LATEX_RENDERING_HANDOVER.md')
    read(OUT.parent/'reference-repair/PROPOSAL.txt')
    provenance=json.loads(read(OUT.parent/'reference-repair/provenance.json'))
    frozen={}
    for row in provenance['historical_sources']:
        original=read(row['path'])
        check('F303 original pin '+Path(row['path']).name,pins[row['path']]==row['sha256'])
        target='ref_f303_'+Path(row['path']).name
        frozen[target]=read(SRC/target)
        renamed=re.sub(r'^(\w+:\.)(\w+)(\s*)$',lambda m:m[1]+'ref_f303_'+m[2]+m[3],original,flags=re.M)
        check('F303 unchanged except import aliases '+target,frozen[target]==renamed)
    check('reference imports remain independent',all(dep+'.vkf' in frozen for text in frozen.values() for dep in re.findall(r'^\w+:\.(\w+)\s*$',text,re.M)))
    addition=after[after.index('# Test-only comparison'):after.index('fixture(case:int):')]
    old_predicate='(a.extras.(i)=metadata_json.encode(b.metadata,b.metadata_roots.(i)))?! "column extras exact"'
    new_predicate='extra_matches(a.extras.(i),b.metadata,b.metadata_roots.(i))?! "column extras exact"'
    restored=after.replace(addition,'').replace(new_predicate,old_predicate).replace('extra_contract_tests()?! "Metadata absence boundary contract"\n','')
    check('only declared helper, tests, one operand boundary and invocation changed',restored==before)
    originals=[s for s in before.splitlines() if '?!' in s]
    check('all existing predicates preserved except one declared boundary',all(s in after or s.strip()==old_predicate for s in originals))
    literals=[s for s in before.splitlines() if '?! "actual JS' in s]
    check('225 authored literal assertions byte-exact',len(literals)==225 and all(s in after for s in literals))
    fixtures=[s for s in before.splitlines() if re.match(r'    index=\d\? values\.\(0\):',s)]
    check('five captured fixtures byte-exact',len(fixtures)==5 and all(s in after for s in fixtures))
    check('strict export equality retained','(old_json=new_json)?! "debug leaf export exact"' in after)
    check('new checks execute before blocked renderer path',after.index('extra_contract_tests()?!')<after.index('\nrenderer_tests()\n'))
    helper=after.split('extra_matches(original:str,metadata:Metadata,root:int)->bit:\n')[1].split('extra_contract_tests()->bit:')[0]
    check('present-value strict equality retained','@:original=metadata_json.encode(metadata,root)' in helper)
    block=after.split('extra_contract_tests()->bit:\n')[1].split('fixture(case:int):')[0]
    cases=contract_cases(block,model_function(helper))
    check('sixteen source-authored boundary cases',len(cases)==16)
    for label,passed in cases: check('Python source-derived helper model: '+label,passed)
    mutations={
        'restore buggy encode-only comparison':'    @:original=metadata_json.encode(metadata,root)\n',
        'collapse root zero into absence':helper.replace('root<0','root<=0'),
        'accept any absent-root text':helper.replace('root<0? @:original=""','root<0? @:true'),
        'ignore present values':helper.replace('@:original=metadata_json.encode(metadata,root)','@:true'),
    }
    mutation_results={}
    for label,body in mutations.items():
        rejected=[case for case,ok in contract_cases(block,model_function(body)) if not ok]
        mutation_results[label]=rejected
        check('negative mutation detected: '+label,bool(rejected))
    # Raw item spans are retained separately from decoded/model-encoded values.
    mismatches=[]; items=0; decoder=json.JSONDecoder()
    for literal in re.findall(r'"(?:\\.|[^"\\])*"',before):
        text=json.loads(literal)
        match=re.search(r'"items"\s*:\s*\[',text)
        if not match: continue
        pos=match.end()
        while pos<len(text) and text[pos]!=']':
            while text[pos] in ' \t\r\n,': pos+=1
            if text[pos]==']': break
            item,end=decoder.raw_decode(text,pos)
            raw=text[pos:end]; items+=1
            numeric=[]
            def scan(value,path):
                if isinstance(value,dict):
                    for key,entry in value.items(): scan(entry,path+'/'+key)
                elif isinstance(value,list):
                    for index,entry in enumerate(value): scan(entry,path+'/'+str(index))
                elif type(value) in (int,float) and value!=0:
                    numeric.append({'path':path,'decoded':value,'model_encoded':formatter(value)})
            scan(item,'')
            if numeric:
                mismatches.append({'item_index':items-1,'raw':raw,'numeric_values':numeric})
            pos=end
    check('nonempty raw-number hazard actually in retained fixtures',items>0 and bool(mismatches))
    check('concrete exact integer formatter witness',formatter(2)=='2e0')
    patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/examples/gpu-math/native-vkf/'+name,tofile='b/examples/gpu-math/native-vkf/'+name))
    check('patch exactly matches candidate',read(OUT/'final.patch')==patch)
    applied=subprocess.run(['git','apply','--check',str(OUT/'final.patch')],cwd=ROOT,text=True,capture_output=True)
    check('git apply --check only',applied.returncode==0)
    check('all pinned inputs unchanged',all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha for path,sha in pins.items()))
    write('input-pins.json',pins)
    write('checks.json',{'base':BASE,'observed_head':observed_head,'native_execution':False,'acceptance_ready':False,'checks':checks,'existing_assertions':len(originals),'literal_assertions':len(literals),'fixtures':len(fixtures),'model_cases':len(cases),'mutation_failures':mutation_results,'frozen_modules':len(frozen),'owned_jobs_joined':True,'outstanding_children':0,'git_apply_check_stderr':applied.stderr})
    write('nonempty-audit.json',{'evidence':'Python decoding/format model plus pinned source analysis, not VKF execution','items_inspected':items,'items_with_nonzero_numbers':len(mismatches),'first_item':mismatches[0],'formatter_witness':{'raw':'2','typed_model':'2e0','numeric_equal':True,'byte_equal':False},'strict_nonempty_and_export_assertions_retained':True,'all_items_with_numeric_values':mismatches})
    print(json.dumps({'source_and_model_checks_passed':len(checks),'model_cases':len(cases),'frozen_modules':len(frozen),'retained_items_inspected':items,'nonempty_numeric_hazards':len(mismatches),'native_execution':False,'acceptance_ready':False}))
if __name__=='__main__': run()
