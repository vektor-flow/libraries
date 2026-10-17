#!/usr/bin/env python3
"""Bounded source/model checks. No compiler, native binary or shared writes."""
from pathlib import Path
from types import SimpleNamespace as Record
from functools import lru_cache
import difflib
import hashlib
import importlib.util
import io
import json
import math
import re
import struct
import subprocess
import sys
import time
import unittest
from vkf_model import translate

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SRC=ROOT/'examples/gpu-math/native-vkf'
BASE='b90d65bbe8df2ce3110288caf66816a6b150930b'
checks=[];pins={};start=time.monotonic()
def read(p):
    p=Path(p);data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest();return data.decode()
def check(label,ok):
    checks.append(dict(check=label,passed=bool(ok)))
    if not ok:raise AssertionError(label)
def write(name,data): (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def run(command):return subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=20)

# A separate exact-rational oracle: integer quotient/remainder rounding after
# binary exponent selection. It does not use candidate midpoint search, any
# project parser, float(token), a formatter or generic object-map equality.
def rational_key(token):
    match=re.fullmatch(r'(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?',token)
    sign,whole,fraction,exponent=match.groups();fraction=fraction or ''
    a=int(whole+fraction);power=int(exponent or '0')-len(fraction)
    if not a:return (0,False,True)
    b=1
    if power>=0:a*=10**power
    else:b=10**(-power)
    e=a.bit_length()-b.bit_length()
    if e>=0:
        if a<b<<e:e-=1
    elif a<<(-e)<b:e-=1
    p=max(e-52,-1074)
    if p>=0:b<<=p
    else:a<<=-p
    q,r=divmod(a,b)
    if 2*r>b or (2*r==b and q%2):q+=1
    if not q:return (0,False,True)
    if q>=2**53:q//=2;p+=1
    if p==-1074 and q<2**52:rank=q
    else:rank=(p+1075)*2**52+q-2**52
    if rank>0x7fefffffffffffff:return (0,False,False)
    return (rank,sign=='-',True)
def key_tuple(k):return (k.rank,k.negative,k.valid)
def bits_key(value):
    bits=struct.unpack('>Q',struct.pack('>d',value))[0]
    rank=bits&0x7fffffffffffffff
    return (rank,bool(bits>>63) and rank!=0,rank<=0x7fefffffffffffff)
def dyadic_text(m,p):
    # Used only to author exact midpoint inputs independently with Python ints.
    if p>=0:return str(m<<p)
    return str(m*5**(-p))+'e'+str(p)

class Pairs(list):pass
class Numeric(str):pass
def independent_metadata(raw):
    value=json.loads(raw,object_pairs_hook=Pairs,parse_float=Numeric,parse_int=Numeric)
    kinds=[];ends=[];texts=[];numbers=[]
    def emit(x):
        i=len(kinds);kind=0;text='';number=0.0
        if isinstance(x,Pairs):kind=1
        elif type(x) is list:kind=2
        elif isinstance(x,Numeric):
            kind=4;k=rational_key(x);assert k[2]
            number=struct.unpack('>d',struct.pack('>Q',k[0]|(int(k[1])<<63)))[0]
        elif type(x) is str:kind=3;text=x
        elif x is True:kind=5
        elif x is False:kind=6
        elif x is None:kind=7
        else:raise TypeError(x)
        kinds.append(kind);ends.append(0);texts.append(text);numbers.append(number)
        if kind==1:
            for key,val in x:emit(key);emit(val)
        if kind==2:
            for val in x:emit(val)
        ends[i]=len(kinds)
    emit(value)
    return Record(kinds=kinds,ends=ends,texts=texts,numbers=numbers,count=len(kinds))

head=run(['git','rev-parse','HEAD']).stdout.strip()
check('authorized base ancestry',run(['git','merge-base','--is-ancestor',BASE,head]).returncode==0)
check('all native VKF source unchanged since authorized base',not run(['git','diff','--name-only',BASE,'--',':(glob)examples/gpu-math/native-vkf/*.vkf']).stdout.strip())
# Pin all source, frozen files and literal test obligations, plus exact context.
for p in sorted(SRC.glob('*.vkf')):read(p)
for rel in ['HANDOVER.txt','COORDINATOR-STATUS.txt','metadata-contract-03/HANDOFF.txt','metadata-contract-03/CONTRACT.txt','metadata-contract-03/root-integration.json','reference-repair/provenance.json','native-gates/prepare.py','native-gates/test_prepare.py']:read(OUT.parent/rel)
read(ROOT.parent.parent/'.coordination/s0-plan-20261012/synchronized-contexts/independent-workers/storage20gb/serialization-boundary-04-visible-chat-grant.json')
read(ROOT/'examples/gpu-math/VKF_LATEX_RENDERING_HANDOVER.md')
for name in ['build.py','vkf_model.py','check.py']:read(OUT/name)
provenance=json.loads(read(OUT.parent/'reference-repair/provenance.json'))
for row in provenance['historical_sources']:
    original=read(row['path'])
    check('F303 original SHA256 '+Path(row['path']).name,pins[row['path']]==row['sha256'])
    renamed=re.sub(r'^(\w+:\.)(\w+)(\s*)$',lambda m:m[1]+'ref_f303_'+m[2]+m[3],original,flags=re.M)
    check('F303 byte-exact except authenticated import renaming '+Path(row['path']).name,renamed==read(SRC/('ref_f303_'+Path(row['path']).name)))
name='typed_packet_reference_harness_tests.vkf';before=read(SRC/name);after=read(OUT/'candidate'/name)
restored=after.replace('ordered_json:.test_ordered_json\n','').replace('ordered_json.metadata_matches(a.extras.(i),b.metadata,b.metadata_roots.(i))','extra_matches(a.extras.(i),b.metadata,b.metadata_roots.(i))').replace('ordered_json.json_matches(old_json,new_json)','(old_json=new_json)').replace('ordered_json.contract_tests()?! "Independent ordered JSON comparison contract"\n','')
check('harness changes exactly two differential predicates, import and new invocation',restored==before)
block=lambda s:s[s.index('extra_matches(original:'):s.index('fixture(case:int):')]
check('entire absence helper and all sixteen authored assertions byte-exact',block(before)==block(after))
assertions=[line for line in before.splitlines() if '?!' in line]
check('all other existing assertions byte-exact',all(line in after for line in assertions if '"column extras exact"' not in line and '"debug leaf export exact"' not in line))
literals=[line for line in before.splitlines() if '?! "actual JS' in line]
check('225 authored literal assertions byte-exact',len(literals)==225 and all(line in after for line in literals))
fixtures=[line for line in before.splitlines() if re.match(r'    index=\d\? values\.\(0\):',line)]
check('five captured fixtures byte-exact',len(fixtures)==5 and all(line in after for line in fixtures))
nsrc=read(OUT/'candidate/test_json_binary64.vkf');jsrc=read(OUT/'candidate/test_ordered_json.vkf')
check('numeric oracle has no module imports',not re.findall(r'^\w+:\.',nsrc,re.M))
check('tree reader imports only independent numeric oracle',re.findall(r'^\w+:\.(\w+)',jsrc,re.M)==['test_json_binary64'])
check('no production/frozen parser encoder decimal intrinsic or tolerance calls',not re.search(r'(resource_json|resource_numbers|binary_decimal|json_numbers|metadata_json|ref_f303_|vkf_decimal_parse|\.encode\(|\.roundtrip\(|1e-9)',nsrc+jsrc))
check('numeric max rank and midpoint coefficient fit signed int64',0x7fefffffffffffff<2**63 and 2*(2**53-1)+1<2**63)
n,ncode,_=translate(nsrc)
# Pure-function memoization accelerates only the host model. The function bodies
# remain translated from the candidate; no numeric implementation substitution.
n.from_token.__globals__['upper']=lru_cache(maxsize=8192)(n.from_token.__globals__['upper'])
j,jcode,labels=translate(jsrc,{'n':n})
(OUT/'numeric-model.py.txt').write_text(ncode);(OUT/'tree-model.py.txt').write_text(jcode)
check('43 candidate-authored boundary assertions execute in source-derived model',len(labels)==43 and j.contract_tests())
for label in labels:check('source-derived control: '+label,True)
print('43 candidate controls passed',flush=True)
# Exact ties on each parity side, huge/subnormal limits, and adjacent values.
tokens=['0','-0','2','2e0','0.1','0.10000000000000002','1.0000000000000002',
        '9007199254740993','-2.5','1e300','5e-324','2.2250738585072014e-308',
        '1.7976931348623157e308','1.8e308',dyadic_text(1,-1075),
        dyadic_text(2**53+1,-53),dyadic_text(2**53+3,-53)]
numeric=[]
for token in tokens:
    expected=rational_key(token);actual=key_tuple(n.from_token(token))
    check('exact-rational token '+token,actual==expected)
    numeric.append(dict(token=token,expected=expected,actual=actual))
    if expected[2]:
        value=struct.unpack('>d',struct.pack('>Q',expected[0]|(int(expected[1])<<63)))[0]
        check('typed binary64 extraction '+token,key_tuple(n.from_number(value))==bits_key(value))
print('17 exact rational conversions and 16 typed extractions passed',flush=True)
# Full presence/kind matrix plus both debug and direct metadata comparisons.
values=['null','{}','[]','""','false','0']
for a in values:
    for b in values:
        check('presence/kind debug '+a+'/'+b,j.json_matches(a,b)==(a==b))
        check('presence/kind typed '+a+'/'+b,j.metadata_matches(a,independent_metadata(b),0)==(a==b))
for raw in ['{"a":1,"a":2}','{"a":[],"b":[null]}','["é","😀","\\u0000"]','{"\\u0061":"x\\/y"}']:
    check('independent pair-preserving typed input '+raw,j.metadata_matches(raw,independent_metadata(raw),0))
invalid=['',' ','01','-','1.','1e','+1','NaN','Infinity','[1,]','{"a":1,}','{"a" 1}','true false','"\\x"','"\\ud800"','"\\udc00"','"\n"','[}', '{"a":}']
for raw in invalid:check('invalid JSON fails closed '+repr(raw),not j.json_matches(raw,raw))
# Mutations of candidate source itself, not merely weak stand-in predicates.
mutations={
    'ignore decoded text':('js',jsrc.replace('        kind=3 /\\ a.texts.(i)~=b.texts.(i)? @:false','        kind=3 /\\ false? @:false')),
    'ignore exact numeric keys':('ns',nsrc.replace('a.rank=b.rank','true')),
    'erase all presence guards':('js',jsrc.replace('root<0? @:original=""','root<0? @:true')),
    'ignore kind differences':('js',jsrc.replace('kind~=b.kinds.(i) \\/ ','false \\/ ')),
}
mutation_results={}
for label,(which,source) in mutations.items():
    badn=n
    if which=='ns':
        badn,_,_=translate(source)
        badn.from_token.__globals__['upper']=n.from_token.__globals__['upper']
    badj,_,_=translate(source if which=='js' else jsrc,{'n':badn})
    try:badj.contract_tests()
    except AssertionError as error:mutation_results[label]=str(error)
    else:raise AssertionError('Surviving mutation '+label)
    check('source mutation rejected: '+label,True)
# Existing six preparation tests, redirected to the grant directory for ALL
# TemporaryDirectory writes; -B prevents imports from writing bytecode elsewhere.
spec=importlib.util.spec_from_file_location('boundary_preparation',OUT.parent/'native-gates/test_prepare.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.HERE=OUT
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
(OUT/'preparation-tests.txt').write_text(stream.getvalue())
check('six preparation tests with grant-local temp directories',result.testsRun==6 and result.wasSuccessful())
patch=''
for p in sorted((OUT/'candidate').glob('*.vkf')):
    prior=read(SRC/p.name) if (SRC/p.name).exists() else ''
    patch+=''.join(difflib.unified_diff(prior.splitlines(True),read(p).splitlines(True),fromfile='a/examples/gpu-math/native-vkf/'+p.name if prior else '/dev/null',tofile='b/examples/gpu-math/native-vkf/'+p.name))
check('patch exactly equals three candidate files',read(OUT/'final.patch')==patch)
applied=run(['git','apply','--check',str(OUT/'final.patch')]);check('git apply --check only',applied.returncode==0)
check('all pinned inputs unchanged',all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items()))
write('input-pins.json',pins)
write('checks.json',dict(base=BASE,observed_head=head,checks=checks,passed=len(checks),native_assertions=len(labels),existing_assertions=len(assertions),literal_assertions=len(literals),fixtures=len(fixtures),numeric_vectors=numeric,source_mutations_detected=mutation_results,preparation_tests=result.testsRun,elapsed_seconds=time.monotonic()-start,native_execution=False,acceptance_ready=False,owned_jobs_joined=True,outstanding_children=0,git_apply_check_stderr=applied.stderr))
print(json.dumps(dict(passed=len(checks),preparation_tests=6,native_execution=False,acceptance_ready=False,elapsed_seconds=time.monotonic()-start)),flush=True)
