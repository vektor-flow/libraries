"""Python 3.14 driver: compare VKF ASTs with the existing math grammar.

The executable is compiled before expressions are written. The JavaScript
parser is an independent development oracle, never the VKF production runtime.
This progressively qualifies the port; a passing set is not full parser/layout
or complete document-render parity.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

if sys.version_info[:2] != (3, 14):
    raise SystemExit('Reference checks require Python 3.14')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--compiler', type=Path, required=True)
parser.add_argument('--fonts', type=Path, required=True,
                    help='Qualified font catalog profile directory')
parser.add_argument('--metrics', type=Path, required=True,
                    help='Original metrics JSON for the independent parser')
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--wasm-compiler', type=Path)
parser.add_argument('--wasm-runtime', type=Path)
parser.add_argument('--preview', action='store_true')
args = parser.parse_args()
if args.wasm_compiler and not args.wasm_runtime:
    parser.error('--wasm-runtime is required with --wasm-compiler')
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = {'componentOnly': True, 'completeRendererPort': False,
          'nativeSemantics': not args.preview,
          'fullParserPort': False, 'compilerSha256': sha(args.compiler),
          'sourceHashes': {p.name: sha(p) for p in root.glob('*.vkf')},
          'catalogSha256': sha(args.fonts/'catalog.vkfont'),
          'metricsSha256': sha(args.metrics), 'cases': []}


def run(command, input=None, timeout=120):
    result = subprocess.run(list(map(str, command)), input=input, text=True,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        report['failure'] = {'command': list(map(str, command)),
                             'exitCode': result.returncode,
                             'stdout': result.stdout, 'stderr': result.stderr}
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


try:
    executable = args.output/'math_dump'
    diagnostics = run([args.compiler, '-b', root/'math_dump.vkf', '-o', executable,
                       '--diagnostics'])
    (args.output/'build.json').write_text(diagnostics)
    cases = ['', 'a', 'x+y=2', 'α+β≤γ', r'\le\ge\ne\land\lor',
             r'\{a\}', r'\frac{a}{b}', r'\frac ab', r'\dfrac{x^2}{y_1}',
             r'\tfrac{a}{\frac{b}{c}}', r'\binom{a}{b}', r'\dbinom ab',
             r'\tbinom{x}{2}', r'\genfrac{[}{]}{0pt}{2}{a}{b}',
             r'\sqrt{x}', r'\sqrt[2]{x+1}', r'\sqrt[\frac12]{x}',
             r'\left(\frac{a}{b}\right)^2', r'\left. a\right|_1',
             r'\left(a+\left[b\right]\right)', r'(a+b)^2',
             r'\mathbf{a}+\mathcal{b}+\bm{x}', r'\mathop{a}\limits_1^2',
             r'\mathrel{a}+\mathord b', r'\hat{x}+\overline{ab}',
             r'\overbrace{a+b}^{x}', r'\smash[t]{x}+\phantom{b}',
             r'a\,b\:c\;x\!y\quad a\qquad b~c\ x',
             r'\displaystyle a+\scriptstyle b+\scriptscriptstyle c',
             r'\sum\nolimits_{a}^b', r"x''^2", r'x^a^b', r'x_a_b',
             r'^2+_a', r'\frac{a}', r'\sqrt', r'{a', r'{',
             r'x^}', r'\left(a', r'\unknown+$', r'\label{eq:x}x',
             r'a\\[2pt]b\newline c', r'\not a', r'\notag a\nonumber',
             r'\relax\protect\allowbreak a', r'x^{\frac{a}{b_2}}',
             r'\mathstrut+x', r'\overset{a}{x}', r'\underset{b}{x}',
             r'\stackrel{a}{=}', r'\xrightarrow{a}', r'\xleftarrow[b]{a}',
             r'\xrightarrow[\frac12]{x^2}',
             r'a\pmod{b}', r'a\pod b', r'a\mod{x}+\bmod b',
             r'a\kern-1.5pt b', r'a\hspace{2em}b', r'a\mkern+.5mu b',
             r'\mskip 2. pt a', r'\hspace', r'\kern{',
             r'\bigl(a\Bigr)', r'\Biggl\{x\biggr\}', r'\big',
             r'\left(a\middle|b\right)', r'\right)', r'\end{matrix}',
             r'\sqrt[2', r'\genfrac{}{}{}{3}ab', r'\genfrac',
             r'\text{abc def}', r'\textbf{abc \textit{xy} z}',
             r'\text{a\emph{b\emph{x}}c}', r'\text{a{b}c}',
             r'\text{\%\$\#\&\_\{\}\textbackslash\textasciicircum\textasciitilde\ }',
             r'\text{a\unsupported b}', r'\text{a\textbf b}',
             r'\text{a\textbf{b}', r'\text', r'\tag{1}', r'\tag*{a b}',
             r'\operatorname{lim}_x', r'\operatorname*{sup}_{a}^b',
             'a\u00a0+\u2009b', r'\text{α β}', r'\textrm{a~b}',
             r'\text{\emph{a\textnormal{b}}}', r'\texttt{a b}',
             'a+', '(a+', '[a=b+', r'\left(a+\right)',
             'a'*3000, r'\text{'+'x'*1200+'}', '{'*32+'a'+'}'*32,
             ' '.join('\\unsupported'+chr(97+i//26)+chr(97+i%26) for i in range(40))]
    for depth in [1, 3, 8]:
        cases.append('a_{'*depth+'x'+'}'*depth)
        cases.append(r'\frac{a}{'*depth+'b'+'}'*depth)
    for name in ['eqnarray','eqnarray*','matrix','pmatrix','bmatrix','Bmatrix',
                 'vmatrix','Vmatrix','smallmatrix','cases','aligned','align',
                 'align*','array','gathered','split','multline','multline*',
                 'gather','gather*','equation','equation*','alignat','alignat*',
                 'substack','subarray']:
        columns = '{rl|c}' if name == 'array' else '{l}' if name == 'subarray' else '{2}' if name.startswith('alignat') else ''
        cases.append(r'\begin{'+name+'}'+columns+r'a&b\\[2pt]c&d\end{'+name+'}')
    cases.extend([
        r'\begin{matrix}\end{matrix}', r'\begin{matrix}a&\end{matrix}',
        r'\begin{matrix}a\\\end{matrix}', r'\begin{matrix}\\\end{matrix}',
        r'\begin{matrix}a\\\hline\end{matrix}',
        r'\begin{array}{|rl|}\hline a&b\\[1ex]\cline{1-2}c&d\\\hline\end{array}',
        r'\begin{array}{*{2}{c}}a&b\end{array}',
        r'\begin{matrix}a\hline b\end{matrix}',
        r'\begin{matrix}\begin{pmatrix}a\\b\end{pmatrix}&\frac{a}{b}\end{matrix}',
        r'\pmatrix{a&b\\c&d}', r'\substack{a\\b}', r'\array{rl}{a&b}',
        r'\pmatrix{}', r'\pmatrix a&b}', r'\begin{ma}a\end{ma}',
        r'\begin{unknown}a\end{unknown}', r'\begin{matrix}a\end{pmatrix}',
        r'\begin{matrix}', '\\begin{matrix} ', r'\begin{matrix}a\\',
        '\\begin{matrix}a\\\\ ', r'\pmatrix{', r'\pmatrix{a',
        r'\begin{alignat}2a&b\end{alignat}', r'\begin{alignat}a&b\end{alignat}',
        r'\begin{array}', r'\begin', r'\begin{matrix}\cline',
        r'\begin{matrix}a\\[2pt', r'\begin{matrix}a&\right)',
        r'a\\[{x[y]z}]b', r'\smash[[t]]{a}', r'\smash[t',
        r'\dots', r'\dots+a', r'\dots=a', r'\dots\not a',
        r'\dots\int a', r'\dots≤a', r'\dots\le a',
        r'\dotsc+\dotsb+\dotsm+\dotsi', r'a\cdots', r'\cdots a',
        r'\left(a\cdots\right)', r'a\ldots b\ddots c',
        r'\Hat{x}\Check{a}\Tilde b\Acute c\Grave x',
        r'\Dot x\Ddot a\Breve b\Bar c\Vec x',
        r'\begin{matrix}a+&b+\\c+&+\end{matrix}',
    ])
    for columns in [1, 3, 17, 40]:
        row = '&'.join(['a']*columns)
        cases.append(r'\begin{matrix}'+r'\\[2pt]'.join([row]*3)+r'\end{matrix}')
    cases.append(r'\begin{matrix}'+r'\\'.join([r'\hline a&b']*40)+r'\end{matrix}')
    cases.append(r'\begin{matrix}'*20+'a'+r'\end{matrix}'*20)
    for name in ['black','white','red','green','blue','cyan','magenta','yellow',
                 'gray','grey','darkgray','lightgray','orange','purple','teal',
                 'brown','lime','olive','pink','violet','ReD','blacK']:
        cases.append(r'\color{'+name+'}a')
    for value in ['#abc','#ABC','#abcdef','#ABCDEF','#000','#fff','bad','',
                  '#ff','#ffff','#ggg','blue!50!red']:
        cases.append(r'\textcolor{'+value+'}{a_1}')
    for n in range(256):
        value = f'{n:02x}{37*n%256:02x}{97*n%256:02x}'
        cases.append(r'\textcolor[HTML]{'+value+'}{a}')
    for model, value in [
        ('rgb','0.3,.5,1'),('RGB','1,2,3'),('RGB','255,128,0'),
        ('rgb','0x1,0b1,0o0'),('RGB','0xff,0b10000000,0o10'),
        ('rgb','+1.,+.5e0,-0'),('rgb',',,'),('rgb','1e-323,1e-300,1e-7'),
        ('rgb','-1e-10000,0,1'),('rgb','1.00000000000000001,0,1'),
        ('RGB','255.00000000000000001,0,1'),
        ('rgb','0e9999999999999,0,1'),('rgb','000.30000,0,1'),
        ('rgb','\v0.3\f,0,1'),('rgb','\ufeff0.5\u00a0,0,1'),
        ('rgb','2,0,0'),('rgb','-0.1,0,0'),('rgb','NaN,0,0'),
        ('rgb','Infinity,0,0'),('rgb','1e99999,0,0'),('rgb','+0xff,0,0'),
        ('rgb','0.3,0.2'),('rgb','1,2,3,4'),('rgb','1e,0,0'),
        ('other','red'),('HTML','red'),('RGB','1 e0,0,0'),
    ]:
        cases.append(r'\textcolor['+model+']{'+value+'}{a}')
    cases.extend([r'\color', r'\color[rgb', r'\textcolor{red}', r'\color{bad}a'])
    # Exact decimal midpoints exercise round-to-nearest/even rather than a
    # tolerance that would hide an incorrectly parsed source component.
    from decimal import Decimal, localcontext
    import math
    with localcontext() as context:
        context.prec = 2000
        for value in [0.1, 0.3, 0.5, math.nextafter(1.0, 0.0)]:
            adjacent = math.nextafter(value, 1.0)
            midpoint = (Decimal.from_float(value)+Decimal.from_float(adjacent))/2
            for delta in [Decimal(0), Decimal('1e-100'), -Decimal('1e-100')]:
                cases.append(r'\color[rgb]{'+str(midpoint+delta)+',0,1}a')
        midpoint = Decimal.from_float(math.ulp(0.0))/2
        for delta in [Decimal(0), Decimal('1e-1400'), -Decimal('1e-1400')]:
            cases.append(r'\color[rgb]{'+str(midpoint+delta)+',0,1}a')
    import random
    generator = random.Random(20261016)
    for _ in range(64):
        value = ','.join(repr(generator.uniform(0, 255)) for _ in range(3))
        cases.append(r'\textcolor[RGB]{'+value+'}{a+b}')
    cases.append(r'\color[RGB]{0.3,0.2,0.1}a')
    for raw in ['', '0', '-0', '1234', '12345', '123456', '1234567',
                '00000', '.3', '3.', '0,003', '+12345.67890e-03',
                '1e2', '1E0002', '1e', '1e+', '1e-', '+', '-', '.', ',',
                'a', '1,2.3', '1e2e3', '1 2 3', '12\t34\n5.67\u00a0890']:
        cases.append(r'\num{'+raw+'}')
        cases.append(r'\num[group-digits=false,output-decimal-marker={,}]{'+raw+'}')
    import re
    vocabulary = (root.parent/'units.mjs').read_text()
    unit_names = re.findall(r'(?:^|,)([A-Za-z]\w*):',
                           vocabulary.split('const units={', 1)[1].split('};', 1)[0])
    prefix_names = re.findall(r'(?:^|,)([A-Za-z]\w*):',
                             vocabulary.split('const prefixes={', 1)[1].split('};', 1)[0])
    for name in unit_names:
        cases.append(r'\unit{'+'\\'+name+'}')
    for name in prefix_names:
        cases.append(r'\si{'+'\\'+name+r'\metre}')
    for raw in [r'\kilo\metre\per\second\squared', 'm/s', r'\metre\per\second\per\ampere',
                r'\per\metre', r'\metre\tothe{-3}', r'\metre\raiseto{2}\second',
                r'\square\metre\cubic\second', r'\raiseto{-2}\metre',
                r'\metre\per\second\tothe{-3}', r'\metre\tothe{}\squared',
                r'\squared', r'\tothe{2}', r'\metre^+2', r'\metre^{+0002}',
                r'\metre^', r'\metre^{', r'\metre^{2', r'\metre^{12345678}',
                r'\metre^{-12345678}', r'\metre^{α}', r'\kilo\per', r'\per',
                r'\raiseto{}', r'\micro', r'\micro\metre', r'\micro/',
                'µm Ω °', r'\degreeCelsius', 'unknown', r'\unknown', '{m}',
                r'\metre.\second*\ampere\,\kelvin\;\mole~\candela', '', '/', '1.2']:
        for mode in ['power','symbol','fraction','reciprocal']:
            cases.append(r'\unit[per-mode='+mode+']{'+raw+'}')
    cases.extend([
        r'\qty{1.2e3}{\kilo\metre\per\second\squared}^2',
        r'\SI[group-digits=none]{12345}{\micro\metre}',
        r'\qty[per-mode=fraction]{3}{\per\second}',
        r'\qty[per-mode=symbol]{4}{\metre\per\second\per\ampere}',
        r'\num', r'\qty', r'\qty{1}', r'\unit', r'\ang', r'\ang{}',
        r'\ang{1;2;3;4}', r'\ang{;2;}', r'\ang{ ;1e-;}',
        r'\qty[bad=yes]{a}', r'\num[group-digits=all,output-decimal-marker={,}]{12345.67890}',
        r'\num[per-mode=fraction=ignored]{1}', r'\num[ ]{1}',
        r'\num[output-decimal-marker={{,}}]{1.2}', r'\qty[per-mode={fraction,group-digits=false]{1}{m}',
    ])
    cases.append(r'\num{'+'1234567890'*120+'}')
    cases.append(r'\unit{'+r'\metre '*200+'}')
    # Same expressions/path receive changed contents after compilation.
    cases.extend(['a+b', 'a+c', 'a+b'])
    (args.output/'cases.json').write_text(json.dumps(cases, ensure_ascii=False))
    reference = args.output/'reference.mjs'
    reference.write_text('''import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {parseDraft}=await import(pathToFileURL(process.argv[2]));
const maps=JSON.parse(await readFile(process.argv[3])).maps;
const cases=JSON.parse(await readFile(process.argv[4]));
console.log(JSON.stringify(cases.map(source=>parseDraft(source,maps.display,{nativeSemantics:process.argv[5]==='true'}))));
''')
    references = json.loads(run(['node', reference, root.parent/'draft-parser.mjs',
                                 args.metrics, args.output/'cases.json',
                                 str(not args.preview).lower()]))
    (args.output/'reference-results.json').write_text(json.dumps(references, ensure_ascii=False))
    source_path = args.output/'changed-after-compilation.tex'
    for index, (source, expected) in enumerate(zip(cases, references)):
        source_path.write_text(source)
        destination = args.output/('case-'+str(index)+'.json')
        run([executable], '\n'.join(map(str, [args.fonts/'catalog.vkfont',
                                             source_path, destination,
                                             'preview' if args.preview else 'native']))+'\n')
        actual = json.loads(destination.read_bytes())
        equal = actual == expected
        report['cases'].append({'index': index, 'source': source, 'equal': equal})
        if not equal:
            report['cases'][-1].update(actual=actual, expected=expected)
    report['passed'] = all(case['equal'] for case in report['cases'])
    if args.wasm_compiler and report['passed']:
        kernel = args.output/'math_kernel'
        diagnostics = run([args.compiler, '-b', root/'math_kernel.vkf', '-o', kernel,
                           '--diagnostics'])
        (args.output/'kernel-build.json').write_text(diagnostics)
        wasm = args.output/'math_kernel.wasm'
        manifest = args.output/'kernel-wasm.json'
        run([args.wasm_compiler, '--typed-ir', json.loads(diagnostics)['typed_ir_path'],
             '--wasm', wasm, '--manifest', manifest, '--entry', 'math_ast', '--prune-to-entry'])
        run(['node', root/'verify_math_wasm.mjs', args.wasm_runtime, manifest, wasm,
             args.fonts/'catalog.vkfont', args.output/'cases.json',
             args.output/'reference-results.json', args.output/'wasm-verification.json',
             str(not args.preview).lower()], timeout=240)
        report['wasm'] = {'passed': True, 'cases': len(cases),
                          'wasmSha256': sha(wasm),
                          'compilerSha256': sha(args.wasm_compiler),
                          'runtimeSha256': sha(args.wasm_runtime)}
finally:
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'passed': report['passed'], 'cases': len(report['cases']),
                  'different': [c['index'] for c in report['cases'] if not c['equal']]}))
if not report['passed']:
    raise SystemExit(1)
