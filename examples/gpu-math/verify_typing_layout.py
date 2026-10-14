"""Fresh LaTeX checks for the independent interactive scripts/fraction subset."""
import argparse,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
CASES=['x^2','x_i','x_i^2',r'a^{n+1}',r'\frac{x}{y}',r'\frac{x^2+\alpha}{1+x_i}=y',r'\frac{a}{\frac{b}{c}}',r'\frac{a}{b}x']
def verify(root,output):
    if output.exists():raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True)
    module=(Path(__file__).parent/'typing-layout.mjs').resolve().as_uri()
    script=f"import{{readFileSync}}from'node:fs';import{{typeset}}from{json.dumps(module)};const data=JSON.parse(readFileSync({json.dumps(str(root/'typing-atlas/typing-data.json'))},'utf8'));console.log(JSON.stringify({json.dumps(CASES)}.map(s=>typeset(s,data.maps))));"
    boxes=json.loads(subprocess.check_output(['node','--input-type=module','-e',script],text=True));results=[]
    for i,(source,box) in enumerate(zip(CASES,boxes)):
        folder=output/str(i);folder.mkdir()
        (folder/'formula.tex').write_text(r'\documentclass{article}\usepackage{amsmath,amssymb}\pagestyle{empty}\begin{document}\noindent $\displaystyle '+source+r'$\end{document}')
        for cmd in [['latex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','formula.tex'],['dvisvgm','--no-fonts=0','--exact-bbox','--precision=8','--output=reference.svg','formula.dvi']]:
            r=subprocess.run(cmd,cwd=folder,capture_output=True,text=True,check=True);(folder/(cmd[0]+'.log')).write_text(r.stdout+r.stderr)
        svg=ET.parse(folder/'reference.svg').getroot();defs={e.attrib['id']:e for e in svg.iter() if 'id'in e.attrib}
        uses=[e for e in svg.iter() if e.tag.endswith('}use')];actual=[p for p in box['items'] if p['kind']=='glyph']
        assert len(uses)==len(actual),(source,len(uses),len(actual));errors=[]
        origin=[float(uses[0].attrib[k]) for k in ['x','y']];base=[actual[0]['x'],actual[0]['y']]
        for use,item in zip(uses,actual):
            style,token=item['key'].split('/',1);mapped=json.loads((root/f'typing-{style}/symbol-mapping.json').read_text())['symbols'][token]['outline']['svgPath']
            ref=defs[use.attrib['{http://www.w3.org/1999/xlink}href'][1:]].attrib['d']
            assert mapped==ref,(source,item['key'])
            errors.extend(abs(float(use.attrib[k])-origin[j]-(item[k]-base[j])) for j,k in enumerate(['x','y']))
        rects=[e for e in svg.iter() if e.tag.endswith('}rect')];rules=[p for p in box['items']if p['kind']=='rule'];assert len(rects)==len(rules)
        for rect,item in zip(sorted(rects,key=lambda r:float(r.attrib['y'])),sorted(rules,key=lambda r:r['y'])):
            errors.extend(abs(float(rect.attrib[k])-origin[j]-(item[k]-base[j])) for j,k in enumerate(['x','y']))
            errors.extend(abs(float(rect.attrib[k])-item[k]) for k in ['width','height'])
        max_error=max(errors);results.append({'source':source,'maxErrorUnits':max_error,'passed':max_error<.003})
    receipt={'cases':results,'passed':all(r['passed']for r in results),'scope':'Relative glyph/rule positions and outline identity; bounded standard display-math subset only.'}
    (output/'typing-layout-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
    if not receipt['passed']:raise SystemExit('Typing layout does not match oracle')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.root,a.output)
