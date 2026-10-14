"""Check independent runtime symbol layout against fresh real-LaTeX fixtures."""
import argparse
import json
import subprocess
from pathlib import Path
from latex_paths import extract

CASES=['a+b=c',r'x+\alpha=\beta','-x+y','a(-b+c)','f+g=h',r'\Gamma+\Omega=2','a,b,c']

def verify(mapping,output):
    if output.exists():raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True)
    module=(Path(__file__).parent/'math-layout.mjs').resolve().as_uri()
    script=f"import {{layoutMath}} from {json.dumps(module)}; import {{readFileSync}} from 'node:fs'; const map=JSON.parse(readFileSync({json.dumps(str(mapping.resolve()))},'utf8')); console.log(JSON.stringify({json.dumps(CASES)}.map(s=>layoutMath(s,map))));"
    packets=json.loads(subprocess.check_output(['node','--input-type=module','-e',script],text=True))
    results=[]
    for index,(source,packet) in enumerate(zip(CASES,packets)):
        folder=output/str(index);folder.mkdir()
        (folder/'source.tex').write_text(r'\documentclass{article}\usepackage{amsmath,amssymb}\pagestyle{empty}\begin{document}\noindent $\displaystyle '+source+r'$\end{document}')
        for command in [['latex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','source.tex'],['dvisvgm','--no-fonts=0','--exact-bbox','--precision=8','--output=source.svg','source.dvi']]:
            proc=subprocess.run(command,cwd=folder,capture_output=True,text=True,check=True,timeout=30)
            (folder/(command[0]+'.log')).write_text(proc.stdout+proc.stderr)
        reference=extract((folder/'source.svg').read_text())
        assert len(reference['primitives'])==len(packet['primitives'])
        origin=reference['primitives'][0]['transform'][4:]
        runtime_origin=packet['primitives'][0]['transform'][4:]
        errors=[]
        for a,b in zip(reference['primitives'],packet['primitives']):
            assert a['outline']==b['outline'],source
            errors.append(max(abs((a['transform'][4+i]-origin[i])-(b['transform'][4+i]-runtime_origin[i])) for i in (0,1)))
        max_error=max(errors)
        results.append({'source':source,'positionMaxErrorUnits':max_error,'passed':max_error<.0003})
        (folder/'runtime-packet.json').write_text(json.dumps(packet,indent=2)+'\n')
    receipt={'cases':results,'passed':all(r['passed'] for r in results),'limits':['Ordinary atom subset only; not full TeX typesetting.','Relative glyph placements and outline identities checked; absolute baseline and raster fidelity not certified.']}
    (output/'mapping-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    if not receipt['passed']:raise ValueError('Runtime layout disagrees with oracle')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mapping',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();verify(a.mapping,a.output)
