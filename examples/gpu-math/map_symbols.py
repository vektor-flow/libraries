"""Development-only LaTeX oracle: export standard symbol outlines and box metrics."""
import argparse
import hashlib
import json
import re
import string
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from latex_paths import extract

TOKENS={c:'ord' for c in string.ascii_letters+string.digits}
TOKENS.update({t:'ord' for t in [r'\alpha',r'\beta',r'\gamma',r'\delta',r'\theta',r'\lambda',r'\mu',r'\pi',r'\sigma',r'\omega',r'\Gamma',r'\Delta',r'\Omega',r'\infty']})
TOKENS.update({'+':'bin','-':'bin','=':'rel','<':'rel','>':'rel',r'\leq':'rel',r'\geq':'rel','(':'open',')':'close','[':'open',']':'close',',':'punct'})

def build(output):
    if output.exists(): raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True)
    symbols={}
    for index,(token,kind) in enumerate(TOKENS.items()):
        folder=output/str(index);folder.mkdir()
        source=(r'\documentclass{article}\usepackage{amsmath,amssymb}\pagestyle{empty}'+'\n'+
            r'\begin{document}\setbox0=\hbox{$\displaystyle '+token+r'$}'+ '\n'+
            r'\typeout{BOXWIDTH:\the\wd0}\typeout{BOXHEIGHT:\the\ht0}\typeout{BOXDEPTH:\the\dp0}'+ '\n'+
            r'\noindent\box0\end{document}')
        (folder/'expression.tex').write_text(source)
        for command in [['latex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','expression.tex'],
            ['dvisvgm','--no-fonts=0','--exact-bbox','--precision=8','--output=expression.svg','expression.dvi']]:
            result=subprocess.run(command,cwd=folder,capture_output=True,text=True,check=True,timeout=30)
            (folder/(command[0]+'.log')).write_text(result.stdout+result.stderr)
        log=(folder/'expression.log').read_text()
        metrics={name:float(re.search('BOX'+name.upper()+r':([-\d.]+)pt',log)[1])*72/72.27 for name in ['width','height','depth']}
        packet=extract((folder/'expression.svg').read_text())
        if len(packet['primitives'])!=1: raise ValueError(f'Expected one filled outline for {token}')
        outline=packet['outlines'][packet['primitives'][0]['outline']]
        symbols[token]={'class':kind,**metrics,'outline':outline,'outlineHash':packet['primitives'][0]['outline']}
    # Em size for standard 10pt math, in the SVG bp coordinates of our outlines.
    result={'schema':'vkf.latex-symbol-mapping/1','em':10*72/72.27,'symbols':symbols,
        'oracle':'Real TeX Live latex, standard 10pt Computer Modern/AMS',
        'limits':['Ordinary single glyph atoms only; no scripts, fractions, macros or arbitrary packages.',
            'Box metrics include measured italic correction; pair rules need separate validation.']}
    (output/'symbol-mapping.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'mappedSymbols':len(symbols)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.output)
