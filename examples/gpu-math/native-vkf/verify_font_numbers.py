"""Compare every prepared-font numeric field by binary64 bits, using VKF JSON.

Python3.14 supplies an independent JSON reference. Native output uses integer
significand/exponent components to avoid ordinary print precision loss. Zero
sign is normalized by this adapter; no full-render/performance claim is made.
"""
import argparse
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

if sys.version_info[:2]!=(3,14):raise SystemExit('Python3.14 required')
p=argparse.ArgumentParser(description=__doc__)
for name in ['compiler','reference','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
root=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'componentOnly':True,'completeRendererPort':False,'performanceValidated':False,
        'zeroSignNormalized':True,'compilerSha256':sha(a.compiler),
        'sourceHashes':{p.name:sha(p)for p in root.glob('*.vkf')},'checks':[]}
bits=lambda v:struct.pack('<d',0.0 if v==0 else v)
try:
    binary=a.output/'resource_bits_audit'
    built=subprocess.run([a.compiler,'-b',root/'resource_bits_audit.vkf','-o',binary,'--diagnostics'],text=True,capture_output=True,timeout=120)
    (a.output/'build.json').write_text(built.stdout)
    assert built.returncode==0,built.stderr
    for profile in ['base','amsart-12']:
        for name in ['metrics.json','vector-index.json']:
            path=a.reference/profile/name;expected=[]
            def walk(node):
                count=1
                if isinstance(node,dict):
                    for value in node.values():count+=1+walk(value)
                elif isinstance(node,list):
                    for value in node:count+=walk(value)
                elif type(node)in(int,float):expected.append(float(node))
                return count
            nodes=walk(json.loads(path.read_text()));output=a.output/(profile+'-'+name+'.txt')
            with output.open('w')as handle:
                result=subprocess.run([binary],input=str(path)+'\n',text=True,stdout=handle,stderr=subprocess.PIPE,timeout=600)
            assert result.returncode==0,result.stderr
            lines=output.read_text().splitlines();actual=[]
            for line in lines[1:]:
                sig,exp=map(int,line.split(','));actual.append(math.ldexp(sig,exp))
            assert int(lines[0])==nodes and len(actual)==len(expected)
            errors=[{'index':i,'actual':x,'expected':y}for i,(x,y)in enumerate(zip(actual,expected))if bits(x)!=bits(y)]
            check={'profile':profile,'file':name,'sha256':sha(path),'nodes':nodes,'numericValues':len(expected),'differentBits':len(errors),'firstErrors':errors[:10]}
            report['checks'].append(check);print(json.dumps(check),flush=True)
            (a.output/'progress.json').write_text(json.dumps(report['checks'],indent=2)+'\n')
            assert not errors
    report.update(passed=True,numericValues=sum(c['numericValues']for c in report['checks']))
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
