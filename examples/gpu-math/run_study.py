"""Build and independently check six real-LaTeX expression fields."""
import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path
from latex_paths import compile_expression
from verify_latex_field import verify

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--generator',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('Use a fresh study output directory')
    args.output.mkdir(parents=True)
    root=Path(__file__).resolve().parent
    engine=Path(shutil.which('latex')).absolute()
    converter=Path(shutil.which('dvisvgm')).absolute()
    results=[]
    for formula in sorted((root/'formulas').glob('*.tex')):
        folder=args.output/formula.stem
        start=time.monotonic()
        compile_expression(formula,folder,engine,converter,args.generator.resolve())
        elapsed=time.monotonic()-start
        checked=verify(folder)
        receipt=json.loads((folder/'build-receipt.json').read_text())
        results.append({'formula':formula.name,'buildSeconds':elapsed,
            'counts':receipt['counts'],'textureSize':receipt['texture']['size'],
            'verification':checked})
    summary={'schema':'vkf.direct-latex-study/1','cases':results,
        'sourceHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [root/'latex_paths.py',root/'verify_latex_field.py',root/'run_study.py']},
        'passed':all(r['verification']['passed'] for r in results),
        'notes':['Offline CPU preparation, no GPU timing or physical GPU testing.',
            'TeX Live verified; no MiKTeX equivalence claim.',
            'Entire expression field; per-outline tiled caching remains future work.']}
    (args.output/'study-verification.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'cases':len(results),'passed':summary['passed'],
        'totalSignChecks':sum(r['verification']['tested'] for r in results)}))
