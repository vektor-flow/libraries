"""Measure independent PDF compilation and page rasterization in fresh processes."""
import argparse,json,subprocess,time
from pathlib import Path

def benchmark(corpus,trials):
 sources=json.loads((corpus/'sources.json').read_text());rows=[]
 for source in sources:
  folder=corpus/source['name'];results=[]
  for trial in range(trials):
   t=time.perf_counter();run=subprocess.run(['pdflatex','-no-shell-escape','-interaction=nonstopmode','-halt-on-error','source.tex'],cwd=folder,capture_output=True,timeout=90);compiled=time.perf_counter();(folder/f'compile-trial-{trial}.log').write_bytes(run.stdout+run.stderr)
   if run.returncode:results.append({'trial':trial,'compileMs':(compiled-t)*1000,'exitCode':run.returncode});break
   subprocess.run(['pdftoppm','-png','-r','96','source.pdf','reference'],cwd=folder,capture_output=True,check=True,timeout=90);finished=time.perf_counter();results.append({'trial':trial,'compileMs':(compiled-t)*1000,'rasterizeAndEncodeMs':(finished-compiled)*1000,'sourceToPNGMs':(finished-t)*1000,'exitCode':0})
  rows.append({'name':source['name'],'trials':results,'referencePages':len(list(folder.glob('reference-*.png')))})
 receipt={'engine':subprocess.check_output(['pdflatex','--version'],text=True).splitlines()[0],'rasterizer':subprocess.run(['pdftoppm','-v'],capture_output=True,text=True).stderr.splitlines()[0],'dpi':96,'documents':rows,'scope':'Fresh engine process per trial, existing auxiliary files and OS caches retained. PDF timing is separate from PNG rendering/encoding/I/O. Browser GPU timing excludes PNG encoding/I/O.'};(corpus/'engine-benchmark.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('--trials',type=int,default=3);a=p.parse_args();benchmark(a.corpus,a.trials)
