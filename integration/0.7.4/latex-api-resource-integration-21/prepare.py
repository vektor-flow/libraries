"""Generate review-only patches in this grant's directory. Never apply to source."""
import difflib, hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
NATIVE=REPO/'examples/gpu-math/native-vkf'
BINDING=Path('/home/viktor/.cache/vkf-s0-runtimes-20261012/Proof/tests/independent-worker-D/iteration301/binding.json')
sha=lambda b:hashlib.sha256(b).hexdigest()
binding=json.loads(BINDING.read_bytes())
lines={row['role']:row['value'] for row in binding['ordered_lines']}
pins={row['path']:row['sha256'] for row in binding['inputs']}
resources={role:{'path':lines[role],'sha256':pins[lines[role]],'bytes':Path(lines[role]).stat().st_size} for role in ['fonts','operators','language']}
for row in resources.values():
    assert sha(Path(row['path']).read_bytes())==row['sha256'], row['path']
roles=lines['ordered_roles_json']
assert sha(roles.encode())==binding['roles_utf8_sha256']
assert len(json.loads(roles))==24
resource_identity=['vkf.latex.resources/1',*[resources[r]['sha256'] for r in ['fonts','operators','language']],binding['roles_utf8_sha256']]
resource_revision='sha256:'+sha(json.dumps(resource_identity,separators=(',',':')).encode())
descriptor={'schema':'vkf.latex.resources/1','source_binding':{'path':str(BINDING),'sha256':sha(BINDING.read_bytes())},'assets':resources,'ordered_roles_json':roles,'ordered_roles_sha256':binding['roles_utf8_sha256'],'resource_revision':resource_revision,'identity_tuple':resource_identity,'portable':False,'native_runtime_verified':False,'failure_policy':'No fallback; missing/unreadable/corrupt assets fail. Root must enforce pre/post hashes; paths do not authenticate content.'}
(HERE/'resource-binding.json').write_text(json.dumps(descriptor,indent=2)+'\n')
candidate=HERE/'candidate';candidate.mkdir(exist_ok=True)
files={}
latex=(NATIVE/'latex.vkf').read_text()
library=(NATIVE/'latex_library.vkf').read_text()
public_signature='source:str,dest:str="",selectable:bit=true,editable:bit=false,files_json:str="{}",job:str="main",entry:str="main.tex",include_layout:bit=true'
files['latex.vkf']=latex+'''\n# Source-only overload; legacy positional resource overload above is unchanged.
# Selected/editable output and destination publication remain explicit errors.
tex2pdf('''+public_signature+'''):
    @:library.tex2pdf_named(source,dest,selectable,editable,files_json,job,entry,include_layout)
'''
files['latex_library.vkf']=library+'''\n# Installation-bound default resources; no caller resource quartet is required.
latex_default_resources:.latex_default_resources
tex2pdf_named('''+public_signature+'''):
    (dest="")?! "latex.tex2pdf: atomic destination publication is not implemented"
    (~(selectable \\/ editable))?! "latex.tex2pdf: authenticated selectable/editable output is not implemented"
    resources:latex_default_resources.load()
    @:tex2pdf(source,resources.fonts,resources.operators,resources.ordered_roles,resources.language,files_json,job,entry,include_layout)
'''
types={line.split(':',1)[0]:line for line in (NATIVE/'document_materialize.vkf').read_text().splitlines() if ':(' in line and not line.startswith(' ')}
quote=lambda x:json.dumps(x,ensure_ascii=False)
files['latex_default_resources.vkf']='''# Generated installation binding from resource-binding.json; NOT portable.
# Root must verify pinned resource bytes before/after native execution.
# No missing/corrupt resource fallback and no project/source defaults.
io:.io
font_catalog:.font_catalog
hyphenation:.hyphenation
text_parser_kernel:.text_parser_kernel
tex_text:.tex_text
'''+types['Catalog']+'\n'+types['Language']+'''
DocumentResources:(fonts:Catalog,operators:str,ordered_roles:[str],language:Language,resource_revision:str)
load()->DocumentResources:
    fonts:font_catalog.load(io.read_text('''+quote(resources['fonts']['path'])+'''))
    operators:io.read_text('''+quote(resources['operators']['path'])+''')
    language:hyphenation.load(io.read_text('''+quote(resources['language']['path'])+'''))
    (fonts.size='''+str(resources['fonts']['bytes'])+''')?! "latex.tex2pdf: default font resource length mismatch"
    (tex_text.byte_length(operators)='''+str(resources['operators']['bytes'])+''')?! "latex.tex2pdf: default operator resource length mismatch"
    (language.size='''+str(resources['language']['bytes'])+''')?! "latex.tex2pdf: default language resource length mismatch"
    ordered_roles:text_parser_kernel.roles('''+quote(roles)+''')
    @:(fonts:fonts,operators:operators,ordered_roles:ordered_roles,language:language,resource_revision:'''+quote(resource_revision)+''')
'''
materialize=(NATIVE/'document_materialize.vkf').read_text()
legacy_render=materialize[materialize.index('render(source:'):]
sig=legacy_render.splitlines()[0].removesuffix(':')
body=legacy_render.splitlines()[1:4]
assert body[0].strip().startswith('result:layout(')
body[0]=body[0].replace('result:layout(', 'result:document_materialize.layout(',1)
files['latex_render_result.vkf']='''# Internal legacy typed transport. Independent module; old render is unchanged.
# Encode the exact document produced by this single layout invocation.
# No provenance authentication, selection encoder, destination or publication.
document_materialize:.document_materialize
document_pdf_bulk:.document_pdf_bulk
'''+''.join(types[name]+'\n' for name in ['Metadata','Catalog','Language','Paint','Payload','Arena','PageDocument','Result'])+'''TypedRenderResult:(pdf:str,layout:Result)
'''+sig+'->TypedRenderResult:\n'+'\n'.join(body)+'''
    @:(pdf:pdf,layout:result)
'''
for name,body in files.items():(candidate/name).write_text(body)
def patch(names):
    out=''
    for name in names:
        rel='examples/gpu-math/native-vkf/'+name
        path=NATIVE/name;before=path.read_text() if path.exists() else ''
        out+=''.join(difflib.unified_diff(before.splitlines(True),files[name].splitlines(True),fromfile='a/'+rel if path.exists() else '/dev/null',tofile='b/'+rel))
    return out
(HERE/'source-api.patch').write_text(patch(['latex.vkf','latex_library.vkf','latex_default_resources.vkf']))
(HERE/'typed-result.patch').write_text(patch(['latex_render_result.vkf']))
inputs=[BINDING,*[Path(x['path']) for x in resources.values()]]
inputs += [NATIVE/name for name in ['latex.vkf','latex_library.vkf','document_materialize.vkf','document_pdf_bulk.vkf','font_catalog.vkf','hyphenation.vkf','text_parser_kernel.vkf','tex_text.vkf','normalize_module_aliases.py','host/latex_source_binding_bridge.mjs','host/latex_operation_binding.mjs','host/latex_source_revision.mjs']]
inputs += [REPO/'integration/0.7.4'/p for p in ['renderer-acceptance-path-19/SOURCE-GAPS.txt','renderer-acceptance-path-19/NEXT-ACCEPTANCE.txt','pdf-api-acceptance/named-syntax.vkf','pdf-api-acceptance/cases.json','pdf-api-acceptance/source.tex']]
compiler=Path('/home/viktor/.cache/vkf-architecture-0136/integration227-capacity01/volume/combined229/source/compiler/native/lowering')
inputs += [compiler/name for name in ['expression_call.cpp','statement_function_definition.cpp','function_lowering.cpp']]
(HERE/'input-pins.json').write_text(json.dumps([{'path':str(p),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in inputs],indent=2)+'\n')
# Future acceptance only. No compiler invocation here.
fixtures=HERE/'native-fixtures';fixtures.mkdir(exist_ok=True)
common='''# FUTURE native fixture; no launch authorized by this proposal.
io:.io
latex:.latex
source:io.read_text(io.read_line())
'''
(fixtures/'direct-legacy-parity.vkf').write_text(common+'''latex_default_resources:.latex_default_resources
latex_render_result:.latex_render_result
files:io.read_text(io.read_line())
resources:latex_default_resources.load()
named:latex.tex2pdf(source,editable:false,files_json:files,selectable:false)
legacy:latex.tex2pdf(source,resources.fonts,resources.operators,resources.ordered_roles,resources.language,files)
typed:latex_render_result.render(source,resources.fonts,resources.operators,resources.ordered_roles,resources.language,files)
(named.complete /\\ legacy.complete /\\ typed.layout.complete)?! "render incomplete"
(named.pdf=legacy.pdf /\\ typed.pdf=legacy.pdf)?! "legacy PDF bytes changed"
(named.layout_json=legacy.layout_json /\\ typed.layout.layout_json=legacy.layout_json)?! "legacy layout changed"
(typed.layout.document.page_count=typed.layout.page_count)?! "typed page count changed"
io.print("direct named/legacy/typed parity passed")
''')
cases=[{'id':'direct-legacy-parity','file':'direct-legacy-parity.vkf','expected':'complete; exact original40 PDF hash/40 pages/430 blocks and full layout equality; typed result requires real transport inspection','executed':False}]
rejects={
 'default-selected':'latex.tex2pdf(source)',
 'selected':'latex.tex2pdf(source,selectable:true,editable:false)',
 'editable-implies-selected':'latex.tex2pdf(source,selectable:false,editable:true)',
 'both-selected':'latex.tex2pdf(source,selectable:true,editable:true)',
 'destination':'latex.tex2pdf(source,dest:"must-remain-sentinel.pdf",selectable:false,editable:false)',
 'default-with-destination':'latex.tex2pdf(source,dest:"must-remain-sentinel.pdf")'}
for name,call in rejects.items():
    (fixtures/(name+'.vkf')).write_text(common+'result:'+call+'\n(false)?! "UNEXPECTED unsupported API succeeded"\n')
    cases.append({'id':name,'file':name+'.vkf','expected':'explicit unsupported error; no resource read/render/publication; destination sentinel unchanged','executed':False})
(fixtures/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
print(json.dumps({'proposal_files':len(files),'patches':2,'resource_bytes':sum(x['bytes'] for x in resources.values()),'native_executed':False}))
