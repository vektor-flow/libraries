"""Normalize local module aliases in a derivative; leave source files unchanged.

Workaround for the published compiler's module alias identity limitations.
Only direct qualified exported function calls outside strings/comments change;
ambiguous/shadowed bindings remain unchanged and are recorded for review.
"""
from pathlib import Path
import re,json,hashlib,shutil
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-dir',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args()
base=args.source_dir.resolve()
out=args.output_dir.resolve()
assert base!=out and base not in out.parents, 'Place the derivative outside source'
out.mkdir(parents=True,exist_ok=False)
dest=out/'source';dest.mkdir()
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
def mask(s):
 chars=list(s);i=0
 def blank(start,stop):
  for at in range(start,stop):
   if chars[at]!='\n':chars[at]=' '
 while i<len(s):
  if s.startswith('##',i):
   stop=s.find('##',i+2);stop=len(s) if stop<0 else stop+2
   blank(i,stop);i=stop;continue
  if s[i]=='#':
   stop=s.find('\n',i);stop=len(s) if stop<0 else stop
   blank(i,stop);i=stop;continue
  triple=s[i:i+3]
  if triple=='"'*3 or triple==chr(39)*3:
   start=i;i+=3
   while i<len(s):
    if s.startswith(triple,i):i+=3;break
    if triple=='"'*3 and s[i]=='\\':i+=2
    else:i+=1
   blank(start,min(i,len(s)));continue
  if s[i]=='"':
   start=i;i+=1
   while i<len(s):
    c=s[i];i+=1
    if c=='\\' and i<len(s):i+=1;continue
    if c=='"':break
   blank(start,i);continue
  i+=1
 return ''.join(chars)
files={p.name:p.read_text() for p in base.glob('*.vkf')};masked={n:mask(s) for n,s in files.items()}
exports={n:set(re.findall(r'^([A-Za-z_]\w*)\(',s,re.M)) for n,s in masked.items()}
canonical={n:'shared_module_'+n[:-4]+'_'+hashlib.sha256(n.encode()).hexdigest()[:8] for n in files}
all_identifiers=set(re.findall(r'[A-Za-z_]\w*','\n'.join(masked.values())))
assert not (all_identifiers & set(canonical.values()))
report={'baseline':str(base),'files':[],'changedFiles':0,'rewrittenCalls':0,'ambiguousAliases':[]}
for name,source in files.items():
 m=masked[name];imports=list(re.finditer(r'^([A-Za-z_]\w*)\s*:\s*\.([A-Za-z_]\w*)\s*$',m,re.M));replacements=[];file_report={'name':name,'beforeSha256':sha(source),'imports':[]}
 for imp in imports:
  alias,target=imp.group(1),imp.group(2)+'.vkf'
  if target not in files:continue
  bindings=[b.start(1) for b in re.finditer(r'(?<![\w.])('+re.escape(alias)+r')\s*:',m) if b.start(1)!=imp.start(1)]
  functions=[b.start(1) for b in re.finditer(r'^('+re.escape(alias)+r')\(',m,re.M)]
  uses=list(re.finditer(r'(?<![\w.])('+re.escape(alias)+r')\s*\.\s*([A-Za-z_]\w*)',m))
  unknown=[u.group(2) for u in uses if u.group(2) not in exports[target]]
  not_calls=[u.group(2) for u in uses if not re.match(r'\s*[\[(]',m[u.end():])]
  reason=[]
  if bindings:reason.append('possible local/parameter/record-field binding')
  if functions:reason.append('function shares imported alias name')
  if unknown:reason.append('non-function qualified member')
  if not_calls:reason.append('qualified function reference without direct call/specialization')
  item={'alias':alias,'target':target,'canonical':canonical[target],'calls':len(uses),'reasons':reason}
  if reason:
   item.update(bindingOffsets=bindings,functionOffsets=functions,unknownMembers=unknown,nonCallMembers=not_calls)
   report['ambiguousAliases'].append(dict(file=name,**item))
  else:
   replacements.append((imp.start(1),imp.end(1),canonical[target]))
   replacements.extend((u.start(1),u.end(1),canonical[target]) for u in uses)
   report['rewrittenCalls']+=len(uses)
  file_report['imports'].append(item)
 changed=source
 for start,stop,value in sorted(replacements,reverse=True):changed=changed[:start]+value+changed[stop:]
 (dest/name).write_text(changed)
 file_report['afterSha256']=sha(changed);file_report['changed']=changed!=source
 report['changedFiles']+=int(changed!=source);report['files'].append(file_report)
(out/'normalization.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['changedFiles','rewrittenCalls']}|{'ambiguousAliases':len(report['ambiguousAliases']),'files':len(files),'source':str(dest)}))
