"""Prepare typed VKF assertions from the instrumented, unmodified JS page flow."""
import json,sys
from pathlib import Path
cases=json.loads(Path(sys.argv[1]).read_text())
lines=['document_pages:.document_pages','close(a:num,b:num)->bit:|a-b|<0.0000001']
def num(x):return repr(float(x))
def literal(x):return json.dumps(x,ensure_ascii=True) if isinstance(x,str) else ('true' if x is True else 'false' if x is False else num(x))
for ci,case in enumerate(cases):
 cfg=case['config'];ams=case['name'].startswith('ams');caps=case['captures'];bc=max(c['blockIndex'] for c in caps)+1
 lines += [f'case_{ci}()->bit:',f'    config:document_pages.settings({",".join(num(cfg[k]) for k in ["paperWidth","paperHeight","left","top","textWidth","textHeight","lineHeight","fontSize"])},{str(ams).lower()})']
 for k in ['maxDepth','lineSkipLimit','displaySkip','shortDisplaySkip','footnoteSkip','footnoteLeading']:
  if k in cfg: lines+=[f'    .config:document_pages.with_number(config,{json.dumps({"maxDepth":"max_depth","lineSkipLimit":"line_skip_limit","displaySkip":"display_skip","shortDisplaySkip":"short_display_skip","footnoteSkip":"footnote_skip","footnoteLeading":"footnote_leading"}[k])},{num(cfg[k])})']
 for key,value in cfg.get('penalties',{}).items():lines +=[f'    .config:document_pages.with_penalty(config,{json.dumps(key)},{int(value)})']
 lines += [f'    blocks:document_pages.empty_blocks({bc})']
 for bi in range(bc): lines +=[f'    .blocks:document_pages.with_block_kinds(blocks,{bi},"pagebreak")']
 linecount=sum(len(c['box']['lines']) for c in caps)
 lines +=[f'    metrics:document_pages.empty_lines({linecount})']
 fields={k:[] for k in ['scenes','source_lines','heights','depths','natural_depths','widths','indents','baselines','flagged']}
 expected=[];offset=0
 for cap in caps:
  b=cap['block'];context=b.get('context',{});kind=b['kind'];bi=cap['blockIndex'];box=cap['box'];ls=box['lines'];unit=cap['unit'];settings={'kinds':kind,'contexts':json.dumps({'placement':b.get('placement','tbp')}) if kind=='figure' else context.get('kind',''),'firsts':offset,'counts':len(ls),'widths':box['width'],'units':unit,'lefts':context.get('left',0),'rights':context.get('right',0),'indents':context.get('indent',0),'before':cap['before'],'before_shrink':cap['beforeShrink'],'before_stretch':cap['beforeStretch'],'after':0,'leading':context.get('lineHeight',cfg['lineHeight'])*({'title':1.73,'section':1.44,'subsection':1.2}.get(kind,1)),'centered':context.get('align',cfg.get(kind,{}).get('align'))=='center','single_display':b.get('singleDisplay',False),'from_paragraph':b.get('fromParagraph',False),'paragraph_after_display':context.get('paragraphAfterDisplay',False),'no_indent_after_list':context.get('noIndentAfterList',False),'keep_display':cap['keepDisplay'],'baseline_leading':cfg.get(kind,{}).get('lineHeight',0),'after_display':context.get('afterDisplay',False),'center_awaiting':context.get('centerAwaiting',False)}
  if kind in ['section','subsection'] and context.get('afterDisplay'):settings['before']=cfg.get(kind,{}).get('before',12*72/72.27)
  if context.get('listEndAfterDisplay'):
   m=context['listEndAfterDisplay'];settings.update(list_end_display=True,list_parsep=m['parsep'],list_top=m['top'],list_parsep_shrink=m['parsepShrink'],list_parsep_stretch=m['parsepStretch'],list_top_shrink=m['topShrink'],list_top_stretch=m['topStretch'])
  if kind in ['section','subsection','title','author']:settings['after']=cfg.get(kind,{}).get('after',8*72/72.27)
  if box.get('lastRow'): settings.update(has_last_row=True,last_row_baselines=box['lastRow']['baseline'],last_row_depths=box['lastRow']['depth'])
  for key,value in settings.items():lines +=[f'    .blocks:document_pages.with_block_{key}(blocks,{bi},{(str(int(value)) if key in ["firsts","counts","baseline_modes"] else literal(value))})']
  for li,m in enumerate(ls):
   fields['scenes'].append(offset+li);fields['source_lines'].append(li)
   for key,js,default in [('heights','height',0),('depths','depth',0),('natural_depths','naturalDepth',m['depth']),('widths','width',box['width']),('indents','indent',0),('baselines','baseline',0),('flagged','flagged',False)]:fields[key].append(m.get(js,default))
   found=None
   for pi,page in enumerate(case['pages']):
    for item in page['items']:
     if item['pageProbeBlock']==bi and item['pageProbeLine']==li and item['kind'] not in ['link'] and not item.get('equationTag'):
      found=(pi,item['x']-item['pageProbeSourceX']*unit,item['y']-item['pageProbeSourceY']*unit);break
    if found:break
   if not found:raise ValueError((case['name'],bi,li,'no item'))
   expected.append((bi,li,*found,{'top':3,'bottom':4,'page':5}.get(item.get('floatPlacement'),0),fields['scenes'][-1]))
  offset+=len(ls)
 for key,values in fields.items():
  factory='bits' if key=='flagged' else 'ints' if key in ['scenes','source_lines'] else 'zeros'
  lines +=[f'    {key}:document_pages.{factory}({len(values)})']
  for vi,value in enumerate(values):
   text=literal(value) if key=='flagged' else str(int(value)) if key in ['scenes','source_lines'] else num(value)
   lines +=[f'    {key}.({vi}):{text}']
  lines +=[f'    metrics.{key}:{key}']
 lines +=['    result:document_pages.layout(config,blocks,metrics,document_pages.empty_notes(0),document_pages.empty_markers(0))',f'    (result.complete={str(not case["diagnostics"]).lower()} /\\ result.pages.count={len(case["pages"])} /\\ result.placements.count={linecount})?! "{case["name"]} page and line count"','    placements:result.placements','    ps:placements.pages','    xs:placements.xs','    ys:placements.ys','    kinds:placements.kinds','    placed_scenes:placements.scenes']
 order=[]
 for page in case['pages']:
  for item in page['items']:
   key=(item['pageProbeBlock'],item['pageProbeLine'])
   if key not in order:order.append(key)
 expected.sort(key=lambda e:order.index(e[:2]))
 for i,(bi,li,page,x,y,kind,scene) in enumerate(expected):lines +=[f'    (ps.({i})={page} /\\ kinds.({i})={kind} /\\ placed_scenes.({i})={scene} /\\ close(xs.({i}),{num(x)}) /\\ close(ys.({i}),{num(y)}))?! "{case["name"]} line {i} exact JS placement"']
 lines+=['    @:true']
lines += ['renderer_tests()->bit:']+[f'    case_{ci}()?! "case {ci}"' for ci in range(len(cases))]+['    @:true','renderer_tests()']
Path(sys.argv[2]).write_text('\n'.join(lines)+'\n')
