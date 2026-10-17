"""Prepare real installed-metric fixtures; all geometry assertions execute in VKF."""
import json,sys
from pathlib import Path
ref=json.loads(Path(sys.argv[1]).read_text());metrics=json.loads(Path(sys.argv[2]).read_text());out=Path(sys.argv[3])
q=lambda x:json.dumps(x,ensure_ascii=False,separators=(',',':')).replace('$','\\$')
entries=[]
for style,mapping in metrics['maps'].items():
 entries.append(('style/'+style,{k:v for k,v in mapping.items() if k!='symbols'}))
 for key,value in mapping['symbols'].items():
  if key in ['2','@roman:2','@font:mathrm:2','@roman:A','@text:%','@text:bullet','\\bullet']:entries.append(('math/'+style+'/'+key,value))
for role in ['roman','italic','author','titlemark']:
 font=metrics['documentFonts'][role];entries.append(('font/'+role,{k:v for k,v in font.items() if k!='symbols'}))
 for code,glyph in font['symbols'].items():
  if int(code) in [65,97,18,19,20,21,22,23,24,94,95,126,127,76,84,69,88,46,121]:entries.append(('text/'+role+'/'+code,glyph))
s=['test_font_data:.test_font_data','font_catalog:.font_catalog','text_chunks:.text_chunks','fonts():',f'    keys:text_chunks.empty({len(entries)})',f'    values:text_chunks.empty({len(entries)})']
for i,(key,value)in enumerate(entries):s +=[f'    keys.({i}):{q(key)}',f'    values.({i}):{q(json.dumps(value,ensure_ascii=False,separators=(",",":")))}']
s+=['    @:font_catalog.load(test_font_data.pack(keys,values))'];out.with_name('text_native_primitives_reference_fonts.vkf').write_text('\n'.join(s)+'\n')
s=['text_native_primitives:.text_native_primitives','text_parser:.text_parser','math_packages:.math_packages','reference_fonts:.text_native_primitives_reference_fonts','resource_json:.resource_json','close(a:num,b:num)->bit:|a-b|<0.000000001']
for i,c in enumerate(ref):
 s +=[f'case_{i}()->bit:','    fonts:reference_fonts.fonts()',f'    context:text_parser.context({q(c["role"])},["roman","italic","author","titlemark"])',f'    parsed:text_parser.parse({q(c["source"])},fonts,context)',f'    provider:text_native_primitives.provide(parsed.stream,fonts,math_packages.defaults(),{str(c["legacy"]).lower()})','    kinds:provider.kinds','    widths:provider.widths','    heights:provider.heights','    depths:provider.depths','    italics:provider.italics','    scenes:provider.scenes','    messages:provider.diagnostics',f'    (provider.count=1)?! "{c["name"]} resolved exactly once"',f'    (messages.(0)={q(",".join(json.dumps(x,ensure_ascii=False) for x in c["diagnostics"]))})?! "{c["name"]} diagnostics"']
 if not c['nodes']:s +=[f'    (kinds.(0)=5)?! "{c["name"]} resolved empty"']
 else:
  assert len(c['nodes'])==1,c
  n=c['nodes'][0];kind={'box':0,'glue':1,'kern':2}[n['type']];box=n.get('box',n)
  s +=[f'    (kinds.(0)={kind} /\\ close(widths.(0),{float(box["width"])}))?! "{c["name"]} node kind/width"']
  if kind==0:
   s +=[f'    (close(heights.(0),{float(box.get("height",0))}) /\\ close(depths.(0),{float(box.get("depth",0))}) /\\ close(italics.(0),{float(box.get("italic",0))}))?! "{c["name"]} native extents"','    scene:resource_json.parse(scenes.(0))','    items:resource_json.member(scene,0,"items")']
   for li,item in enumerate(box['items']):
    s +=[f'    leaf_{li}:resource_json.element(scene,items,{li})']
    for key,value in item.items():
     if value is None:s +=[f'    (resource_json.member(scene,leaf_{li},{q(key)})>=0)?! "{c["name"]} retained {key}"']
     elif isinstance(value,str):s +=[f'    (text_native_primitives.string(scene,leaf_{li},{q(key)})={q(value)})?! "{c["name"]} leaf {key}"']
     else:s +=[f'    close(text_native_primitives.numeric(scene,leaf_{li},{q(key)}),{float(value)})?! "{c["name"]} leaf {key}"']
  if kind==2:s +=['    breaks:provider.breakable',f'    breaks.(0)?! \"{c["name"]} ordinary kern remains breakable before following glue\"']
  if kind==1:
   s+=['    stretches:provider.stretches','    shrinks:provider.shrinks','    breaks:provider.breakable',f'    (close(stretches.(0),{float(n.get("stretch",0))}) /\\ close(shrinks.(0),{float(n.get("shrink",0))}) /\\ breaks.(0))?! "{c["name"]} exact glue components"']
 s+=['    @:true']
s+=['renderer_tests()->bit:']+[f'    case_{i}()?! "case {i}"' for i in range(len(ref))]+['    @:true','renderer_tests()'];out.write_text('\n'.join(s)+'\n')
