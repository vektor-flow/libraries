"""Stage the independent typing/document runtime and its prepared font profiles.

No font generation, source compilation, network access or reference PDF input.
The output directory must be new, preserving earlier snapshots and receipts.
"""
import argparse,hashlib,json,posixpath,re,shutil
from pathlib import Path

def stage(output):
 root=Path(__file__).resolve().parent;demo=root/'typing-demo'
 if output.exists():raise ValueError('Output directory already exists')
 shutil.copytree(demo,output);shutil.copytree(root/'latex-modules',output/'latex-modules')
 queue=[('demo.mjs',demo/'demo.mjs'),('document-demo.mjs',demo/'document-demo.mjs')];seen=set()
 while queue:
  logical,source=queue.pop()
  if logical in seen:continue
  if logical.startswith('../')or logical.startswith('/'):raise ValueError('Runtime dependency escapes output')
  seen.add(logical);target=output/logical;target.parent.mkdir(parents=True,exist_ok=True)
  if source.resolve()!=target.resolve():shutil.copy2(source,target)
  for dependency in re.findall(r'''['"](\./[^'"\n]+\.mjs)['"]''',source.read_text()):
   name=posixpath.normpath(posixpath.join(posixpath.dirname(logical),dependency));candidate=source.parent/dependency
   if not candidate.is_file():candidate=root/name
   if not candidate.is_file():raise ValueError('Missing runtime dependency: '+name)
   queue.append((name,candidate))
 hashes={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest()for p in output.rglob('*')if p.is_file()}
 (output/'runtime-manifest.json').write_text(json.dumps({'files':hashes,'runtimeModules':sorted(seen)},indent=2)+'\n')
 return {'output':str(output),'files':len(hashes),'runtimeModules':len(seen)}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);args=parser.parse_args();print(json.dumps(stage(args.output)))
