"""Check same-family prose glyph placement against a fresh native LaTeX line."""
import argparse,json,subprocess,os,xml.etree.ElementTree as ET
from pathlib import Path
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
SOURCES=['Office affinity afflict AVATAR.','This is regular Computer Modern text.','Swedish letters: å ä ö Å Ä Ö.']
def verify(root,atlas,output):
 output.mkdir();module=Path(__file__).with_name('text-flow.mjs').resolve().as_uri();data=json.loads((atlas/'typing-data.json').read_text());env=os.environ.copy();extras=root/'oracle-packages'
 for variable in ['TEXINPUTS','TFMFONTS','TEXFONTS','T1FONTS']:env[variable]=str(extras.resolve())+'//:'
 script=f"import{{readFileSync}}from'node:fs';import{{typesetText}}from{json.dumps(module)};const{{maps}}=JSON.parse(readFileSync({json.dumps(str(atlas/'typing-data.json'))}));console.log(JSON.stringify({json.dumps(SOURCES)}.map(s=>typesetText(s,maps,{{width:1000}}))));"
 boxes=json.loads(subprocess.check_output(['node','--input-type=module','-e',script],text=True));results=[]
 for index,(text,box)in enumerate(zip(SOURCES,boxes)):
  folder=output/str(index);folder.mkdir();(folder/'text.tex').write_text(r'\documentclass{article}\pagestyle{empty}\begin{document}\noindent\special{dvisvgm:raw <rect id="origin" x="{?x}" y="{?y}" width="0" height="0"/>}'+text+r'\end{document}')
  for command in [['latex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','text.tex'],['dvisvgm','--no-fonts=0','--exact-bbox','--precision=8','--output=reference.svg','text.dvi']]:subprocess.run(command,cwd=folder,env=env,capture_output=True,check=True)
  ref=ET.parse(folder/'reference.svg').getroot();defs={e.attrib['id']:e for e in ref.iter()if'id'in e.attrib};origin=defs['origin'];actual=[];expected=[]
  for use in ref.iter():
   if not use.tag.endswith('}use'):continue
   pen=BoundsPen(None);parse_path(defs[use.attrib['{http://www.w3.org/1999/xlink}href'][1:]].attrib['d'],pen);expected.append([v+float(use.attrib['x'if i%2==0 else'y'])-float(origin.attrib['x'if i%2==0 else'y'])for i,v in enumerate(pen.bounds)])
  maps=json.loads((root/'typing-text/symbol-mapping.json').read_text())['symbols']
  for item in box['items']:
   token=item['key'].split('/',1)[1];idx=list(maps).index(token);asset=ET.parse(root/'typing-text'/str(idx)/'expression.svg').getroot();ad={e.attrib['id']:e for e in asset.iter()if'id'in e.attrib};ao=ad['box-origin']
   for use in asset.iter():
    if not use.tag.endswith('}use'):continue
    pen=BoundsPen(None);parse_path(ad[use.attrib['{http://www.w3.org/1999/xlink}href'][1:]].attrib['d'],pen);actual.append([v+float(use.attrib['x'if i%2==0 else'y'])-float(ao.attrib['x'if i%2==0 else'y'])+item['x'if i%2==0 else'y']for i,v in enumerate(pen.bounds)])
  assert len(actual)==len(expected),(text,len(actual),len(expected));error=max(abs(a-b)for aa,bb in zip(actual,expected)for a,b in zip(aa,bb));results.append({'source':text,'maxInkPositionErrorBp':error,'passed':error<.003})
 receipt={'cases':results,'passed':all(r['passed']for r in results),'scope':'Same-family unwrapped text glyphs, kerning and ligatures; paragraph linebreaking is independent greedy word flow.'};(output/'text-flow-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
 if not receipt['passed']:raise SystemExit('Text positions differ from LaTeX')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--atlas',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.root,a.atlas,a.output)
