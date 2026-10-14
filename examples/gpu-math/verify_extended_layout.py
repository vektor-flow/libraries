"""Independent whole-expression LaTeX checks, using positioned ink bounds and rules."""
import argparse,json,os,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
CASES=[r'x^{\int_0^1}',r'x^{\sum_i^n}',r'f(x)+y',r'f(x)^2',r'\int\limits_0^1',r'\sum\nolimits_i^n',r'x_i^2',r'\frac{x^2+\alpha}{1+x_i}=y',r'x^{2^{n+1}}',r'\sum_{x=0}^n x^2',r'\prod_{k=1}^n k',r'\int_0^1 f(x)\,dx',r'\oint_C f(x)\,dx',r'\Gamma+\Delta+\Theta+\Lambda+\Xi+\Pi+\Sigma+\Upsilon+\Phi+\Psi+\Omega',r'\left\langle\frac{1}{\left(1+x^2\right)}\right\rangle',r'\begin{pmatrix}a&b\\c&d\end{pmatrix}',r'\begin{bmatrix}x\\y\end{bmatrix}',r'f(x)=\begin{cases}x^2&x>0\\-x&x\leq0\end{cases}',r'\begin{aligned}x&=y\\z&=w\end{aligned}',r'\left\{\begin{matrix}x+y=1\\x-y=0\end{matrix}\right.']
def verify(root,atlas,output,mode):
    if output.exists():raise ValueError('Fresh output required')
    output.mkdir(parents=True);env=os.environ.copy();extras=root/'oracle-packages'
    for variable in ['TEXINPUTS','TFMFONTS','T1FONTS']:env[variable]=str(extras.resolve())+'//:'
    module=Path(__file__).with_name('typing-layout.mjs').resolve().as_uri()
    script=f"import{{readFileSync}}from'node:fs';import{{typeset}}from{json.dumps(module)};const data=JSON.parse(readFileSync({json.dumps(str(atlas/'typing-data.json'))},'utf8'));console.log(JSON.stringify({json.dumps(CASES)}.map(s=>typeset(s,data.maps,{{mode:{json.dumps(mode)}}}))));"
    boxes=json.loads(subprocess.check_output(['node','--input-type=module','-e',script],text=True));maps={s:json.loads((root/f'typing-{s}/symbol-mapping.json').read_text())for s in ['display','text','script','scriptscript']};results=[]
    for i,(source,box)in enumerate(zip(CASES,boxes)):
        folder=output/str(i);folder.mkdir();(folder/'formula.tex').write_text(r'\documentclass{article}\usepackage{amsmath,amssymb}\usepackage[nointlimits]{esint}\pagestyle{empty}\begin{document}\noindent\special{dvisvgm:raw <rect id="origin" x="{?x}" y="{?y}" width="0" height="0"/>}$'+('\\displaystyle 'if mode=='display'else'\\textstyle ')+source+r'$\end{document}')
        for cmd in [['latex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','formula.tex'],['dvisvgm','--fontmap=+'+str(extras/'esint.map'),'--no-fonts=0','--exact-bbox','--precision=8','--output=reference.svg','formula.dvi']]:subprocess.run(cmd,cwd=folder,env=env,capture_output=True,text=True,check=True)
        svg=ET.parse(folder/'reference.svg').getroot();defs={e.attrib['id']:e for e in svg.iter()if'id'in e.attrib};origin=defs['origin'];ox,oy=float(origin.attrib['x']),float(origin.attrib['y'])
        uses=[e for e in svg.iter()if e.tag.endswith('}use')];actual=[p for p in box['items']if p['kind']=='glyph'];errors=[]
        reference=[];independent=[]
        for use in uses:
            path=defs[use.attrib['{http://www.w3.org/1999/xlink}href'][1:]].attrib['d'];pen=BoundsPen(None);parse_path(path,pen)
            reference.append([v+float(use.attrib['x'if j%2==0 else'y'])-(ox if j%2==0 else oy)for j,v in enumerate(pen.bounds)])
        for item in actual:
            style,token=item['key'].split('/',1);pen=BoundsPen(None);parse_path(maps[style]['symbols'][token]['outline']['svgPath'],pen)
            independent.append([v+item['x'if j%2==0 else'y']for j,v in enumerate(pen.bounds)])
        # DVI draws stacked operator limits in a different traversal order.
        if len(reference)==len(independent):
            remaining=reference[:];pairs=[]
            for item,bounds in zip(actual,independent):
                candidate=min(remaining,key=lambda r:sum(abs(a-b)for a,b in zip(bounds,r)));remaining.remove(candidate)
                error=max(abs(a-b)for a,b in zip(bounds,candidate));errors.append(error)
                pairs.append({'key':item['key'],'actual':bounds,'reference':candidate,'error':error})
            (folder/'pairs.json').write_text(json.dumps(pairs,indent=2))
        else:errors=[999]
        rects=[e for e in svg.iter()if e.tag.endswith('}rect')and e.attrib.get('id')!='origin'];rules=[p for p in box['items']if p['kind']=='rule']
        if len(rects)!=len(rules):errors.append(999)
        for rect,item in zip(sorted(rects,key=lambda r:float(r.attrib['y'])),sorted(rules,key=lambda r:r['y'])):
            for k in ['x','y','width','height']:errors.append(abs(float(rect.attrib[k])-(ox if k=='x'else oy if k=='y'else 0)-item[k]))
        maximum=max(errors,default=0);results.append({'source':source,'maxInkOrRuleErrorBp':maximum,'glyphs':[len(uses),len(actual)],'passed':maximum<.01})
    receipt={'mode':mode,'cases':results,'passed':all(r['passed']for r in results),'scope':'Fresh real-LaTeX positioned glyph ink bounds and fraction rules; no raster or arbitrary-package equivalence.'};(output/'extended-layout-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
    if not receipt['passed']:raise SystemExit('Extended layout differs from LaTeX')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--atlas',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mode',choices=['inline','display'],default='display');a=p.parse_args();verify(a.root,a.atlas,a.output,a.mode)
