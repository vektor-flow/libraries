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

def build(output,style="display",extended=False,extras=None,reuse=None,point_size=10,alphabet=None,package=None,characters=None):
    sizes={10:(10,7,5),11:(10.95,8,6),12:(12,8,6)}
    if point_size not in sizes:raise ValueError("Unsupported native article point size")
    normal,script,scriptscript=sizes[point_size]
    size=normal if style in ("display","text") else script if style=="script" else scriptscript
    if output.exists(): raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True)
    symbols={}
    catalogue=TOKENS;aliases={}
    if extended:
        import runpy
        config=runpy.run_path(str(Path(__file__).with_name('extended-symbols.py')))
        catalogue,aliases=config['TOKENS'],config['ALIASES']
    if alphabet is not None:
        if not re.fullmatch(r'[A-Za-z]+',alphabet)or not package or not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*',package):raise ValueError('Invalid math alphabet or package name')
        characters=string.ascii_letters+string.digits if characters is None else characters
        if not characters or any(c not in string.ascii_letters+string.digits for c in characters):raise ValueError('Invalid alphabet character set')
        catalogue={'@font:'+alphabet+':'+c:'ord'for c in characters}
        aliases={token:'\\'+alphabet+'{'+token.rsplit(':',1)[1]+'}'for token in catalogue}
    import os
    env=dict(os.environ)
    if extras:
        for variable in ['TEXINPUTS','TFMFONTS','TEXFONTS','MFINPUTS','T1FONTS']:
            env[variable]=str(extras.resolve())+'//:'+env.get(variable,'')
    style_command={'display':r'\displaystyle','text':r'\textstyle','script':r'\scriptstyle','scriptscript':r'\scriptscriptstyle'}[style]
    prior=json.loads((reuse/'symbol-mapping.json').read_text())['symbols'] if reuse else {}
    prior_indices={token:i for i,token in enumerate(prior)}
    for index,(token,kind) in enumerate(catalogue.items()):
        folder=output/str(index)
        if token in prior:
            symbols[token]=prior[token];folder.symlink_to((reuse/str(prior_indices[token])).resolve(),target_is_directory=True);continue
        folder.mkdir()
        source=(r'\documentclass['+str(point_size)+r'pt]{article}\usepackage{amsmath,amssymb,graphicx}'+(r'\usepackage[nointlimits]{esint}' if extras else '')+(r'\usepackage{siunitx}' if extras and (extras/'siunitx.sty').exists() else '')+(r'\usepackage{mathrsfs}\DeclareMathAlphabet{\vkfbb}{U}{bbold}{m}{n}'if extras and (extras/'mathrsfs.sty').exists()else '')+r'\pagestyle{empty}'+'\n'+
            (r'\usepackage{'+package+'}'if package else '')+r'\begin{document}\setbox0=\hbox{$'+style_command+' '+aliases.get(token,token)+r'$}'+ '\n'+
            r'\typeout{BOXWIDTH:\the\wd0}\typeout{BOXHEIGHT:\the\ht0}\typeout{BOXDEPTH:\the\dp0}'+ '\n'+
            r'\noindent\special{dvisvgm:raw <rect id="box-origin" x="{?x}" y="{?y}" width="0" height="0"/>}\box0\end{document}')
        (folder/'expression.tex').write_text(source)
        for command in [['latex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','expression.tex'],
            ['dvisvgm']+(['--fontmap=+'+str(extras.resolve()/name)for name in ['esint.map','rsfs.map','bbold.map']if(extras/name).exists()] if extras else [])+['--no-fonts=0','--exact-bbox','--precision=8','--output=expression.svg','expression.dvi']]:
            result=subprocess.run(command,cwd=folder,capture_output=True,text=True,check=True,timeout=30,env=env)
            (folder/(command[0]+'.log')).write_text(result.stdout+result.stderr)
        log=(folder/'expression.log').read_text()
        metrics={name:float(re.search('BOX'+name.upper()+r':([-\d.]+)pt',log)[1])*72/72.27 for name in ['width','height','depth']}
        packet=extract((folder/'expression.svg').read_text())
        tree=ET.parse(folder/'expression.svg').getroot()
        origin=next(e for e in tree.iter() if e.attrib.get('id')=='box-origin')
        ox,oy=float(origin.attrib['x']),float(origin.attrib['y'])
        from fontTools.pens.svgPathPen import SVGPathPen
        from fontTools.pens.recordingPen import RecordingPen
        from fontTools.pens.transformPen import TransformPen
        from fontTools.misc.transform import Transform
        from fontTools.svgLib.path import parse_path
        combined=SVGPathPen(None)
        for primitive in packet['primitives']:
            t=list(primitive['transform']);t[4]+=packet['sourceViewBox'][0]-ox;t[5]+=packet['sourceViewBox'][1]-oy
            parse_path(packet['outlines'][primitive['outline']]['svgPath'],TransformPen(combined,Transform(*t)))
        d=combined.getCommands()
        # Preserve literal upstream spelling for an unshifted single glyph.
        if len(packet['primitives'])==1 and abs(t[4])+abs(t[5])<1e-6:
            d=packet['outlines'][packet['primitives'][0]['outline']]['svgPath']
        pen=RecordingPen();parse_path(d,pen)
        symbols[token]={'class':kind,**metrics,'outline':{'svgPath':d,'commands':pen.value},'outlineHash':hashlib.sha256(d.encode()).hexdigest(),'oracleToken':aliases.get(token,token),'italic':0}
    # Em size for standard 10pt math, in the SVG bp coordinates of our outlines.
    result={'schema':'vkf.latex-symbol-mapping/1','fontPointSize':point_size,'em':size*72/72.27,'style':style,'symbols':symbols,
        'oracle':f'Real TeX Live latex, standard {point_size}pt Computer Modern/AMS',
        'limits':['Measured standard glyphs and composite symbols only; expression layout is a separate runtime.',
            'Box metrics include measured italic correction; pair rules need separate validation.']}
    from fontTools.tfmLib import TFM
    tfm=TFM(subprocess.check_output(['kpsewhich',f'cmsy{min(10,int(size))}.tfm'],text=True).strip())
    result['parameters']={name:value*size*72/72.27 for name,value in tfm.fontdimens.items()}
    extension=TFM(subprocess.check_output(['kpsewhich','cmex10.tfm'],text=True).strip())
    result['parameters'].update({key:value*size*72/72.27 for key,value in extension.fontdimens.items() if key.startswith('BIGOP')})
    result['parameters']['RULE']=TFM(subprocess.check_output(['kpsewhich','cmex10.tfm'],text=True).strip()).fontdimens['DEFAULTRULETHICKNESS']*10*72/72.27
    (output/'symbol-mapping.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'mappedSymbols':len(symbols)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--style',choices=['display','text','script','scriptscript'],default='display')
    parser.add_argument('--point-size',type=int,choices=[10,11,12],default=10);parser.add_argument('--extended',action='store_true');parser.add_argument('--oracle-extras',type=Path);parser.add_argument('--reuse',type=Path);parser.add_argument('--alphabet');parser.add_argument('--package');parser.add_argument('--characters')
    args=parser.parse_args();build(args.output,args.style,args.extended,args.oracle_extras,args.reuse,args.point_size,args.alphabet,args.package,args.characters)
