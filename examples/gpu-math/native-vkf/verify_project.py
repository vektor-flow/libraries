"""Python 3.14 differential driver: native VKF vs the existing project resolver.

All production input expansion remains VKF. Sources and file contents are
written after the native executable is built, including repeated local edits.
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
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--article', type=Path, help='Optional real .tex source; no supplied bbl')
parser.add_argument('--front-end', action='store_true', help='Also compare macros and theorem metadata')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = {'python': sys.version, 'cases': [], 'completeRendererPort': False,
          'compilerSha256': sha(args.compiler),
          'referenceSha256': sha(root.parent/'document-project.mjs'),
          'sourceHashes': {p.name: sha(p) for p in root.glob('*.vkf')}}
report['stage'] = 'project-macros-theorems' if args.front_end else 'project'
if args.front_end:
    report['macroReferenceSha256'] = sha(root.parent/'latex-modules/core/macros.mjs')


def run(command, **kwargs):
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=60, **kwargs)
    except subprocess.TimeoutExpired:
        report['failure'] = {'command': list(map(str, command)), 'timedOut': True,
                             'limitSeconds': 60}
        raise
    if result.returncode:
        report['failure'] = {'command': list(map(str, command)), 'stdout': result.stdout,
                             'stderr': result.stderr, 'exitCode': result.returncode}
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


try:
    entry = 'frontend_dump' if args.front_end else 'project_dump'
    executable = args.output/entry
    build = run([str(args.compiler), '-b', str(root/(entry+'.vkf')),
                 '-o', str(executable), '--diagnostics'])
    (args.output/'build.json').write_text(build)
    cases = [
        {'source': r'\input{sections/a}\bibliographystyle{plain}\bibliography{db}',
         'files': {'sections/a.tex': r'A \input{../common}', 'common.tex': 'α🙂',
                   'paper.bbl': r'\begin{thebibliography}{1}ref\end{thebibliography}'},
         'entry': 'paper.tex', 'jobName': 'paper'},
        {'source': 'before \\input{missing} after'},
        {'source': r'\input{../secret}\input{/etc/passwd}\input{https:foo}'},
        {'source': r'\input{a}', 'files': {'a.tex': r'A \input{b}', 'b.tex': r'B \input{a}'}},
        {'source': r'\input{a}', 'entry': 'a.tex', 'files': {'a.tex': r'\input{a}'}},
        {'source': r'\url{https://a.test/\input{x}%20}\href{x\input{y}}{label}'},
        {'source': '% \\input{missing}\n\\verb*|\\input{x}|'
                   r'\begin{verbatim}\input{x}\end{verbatim}'
                   r'\begin{comment}\include{y}\end{comment}'},
        {'source': r'\usepackage[backend=biber]{amsmath,biblatex}\bibliography{refs}'},
        {'source': r'\input{a}\include{a.tex}\input bare \input{empty}',
         'files': {'a.tex': {'text': 'α'}, 'bare': 'B', 'empty.tex': ''}},
        {'source': r'\input{invalid}', 'files': {'invalid.tex': {'text': 42}}},
        {'source': r'\input{same}', 'files': {'same.tex': 'first'}},
        {'source': r'\input{same}', 'files': {'same.tex': 'changed'}},
        {'source': r'\input{same}', 'files': {'same.tex': 'first'}},
    ]
    for count in [1, 3, 12, 31]:
        files = {f'sections/s{i}.tex': f'piece{i} é🙂' for i in range(count)}
        source = ''.join(r'\input{sections/s'+str(i)+'}' for i in range(count))
        cases.append({'source': source+source, 'files': files})
    for count in [1, 7, 30]:
        files = {f'{i}.tex': r'\input{'+str(i+1)+'}' for i in range(count)}
        files[f'{count}.tex'] = 'last'
        cases.append({'source': r'\input{0}', 'files': files})
    if args.front_end:
        cases.extend([
            {'source': r'\input{defs} \pair{x}{y}',
             'files': {'defs.tex': r'\newcommand{\pair}[2]{#1+#2}'}},
            {'source': r'\newcommand{\x}{a}\x   b'},
            {'source': r'\iffalse hidden\else shown\fi'},
            {'source': r'\newtheorem{lemma}{Lemma}[section]\theoremstyle{remark}'
                       r'\newtheorem{note}[lemma]{Note}\newtheorem*{claim}{Claim}body'},
            {'source': r'\newtheorem{x}{First}\newtheorem{x}{Second}body'},
            {'source': r'\DeclareMathOperator*{\lfoo}{limfoo}\lfoo_x'},
            {'source': r'\newcommand{\a}{\b}\newcommand{\b}[1]{[#1]}\a{x}'},
            {'source': r'\newcommand{\a}{\b}\newcommand{\b}[2][d]{#1:#2}\a[z]{x}'},
            {'source': r'\newcommand{\a}{\url}\newcommand{\x}{wrong}\a{https://a/\x#target}'},
            {'source': r'\newcommand{\a}{\iftrue}\a A\else B\fi'},
            {'source': r'\newcommand{\a}{\newcommand{\x}{A}}\a\x'},
        ])
    if args.article:
        files = {p.name: p.read_bytes().decode() for p in args.article.parent.glob('*.bib')}
        cases.append({'source': args.article.read_bytes().decode(), 'files': files,
                      'entry': args.article.name, 'jobName': args.article.stem})
        report['articleSha256'] = sha(args.article)
    cases_path = args.output/'cases.json'
    cases_path.write_text(json.dumps(cases, ensure_ascii=False))
    reference_driver = args.output/'reference.mjs'
    reference_driver.write_text('''import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {resolveDocumentProject}=await import(pathToFileURL(process.argv[2]));
const cases=JSON.parse(await readFile(process.argv[3]));
const {expandDocumentMacros}=await import(pathToFileURL(process.argv[4]));
const front=process.argv[5]==='true';
process.stdout.write(JSON.stringify(cases.map(c=>{
 const resolved=resolveDocumentProject(c.source,c);
 if(!front)return resolved;
 if(resolved.diagnostics.length)return {...resolved,valid:false,expansions:0,theorems:{}};
 const expanded=expandDocumentMacros(resolved.source);
 return {...resolved,...expanded,valid:expanded.diagnostics.length===0,theorems:Object.fromEntries(expanded.theorems)};
})));
''')
    reference = json.loads(run(['node', str(reference_driver),
                                str(root.parent/'document-project.mjs'), str(cases_path),
                                str(root.parent/'latex-modules/core/macros.mjs'),
                                'true' if args.front_end else 'false']))
    (args.output/'reference-results.json').write_text(json.dumps(reference, ensure_ascii=False))
    for index, (case, expected) in enumerate(zip(cases, reference)):
        source_path = args.output/'changed-after-compilation.tex'
        files_path = args.output/'changed-after-compilation-files.json'
        destination = args.output/('case-'+str(index)+'.tex')
        source_path.write_bytes(case['source'].encode())
        files_path.write_text(json.dumps(case.get('files', {}), ensure_ascii=False))
        inputs = [source_path, files_path, case.get('jobName', 'document'),
                  case.get('entry', ''), destination]
        output = run([str(executable)], input='\n'.join(map(str, inputs))+'\n')
        fields = output.splitlines()
        if args.front_end:
            assert (fields[0] == 'true') == expected['valid'], (index, 'front-end status')
            assert int(fields[1]) == expected['expansions'], (index, 'macro expansion count')
            declarations = json.loads(Path(str(destination)+'.theorems.json').read_bytes())
            assert int(fields[3]) == len(declarations), (index, 'declaration count')
            metadata = {}
            for declaration in declarations:
                name = declaration.pop('name')
                metadata[name] = declaration
            assert metadata == expected['theorems'], (index, 'theorem metadata')
            fields = fields[4:]
        names = [bytes.fromhex(value[1:-1]).decode() for value in fields[1:]]
        actual_source = destination.read_bytes().decode()
        actual_diagnostics = Path(str(destination)+'.diagnostics').read_bytes().decode()
        assert actual_source == expected['source'], (index, 'expanded source')
        assert int(fields[0]) == len(names) and names == expected['inputs'], (index, 'input order')
        expected_diagnostics = ''.join(value+'\n' for value in expected['diagnostics'])
        assert actual_diagnostics == expected_diagnostics, (index, actual_diagnostics, expected_diagnostics)
        report['cases'].append({'index': index, 'sourceBytes': len(case['source'].encode()),
                                'outputSha256': sha(destination), 'inputCount': len(names),
                                'diagnostics': expected['diagnostics'], 'equal': True})
    report['passed'] = True
finally:
    (args.output/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'passed': True, 'cases': len(cases)}))
