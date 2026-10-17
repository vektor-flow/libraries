"""Qualify a VKF compiler swap against a frozen renderer; never benchmark it.

Python 3.14 is required for execution. Preparation records an inspectable plan
without invoking either compiler. A failed execution requires a fresh output.
Fresh-LaTeX geometry and honest cold/warm/edit benchmarks remain separate gates.
"""
from __future__ import annotations
import argparse
import datetime
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DEFAULT_CASES = Path('/mnt/development/CuvamiLaTeX/native-documents-073-06/commands.json')
SUITES = [
    'string_vector_contract_tests', 'text_chunks_tests', 'text_chunks_linear_tests',
    'text_parser_stream_access_tests', 'document_scene_tests',
    'document_scene_flat_tests', 'document_scene_paragraph_linear_tests',
    'document_scene_paragraph_linear_reference_tests', 'document_scene_export_tests',
    'document_pdf_bulk_tests', 'text_math_boxes_canonical_tests',
    'document_materialize_output_typed_tests', 'document_materialize_output_bulk_tests',
    'document_scene_paragraph_columns_tests', 'document_pages_prefix_tests',
    'document_scene_sources_tests', 'tex_text_span_tests',
    'text_parser_stream_fields_tests',
    'paragraph_font_scalar_tests',
    'math_draw_root_tests', 'document_gpu_rows_tests',
]
INPUT_OPTIONS = ('--source', '--files', '--fonts', '--operators', '--metrics', '--language')
PACKAGE_FILES = ('playground/canonical/compiler.mjs', 'playground/canonical/compiler.wasm',
                 'playground/canonical/compiler.data', 'vf-ui/vf-symbolic-kernel-runtime.mjs')


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2) + '\n')


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def option(argv, name):
    if argv.count(name) != 1 or argv.index(name) + 1 >= len(argv):
        raise ValueError(f'Expected exactly one {name} value: {argv}')
    return argv[argv.index(name) + 1]


def replace(argv, name, value):
    option(argv, name)
    argv[argv.index(name) + 1] = str(value)


def checked(command, *, cwd, stdout, stderr, timeout=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    with stdout.open('w') as out, stderr.open('w') as err:
        process = subprocess.Popen(list(map(str, command)), cwd=cwd, env=env,
                                   stdout=out, stderr=err, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=2)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            raise
    if code:
        raise RuntimeError(f'Command failed ({code}); see {stderr}: {command}')


def snapshot(destination):
    """Copy source/reference code, excluding generated and dependency trees."""
    base = ROOT.parent
    allowed = {'.vkf', '.py', '.mjs', '.js', '.json', '.wgsl'}
    for directory, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in
                   {'node_modules', '.git', '.vkfbuild', '__pycache__', '.venv', 'venv'}
                   and not d.startswith('.')]
        for name in files:
            source = Path(directory) / name
            if source.suffix not in allowed:
                continue
            target = destination / source.relative_to(base)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def patch_factory(source, output):
    before = source.read_text()
    marker = 'empty(capacity:int)->[str]:\n'
    start = before.index(marker)
    stop = before.index('\njoin(', start)
    guards = ('    (capacity%1=0)?!\n'
              '    (capacity>=0)?!\n'
              '    (capacity<=536870909)?!\n')
    if not before[start + len(marker):].startswith(guards):
        raise ValueError('Unknown text_chunks.empty guards; refusing a speculative mode patch')
    after = before[:start] + marker + guards + '    @:["":capacity]\n' + before[stop:]
    output.mkdir()
    (output / 'text_chunks.before.vkf').write_text(before)
    (output / 'text_chunks.after.vkf').write_text(after)
    (output / 'text_chunks.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile='before/text_chunks.vkf', tofile='after/text_chunks.vkf')))
    source.write_text(after)
    return dict(mode='native-string-vectors', beforeSha256=hashlib.sha256(before.encode()).hexdigest(),
                afterSha256=sha(source), patch=str(output / 'text_chunks.patch'),
                canonicalRepositoryEdited=False)


def wasm_runner(path):
    path.write_text(r'''import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const [adapter,pkg,source,out,mode,casePath,nativePath]=process.argv.slice(2);
const {compileBrowserKernel}=await import(pathToFileURL(adapter));
const entry=mode==='unit'?'renderer_tests':'render_document';
const entryCall=mode==='unit'?'::renderer_tests()':'::render_document("", "", "", "", "[]")';
const report={passed:false,compiled:false,rendered:false,performanceValidated:false,fullReachableSharedCore:mode==='document',mode};
try {
 const built=await compileBrowserKernel({packageRoot:pkg,source,output:out,entry,entryCall});
 report.compiled=true;
 const {createSymbolicKernel}=await import(pathToFileURL(pkg+'/vf-ui/vf-symbolic-kernel-runtime.mjs'));
 const {instance}=await WebAssembly.instantiate(built.wasm);
 const kernel=createSymbolicKernel({instance,manifest:built.manifest});
 if(mode==='unit') {
  report.results=[];
  for(let i=0;i<3;i++) { const value=kernel.invokeValue(entry,[]);report.results.push(value);if(value!==true)throw Error('VKF contract/assertions returned '+value); }
 } else {
  const c=JSON.parse(await readFile(casePath,'utf8'));
  const args=await Promise.all([c.source,c.fonts,c.operators,c.language].map(p=>readFile(p,'utf8')));
  args.push(c.roles,c.files?await readFile(c.files,'utf8'):'{}',c.job??'main',c.entry??'main.tex');
  const raw=kernel.invokeValue(entry,args);
  if(typeof raw!=='string')throw Error('render_document did not return a serialized result');
  const value=JSON.parse(raw);report.rendered=true;await writeFile(out+'/result.json',JSON.stringify(value));
  const pdf=value.pdf??'';await writeFile(out+'/document.pdf',pdf,'utf8');
  if(value.complete!==true||!Array.isArray(value.diagnostics)||value.diagnostics.length||!Array.isArray(value.unresolved)||value.unresolved.length||!(value.pageCount>0)||!pdf.startsWith('%PDF-1.7')||value.pdfBytes!==Buffer.byteLength(pdf,'utf8'))throw Error('Incomplete/invalid shared-core document');
  const native=await readFile(nativePath);const bytes=Buffer.from(pdf,'utf8');
  if(!bytes.equals(native))throw Error('WASM/native PDF bytes differ for the same frozen case');
  report.pageCount=value.pageCount;report.pdfBytes=value.pdfBytes;report.nativePdfByteIdentical=true;
  report.pdfSha256=createHash('sha256').update(bytes).digest('hex');
 }
 report.passed=true;
} catch(error) {report.error=String(error?.stack??error);}
// compileBrowserKernel creates out only after a successful compile.
const {mkdir}=await import('node:fs/promises');await mkdir(out,{recursive:true});
await writeFile(out+'/verification.json',JSON.stringify(report,null,2)+'\n');
if(!report.passed)process.exitCode=1;
''')


def prepare(args):
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'state.json', dict(status='preparing', passed=False, startedExecution=False))
    original = out / 'snapshot' / 'gpu-math'
    snapshot(original)
    native = original / 'native-vkf'
    for required in ('native_document_cli.vkf', 'document_render_kernel.vkf',
                     'verify.py', 'verify_native_document.py', 'compile_browser_kernel.mjs'):
        if not (native / required).is_file():
            raise FileNotFoundError(f'Required frozen renderer entry/adapter missing: {required}')
    for suite in SUITES:
        if not (native / (suite + '.vkf')).is_file():
            raise FileNotFoundError(f'Required affected suite missing: {suite}')
    factory = dict(mode='portable-doubling', canonicalRepositoryEdited=False)
    if args.native_string_vectors:
        factory = patch_factory(native / 'text_chunks.vkf', out / 'mode-patch')
    normalized = out / 'normalized'
    checked([sys.executable, native / 'normalize_module_aliases.py', '--source-dir', native,
             '--output-dir', normalized], cwd=out, stdout=out / 'normalization.stdout',
            stderr=out / 'normalization.stderr')
    code = normalized / 'source'
    shutil.copy2(native / 'verify.py', code / 'verify.py')
    saved = json.loads(args.cases.read_text())
    if not isinstance(saved, list) or not saved:
        raise ValueError('Cases must be a nonempty list of [name, argv] entries')
    inputs = out / 'inputs'; inputs.mkdir()
    captured = {}
    input_manifest = {}

    def capture(value):
        source = Path(value).resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        key = str(source)
        if key not in captured:
            digest = sha(source)
            target = inputs / (digest + '-' + source.name)
            if not target.exists():
                shutil.copy2(source, target)
            captured[key] = str(target)
            input_manifest[str(target)] = dict(original=key, sha256=digest)
        return captured[key]

    cases = []
    names = set()
    binary = out / 'native' / 'native-document-cli'
    for item in saved:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError('Case entry must be [name, argv]')
        name, argv = item
        if not isinstance(name, str) or not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name) or name in names:
            raise ValueError(f'Invalid/duplicate case name: {name!r}')
        names.add(name)
        if not isinstance(argv, list) or len(argv) < 2 or any(not isinstance(x, str) for x in argv) or Path(argv[1]).name != 'verify_native_document.py':
            raise ValueError(f'Unrecognized saved correctness command: {name}')
        cmd = [sys.executable, str(native / 'verify_native_document.py'), *argv[2:]]
        replace(cmd, '--binary', binary)
        replace(cmd, '--output', out / 'documents' / name)
        for flag in INPUT_OPTIONS:
            if flag in cmd:
                replace(cmd, flag, capture(option(cmd, flag)))
        cases.append(dict(name=name, command=cmd, original40=name.lower() == 'original40'))
    cases.sort(key=lambda c: c['original40'])
    small = [c for c in cases if not c['original40']]
    if not small:
        raise ValueError('At least one small correctness case is required for the full WASM shared-core gate')
    wasm_runner(out / 'run-wasm.mjs')
    selected = small[0]
    c = selected['command']
    metrics = json.loads(Path(option(c, '--metrics')).read_text())
    config = {name: option(c, '--' + name) for name in ('source', 'fonts', 'operators', 'language')}
    config['roles'] = json.dumps(list(metrics['documentFonts']))
    for name in ('files', 'job', 'entry'):
        if '--' + name in c:
            config[name] = option(c, '--' + name)
    write(out / 'wasm-document-case.json', config)
    steps = [dict(name='compiler-version', command=[str(args.compiler), '-v'])]
    for suite in SUITES:
        steps.append(dict(name='native-' + suite, command=[sys.executable, str(code / 'verify.py'),
            '--compiler', str(args.compiler), '--output', str(out / 'native-units' / suite),
            '--suite', suite, '--build-timeout', str(args.build_timeout)],
            verification=str(out / 'native-units' / suite / 'verification.json')))
        steps.append(dict(name='wasm-' + suite, command=['node', str(out / 'run-wasm.mjs'),
            str(native / 'compile_browser_kernel.mjs'), str(args.browser_package),
            str(code / (suite + '.vkf')), str(out / 'wasm-units' / suite), 'unit'],
            verification=str(out / 'wasm-units' / suite / 'verification.json')))
    steps.append(dict(name='native-cli-build', command=[str(args.compiler), '-b',
        str(code / 'native_document_cli.vkf'), '-o', str(binary), '--diagnostics'],
        binary=str(binary)))
    for case in small:
        steps.append(dict(name='document-' + case['name'], command=case['command'],
            verification=str(out / 'documents' / case['name'] / 'verification.json')))
    steps.append(dict(name='wasm-full-shared-core-small', command=['node', str(out / 'run-wasm.mjs'),
        str(native / 'compile_browser_kernel.mjs'), str(args.browser_package),
        str(code / 'document_render_kernel.vkf'), str(out / 'wasm-document'), 'document',
        str(out / 'wasm-document-case.json'), str(out / 'documents' / selected['name'] / 'document.pdf')],
        verification=str(out / 'wasm-document' / 'verification.json')))
    for case in cases:
        if case['original40']:
            steps.append(dict(name='document-' + case['name'], command=case['command'],
                verification=str(out / 'documents' / case['name'] / 'verification.json')))
    provenance = dict(compiler=dict(path=str(args.compiler), sha256=sha(args.compiler)),
        browserPackage=dict(path=str(args.browser_package), files={n:sha(args.browser_package / n) for n in PACKAGE_FILES}),
        cases=dict(path=str(args.cases), sha256=sha(args.cases)), inputs=input_manifest,
        sourceHashes={str(p.relative_to(out)):sha(p) for p in original.rglob('*') if p.is_file()},
        normalizedHashes={str(p.relative_to(out)):sha(p) for p in code.iterdir() if p.is_file()},
        python=sys.version, factoryMode=factory,
        adapterHashes={'run-wasm.mjs':sha(out / 'run-wasm.mjs')},
        packageMetadata={n:json.loads((args.browser_package / n).read_text()) for n in ('UPSTREAM.json', 'CUVAMI-ACCEPTANCE.json') if (args.browser_package / n).is_file()})
    write(out / 'provenance.json', provenance)
    plan = dict(schema=1, output=str(out), compiler=str(args.compiler), browserPackage=str(args.browser_package),
        factoryMode=factory['mode'], steps=steps, nativeCases=[c['name'] for c in cases],
        includesOriginal40=any(c['original40'] for c in cases), performanceValidated=False, freshLaTeXValidated=False,
        wasmDocumentScope='full reachable shared core, first small case; exact PDF comparison with fresh native output',
        requiredLater=['fresh exact-source LaTeX glyph geometry (including constituent glyphs/diagrams)',
                       'separate uncached cold, warm, and small-local-edit benchmarks'],
        noCacheEviction=True, noRecoveredArtifactPass=True)
    write(out / 'plan.json', plan)
    write(out / 'state.json', dict(status='prepared', passed=False, startedExecution=False,
                                  performanceValidated=False, freshLaTeXValidated=False,
                                  planSha256=sha(out / 'plan.json'), provenanceSha256=sha(out / 'provenance.json')))
    (out / 'README.txt').write_text('Prepared compiler qualification, NOT a renderer acceptance or timing result.\n'
        'Inspect plan.json and provenance.json. Execute this exact prepared snapshot with the same arguments plus --execute-prepared.\n'
        'Execution stops at the first failed command/assertion, including the direct string-vector contract.\n'
        'No failed-build artifact is recovered or accepted; failed runs require a NEW output directory.\n'
        'Full WASM shared-core execution covers the first small case only; original40 native correctness remains last.\n'
        'A PASS still requires separate fresh-LaTeX constituent-glyph geometry/diagram validation and honest cold/warm/local-edit benchmarks.\n'
        'No timings, cache eviction, compiler installation, or repository renderer edits occur here.\n')
    return plan


def execute(args, plan):
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError('Execution requires Python 3.14 (reference drivers enforce the same version)')
    out = args.output
    provenance = json.loads((out / 'provenance.json').read_text())
    if sha(args.compiler) != provenance['compiler']['sha256']:
        raise RuntimeError('Compiler changed after preparation')
    for name, digest in provenance['browserPackage']['files'].items():
        if sha(args.browser_package / name) != digest:
            raise RuntimeError('Browser package changed after preparation: ' + name)
    for group in ('sourceHashes', 'normalizedHashes', 'adapterHashes'):
        for name, digest in provenance[group].items():
            if sha(out / name) != digest:
                raise RuntimeError('Frozen source changed after preparation: ' + name)
    for name, data in provenance['inputs'].items():
        if sha(Path(name)) != data['sha256']:
            raise RuntimeError('Frozen case input changed after preparation: ' + name)
    logs = out / 'logs'; logs.mkdir()
    (out / 'native').mkdir()
    state = dict(status='running', passed=False, startedExecution=True, startedUtc=now(),
                 performanceValidated=False, freshLaTeXValidated=False, completedSteps=[])
    write(out / 'state.json', state)
    try:
        for index, step in enumerate(plan['steps']):
            state['currentStep'] = step['name']; write(out / 'state.json', state)
            stdout = logs / f'{index:02d}-{step["name"]}.stdout'
            stderr = logs / f'{index:02d}-{step["name"]}.stderr'
            if 'binary' in step and Path(step['binary']).exists():
                raise RuntimeError('Refusing a preexisting/recovered compiler artifact')
            if 'verification' in step and Path(step['verification']).parent.exists():
                raise RuntimeError('Refusing a preexisting/recovered verification directory')
            checked(step['command'], cwd=out, stdout=stdout, stderr=stderr,
                    timeout=args.build_timeout if step['name'] == 'native-cli-build' else args.step_timeout)
            if 'verification' in step:
                result = json.loads(Path(step['verification']).read_text())
                if result.get('passed') is not True:
                    raise RuntimeError('Verification did not explicitly pass: ' + step['name'])
            if step['name'] == 'compiler-version':
                state['compilerVersion'] = stdout.read_text().strip()
                state['compilerVersionStderr'] = stderr.read_text().strip()
            receipt = dict(name=step['name'], command=step['command'], exitCode=0,
                           stdout=str(stdout), stderr=str(stderr))
            if 'binary' in step:
                binary = Path(step['binary'])
                if not binary.is_file() or not binary.stat().st_size:
                    raise RuntimeError('Successful build did not create a fresh binary')
                receipt.update(binarySha256=sha(binary), binaryBytes=binary.stat().st_size)
            state['completedSteps'].append(receipt); write(out / 'state.json', state)
        state.update(status='passed', passed=True, finishedUtc=now(), requiredLater=plan['requiredLater'],
                     nativeCases=plan['nativeCases'], includesOriginal40=plan['includesOriginal40'], wasmDocumentScope=plan['wasmDocumentScope'])
    except BaseException as error:
        state.update(status='failed', passed=False, error=repr(error), finishedUtc=now())
        raise
    finally:
        write(out / 'state.json', state)
        write(out / 'qualification.json', state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--browser-package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=DEFAULT_CASES)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--prepare-only', '--dry-run', action='store_true',
                       help='Snapshot and normalize sources/inputs, write exact plan; run no compiler or renderer')
    modes.add_argument('--execute-prepared', action='store_true', help='Execute an untouched prepared output exactly once')
    parser.add_argument('--native-string-vectors', action='store_true',
                       help='Candidate-only frozen derivative: replace text_chunks.empty with guarded direct repeat')
    parser.add_argument('--build-timeout', type=int, default=3600)
    parser.add_argument('--step-timeout', type=int, default=3600)
    args = parser.parse_args()
    for name in ('compiler', 'browser_package', 'output', 'cases'):
        setattr(args, name, getattr(args, name).expanduser().resolve())
    if args.output == ROOT.parent or ROOT.parent in args.output.parents:
        parser.error('All generated artifacts must be outside the renderer source tree')
    if not args.compiler.is_file() or not os.access(args.compiler, os.X_OK):
        parser.error('--compiler must name an executable file')
    if not args.cases.is_file():
        parser.error('--cases must name saved correctness commands')
    for name in PACKAGE_FILES:
        if not (args.browser_package / name).is_file():
            parser.error('Incomplete browser package: ' + name)
    if args.build_timeout <= 0 or args.step_timeout <= 0:
        parser.error('Timeouts must be positive')
    if args.execute_prepared:
        state = json.loads((args.output / 'state.json').read_text())
        plan = json.loads((args.output / 'plan.json').read_text())
        expected = 'native-string-vectors' if args.native_string_vectors else 'portable-doubling'
        if state.get('status') != 'prepared' or state.get('startedExecution') is not False:
            parser.error('Only an untouched prepared output can execute; failed/partial runs require a new output')
        if sha(args.output / 'plan.json') != state['planSha256'] or sha(args.output / 'provenance.json') != state['provenanceSha256']:
            parser.error('Prepared plan/provenance changed; prepare a fresh output')
        if plan['output'] != str(args.output) or plan['compiler'] != str(args.compiler) or plan['browserPackage'] != str(args.browser_package) or plan['factoryMode'] != expected:
            parser.error('Prepared compiler/package/factory mode differs from these arguments')
    else:
        try:
            plan = prepare(args)
        except BaseException as error:
            state_path = args.output / 'state.json'
            if state_path.exists() and json.loads(state_path.read_text()).get('status') == 'preparing':
                write(state_path, dict(status='prepare-failed', passed=False, startedExecution=False, error=repr(error)))
            raise
    if args.prepare_only:
        print(json.dumps(dict(prepared=True, executed=False, passed=False, plan=str(args.output / 'plan.json'), performanceValidated=False)))
        return
    execute(args, plan)
    print(json.dumps(dict(passed=True, qualification=str(args.output / 'qualification.json'), performanceValidated=False, freshLaTeXValidated=False)))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Compiler qualification failed: {error}', file=sys.stderr)
        raise SystemExit(1)
