"""Generic installed ICU English primary collation folds; no bibliography input."""
import json,subprocess,importlib.util,sys
from pathlib import Path
assert sys.version_info[:2]==(3,14)
root=Path(__file__).resolve().parent
script=r"""const collator=new Intl.Collator('en',{sensitivity:'base',ignorePunctuation:true}),entries=[],ignorable=[],ascii='`^+<=>|~$0123456789abcdefghijklmnopqrstuvwxyz';
for(let code=128;code<=0x10ffff;code++){if(code>=0xd800&&code<=0xdfff)continue;const c=String.fromCodePoint(code);if(collator.compare(c,'')===0){ignorable.push(code);continue;}let f=c.normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase();if(!f||[...f].some(x=>!ascii.includes(x)))f='';if(!f){for(const candidate of ['ae','oe','ss','th','d','l','o','h','i','n','t','f','s','k','a','e'])if(collator.compare(c,candidate)===0){f=candidate;break;}}if(f&&collator.compare(c,f)===0)entries.push([c,f]);}
process.stdout.write(JSON.stringify({unicode:process.versions.unicode,icu:process.versions.icu,entries,ignorable}));"""
data=json.loads(subprocess.run(['node','--input-type=module','-e',script],text=True,capture_output=True,check=True).stdout)
spec=importlib.util.spec_from_file_location('catalog',root/'prepare_font_catalog.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def ranges(values):
 out=[];start=last=None
 for v in values:
  if last is not None and v==last+1:last=v;continue
  if last is not None:out.append(f'{start:012d}{last:012d}')
  start=last=v
 if last is not None:out.append(f'{start:012d}{last:012d}')
 return ''.join(out)
fields={'unicode':data['unicode'],'icu':data['icu'],'directory':m.pack(data['entries']).decode(),'ignorable':ranges(data['ignorable'])}
(root/'bibliography_collation_data.vkf').write_text('# Generic ICU English primary folds. Unknown primary weights remain explicit.\n'+''.join(k+'()->str:'+json.dumps(v,ensure_ascii=False).replace('$',r'\$')+'\n' for k,v in fields.items()))
print(json.dumps({'mappings':len(data['entries']),'ranges':len(fields['ignorable'])//24,'unicode':data['unicode'],'icu':data['icu']}))
