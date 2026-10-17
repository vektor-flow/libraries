"""Prepare reusable TeX command semantics; no author document or PDF input."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path

def dots_follow(token,meaning):
 # amsmath's mdots@@ examines the following token's *meaning*, not merely
 # its final atom class. Protected composites can therefore select low dots.
 if token=='\\not':return 'centered'
 char=re.match(r'\\mathchar"([0-9A-Fa-f])',meaning)
 if char:return 'centered'if int(char[1],16)in (2,3)else'baseline'
 body=meaning.partition('->')[2].lstrip()
 if body.startswith(('\\DOTSB','\\mathbin','\\mathrel','\\not ')):return 'centered'
 if body.startswith('\\DOTSI'):return 'integral'
 return 'baseline'

def prepare(source,output,packages):
 if output.exists():raise ValueError('Use a fresh output directory')
 if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*',p)for p in packages):raise ValueError('Invalid package identifier')
 output.mkdir();oracle=output/'oracle';oracle.mkdir();data=json.loads((source/'typing-data.json').read_text())
 tokens=sorted({t for m in data['maps'].values()for t in m['symbols']if re.fullmatch(r'\\[A-Za-z]+',t)})
 tex=r'\documentclass{article}'+''.join(r'\usepackage{'+p+'}'for p in packages)+r'\begin{document}'
 for i,token in enumerate(tokens):tex+='\n\\typeout{MEANING-'+str(i)+':\\meaning'+token+'}'
 tex+=r'\end{document}';(oracle/'source.tex').write_text(tex);env=os.environ.copy();env['max_print_line']='10000'
 result=subprocess.run(['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','source.tex'],cwd=oracle,env=env,capture_output=True,text=True,timeout=30);(oracle/'compile.log').write_text(result.stdout+result.stderr);result.check_returncode()
 meanings={tokens[int(i)]:v for i,v in re.findall(r'MEANING-(\d+):(.*)',result.stdout)}
 if len(meanings)!=len(tokens):raise ValueError('Incomplete native command metadata')
 for mapping in data['maps'].values():
  for token,symbol in mapping['symbols'].items():
   if token in meanings:symbol['dotsFollow']=dots_follow(token,meanings[token])
 (oracle/'meanings.json').write_text(json.dumps(meanings,indent=2));(output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));shutil.copy2(source/'atlas.rgba.gz',output/'atlas.rgba.gz')
 print(json.dumps({'nativeCommands':len(meanings),'packages':packages}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--packages',default='amsmath,amssymb');a=p.parse_args();prepare(a.source,a.output,a.packages.split(','))
