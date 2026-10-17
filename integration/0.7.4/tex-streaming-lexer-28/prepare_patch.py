"""Build native fixtures from HANDWRITTEN expectations, never model outputs."""
from pathlib import Path
import difflib,json,re
H=Path(__file__).resolve().parent;C=H/'candidate';N=C/'examples/gpu-math/native-vkf'
def string(value):
 # Explicit chr for nonprintable bytes; ordinary VKF literal escapes otherwise.
 if any(ord(c)<32 and c not in '\t\r\n' for c in value):
  return '&'.join('str(chr('+str(ord(c))+'))' if ord(c)<32 and c not in '\t\r\n' else string(c) for c in value)
 return json.dumps(value,ensure_ascii=False).replace('$','\\$')
lines=['# Future real native fixtures. UNCOMPILED/UNEXECUTED; handwritten oracle.','m:.tex_streaming_mouth','',
 'table(raw:str,revision:str="sha256:fixture"):', '    @:(schema:1,revision:revision,ids:["fixture"],versions:[0],texts:[raw],hashes:["'+'a'*64+'"])','',
 'origins(revision:str="sha256:fixture"):', '    @:(revision:revision,occurrence_sources:[0],occurrence_via:[-1],source:[0:0],occurrence:[0:0],start:[0:0],stop:[0:0],role:["":0],definition:[0:0],invocation:[0:0])','']
rows=json.loads((H/'cases.json').read_text());names=[]
for row in rows:
 name='case_'+row['id'].replace('-','_');names.append(name)
 lines += [name+'()->bit:', '    source:table('+string(row['raw'])+')','    trace:origins()','    state:m.open(source,trace,0)','    cats:m.categories()']
 for code,cat in row.get('assign',[]):lines+=['    .cats:m.assign(cats,'+str(code)+','+str(cat)+')']
 lines+=['    step:m.next(source,trace,state,cats)']
 if 'diagnostic' in row:
  lines+=['    (step.diagnostic='+str(row['diagnostic'])+')?! "explicit unsupported diagnostic"','    (step.origins.source.length()=0 /\\ step.state.position=0)?! "diagnostic is transactional"']
 else:
  for i,(kind,category,value) in enumerate(row['tokens']):
   if i:lines+=['    .step:m.next(source,step.origins,step.state,cats)']
   lines+=['    (step.diagnostic=0 /\\ step.token.kind='+str(kind)+' /\\ step.token.category='+str(category)+' /\\ step.token.value='+string(value)+')?! "'+row['id']+' token '+str(i)+'"']
   if 'spans' in row:
    start,stop,prov=row['spans'][i]
    lines+=['    (step.token.start='+str(start)+' /\\ step.token.stop='+str(stop)+' /\\ step.token.provenance='+str(prov)+')?! "exact byte span/provenance"']
    if start==stop:lines+=['    (step.token.origin= -1)?! "virtual EOF has no authored origin"']
  if row['tokens']:lines+=['    .step:m.next(source,step.origins,step.state,cats)']
  lines+=['    (step.diagnostic=0 /\\ step.token.kind=0)?! "true EOF"']
 lines+=['    @:true','']
lines+=['mutation_between_reads()->bit:',r'    source:table("@\\a@b %x")','    trace:origins()','    state:m.open(source,trace,0)','    cats:m.categories()','    first:m.next(source,trace,state,cats)','    (first.token.category=12)?! "default @ other"','    .cats:m.assign(cats,64,11)','    word:m.next(source,first.origins,first.state,cats)','    (word.token.value="a@b" /\\ first.token.category=12)?! "new scan and old token identity"','    .cats:m.assign(cats,37,12)','    percent:m.next(source,word.origins,word.state,cats)','    (percent.token.value="%" /\\ percent.token.category=12)?! "comment category changed between reads"','    (percent.token.origin=2 /\\ percent.origins.start.(0)=0 /\\ percent.origins.start.(1)=1)?! "stable origin IDs"','    (~m.reusable(state,state,m.categories(),cats,trace,trace))?! "category invalidates checkpoint"','    m.reusable(state,state,cats,cats,trace,trace)?! "exact unchanged checkpoint"','    @:true','',
 'reject_endline_assignment():m.assign(m.categories(),13,12)',
 'reject_category5_assignment():m.assign(m.categories(),64,5)',
 'reject_preview()->bit:m.strict_token((kind:1,category:2,value:"}",source: -1,occurrence: -1,start:0,stop:0,origin: -1,provenance:2))','',
 'renderer_tests()->bit:']
for name in names+['mutation_between_reads']:lines+=['    '+name+'()?! "'+name+'"']
lines+=['    @:true','']
# This entry accepts the actual package25 table; installed bytes are never copied
# into this repository. A separately admitted native driver supplies these args.
native_source=(N/'tex_streaming_mouth.vkf').read_text()
lines += [line for line in native_source.splitlines() if line.startswith(('Sources:','Origins:'))]
lines += [
 'installed_first_boundary(table:Sources,trace:Origins,occurrence:int,expected:str,start:int,stop:int)->bit:',
 '    state:m.open(table,trace,occurrence)',
 '    cats:m.categories()',
 '    step:m.next(table,trace,state,cats)',
 '    true?>',
 '        (step.diagnostic=0 /\\ step.token.kind~=0)?! "installed lexical boundary unavailable"',
 '        (step.token.kind=2 /\\ step.token.value~= "par")? @|',
 '        .step:m.next(table,step.origins,step.state,cats)',
 '    (step.token.value=expected /\\ step.token.start=start /\\ step.token.stop=stop)?! "installed exact first control"',
 '    @:true','',
 'reject_stale_source():',
 '    a:table("x")',
 '    before:origins()',
 '    state:m.open(a,before,0)',
 '    b:table("x","sha256:changed")',
 '    after:origins("sha256:changed")',
 '    @:m.next(b,after,state,m.categories())','']

lines += ['renderer_tests()','']
(N/'tex_streaming_mouth_tests.vkf').write_text('\n'.join(lines))
patch=[]
for p in sorted(C.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(C).as_posix();patch.append(f'diff --git a/{rel} b/{rel}\nnew file mode 100644\n')
 patch.extend(difflib.unified_diff([],p.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+rel))
(H/'streaming-mouth.patch').write_text(''.join(patch))
(H/'native-fixtures.json').write_text(json.dumps(dict(executed=False,compiled=False,entry='tex_streaming_mouth_tests.renderer_tests',positive=names+['mutation_between_reads'],negative=[dict(function='reject_endline_assignment',diagnostic='TEX_MOUTH_UNSUPPORTED_CATEGORY_TARGET'),dict(function='reject_category5_assignment',diagnostic='TEX_MOUTH_UNSUPPORTED_CATEGORY_VALUE'),dict(function='reject_preview',diagnostic='TEX_PREVIEW_TOKEN_FORBIDDEN'),dict(function='reject_stale_source',diagnostic='TEX_MOUTH_STALE_SOURCE')],installed_sources='prepare_installed_native.mjs returns exact package25 table/origins plus three calls to installed_first_boundary; fresh admission required',source_only=True),indent=2)+'\n')
