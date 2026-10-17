"""Python3.14 serializes installed ECMAScript Unicode casing/property assets."""
import importlib.util,json,subprocess,sys
from pathlib import Path
assert sys.version_info[:2]==(3,14)
root=Path(__file__).resolve().parent
script=r"""const entries=[],cased=[],ignorable=[];for(let code=0;code<=0x10ffff;code++){if(code>=0xd800&&code<=0xdfff)continue;const c=String.fromCodePoint(code),up=c.toUpperCase(),low=c.toLowerCase();if(up!==c)entries.push(['upper/'+c,up]);if(low!==c)entries.push(['lower/'+c,low]);if(/\p{Cased}/u.test(c))cased.push(code);if(/\p{Case_Ignorable}/u.test(c))ignorable.push(code);}process.stdout.write(JSON.stringify({unicode:process.versions.unicode,entries,cased,ignorable}));"""
data=json.loads(subprocess.run(['node','--input-type=module','-e',script],text=True,capture_output=True,check=True).stdout)
spec=importlib.util.spec_from_file_location('prepare_font_catalog',root/'prepare_font_catalog.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
packed=module.pack(data['entries']).decode()
def ranges(values):
 out=[];first=last=None
 for value in values:
  if last is not None and value==last+1:last=value;continue
  if last is not None:out.append(f'{first:012d}{last:012d}')
  first=last=value
 if last is not None:out.append(f'{first:012d}{last:012d}')
 return ''.join(out)
fields={'version':data['unicode'],'directory':packed,'cased_ranges':ranges(data['cased']),'ignorable_ranges':ranges(data['ignorable'])}
(root/'unicode_case_data.vkf').write_text('# Installed ECMAScript Unicode casing/property data; no document input.\n'+''.join(name+'()->str:'+json.dumps(value,ensure_ascii=False)+'\n' for name,value in fields.items()))
print(json.dumps({'unicode':data['unicode'],'mappings':len(data['entries']),'bytes':len(packed.encode()),'casedRanges':len(fields['cased_ranges'])//24,'ignorableRanges':len(fields['ignorable_ranges'])//24}))
