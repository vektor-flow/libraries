"""Development-only single-font PK templates for reusable mask preparation.

Accepts native font names, never article source or a reference PDF. pdfTeX and
METAFONT are offline font preparation tools; generated templates are not runtime
inputs. Every available glyph of each selected TFM is included.
"""
import argparse,json,os,re,subprocess
from pathlib import Path
from fontTools.tfmLib import TFM

def prepare(names,output,extras=None):
 output.mkdir();env=os.environ.copy();env.update(TEXMFVAR=str(output.resolve()/'cache'),VARTEXFONTS=str(output.resolve()/'fonts'))
 if extras:env.update(TEXMFHOME=str(extras.resolve()),TFMFONTS=str(extras.resolve())+'//:')
 rows=[]
 for name in names:
  if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',name):raise ValueError('Invalid native font name')
  path=subprocess.check_output(['kpsewhich',name+'.tfm'],text=True,env=env).strip();tfm=TFM(path)
  text=r'\pdfoutput=1\pdfpkresolution=600\font\native='+name+r'\native\setbox0=\hbox{'+''.join(r'\char'+str(code)+' 'for code in tfm.chars)+r'}\shipout\box0\end'
  (output/(name+'.tex')).write_text(text)
  p=subprocess.run(['pdftex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error',name+'.tex'],cwd=output,env=env,capture_output=True)
  (output/(name+'.compile.log')).write_bytes(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError('Native font preparation failed: '+name)
  rows.append({'font':name,'glyphCodes':list(tfm.chars),'pkResolution':600,'template':name+'.pdf'})
 (output/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('fonts',nargs='+');parser.add_argument('--oracle-extras',type=Path);args=parser.parse_args();prepare(args.fonts,args.output,args.oracle_extras)
