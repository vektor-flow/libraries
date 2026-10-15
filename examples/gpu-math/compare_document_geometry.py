"""Dev-only glyph/figure placement oracle from PDF vector traces; no registration.

The independent renderer never consumes these traces. Matching uses font/glyph
identity and a one-to-one minimum-distance assignment on each original page.
"""
import json,math,os,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.optimize import linear_sum_assignment
from fontTools.t1Lib import T1Font
from fontTools.tfmLib import TFM

def compare_geometry(pdf,layout,data,trace_path,extras=None):
 subprocess.run(['mutool','draw','-F','trace','-o',str(trace_path),str(pdf)],capture_output=True,check=True)
 pages=ET.parse(trace_path).getroot().findall('page');font_cache={};env=os.environ.copy()
 if extras:
  for name in ['TFMFONTS','T1FONTS']:env[name]=str(extras.resolve())+'//:'
 def font(name):
  if name not in font_cache:
   paths=[subprocess.run(['kpsewhich',name+ext],capture_output=True,text=True,env=env).stdout.strip()for ext in ['.pfb','.tfm']]
   font_cache[name]=(T1Font(paths[0])if paths[0]else None,TFM(paths[1])if paths[1]else None)
  return font_cache[name]
 def native_identity(name,glyph):
  name=name.split('+')[-1].lower()
  return ('bitmap',glyph)if re.fullmatch('f[0-9]+',name)and glyph.isdigit()else(name,glyph)
 def actual(item):
  key=item['key'];style,token=key.split('/',1);symbol=data['maps'][style]['symbols'].get(token)
  if token.startswith('@document:'):
   _,role,code=token.split(':');symbol=data['documentFonts'][role]['symbols'][code]
  if not symbol:return None
  if 'glyphParts'in symbol:parts=symbol['glyphParts']
  elif symbol.get('fontName')is not None and symbol.get('fontCode')is not None:parts=[{**symbol,'x':0,'y':0}]
  else:return None
  records=[]
  for part in parts:
   name=part['fontName'];code=part['fontCode'];type1,tfm=font(name)
   identity=(name,type1['Encoding'][code])if type1 else('bitmap',str(code))
   size=part.get('fontSize')or(part['advance']/tfm.chars[code]['width']if tfm and part.get('advance')else None)
   sx=item.get('sx',1);sy=item.get('sy',1)
   records.append({'identity':identity,'x':item['x']+part['x']*sx,'y':item['y']+part['y']*sy,'size':size*sx if size else None,'key':key})
  return records

 records=[]
 for index in range(max(len(pages),len(layout['pages']))):
  expected=[];gpu=[];unknown=[];figures=[];actual_figures=[];unsupported=[]
  if index<len(pages):
   for text in pages[index].iter('fill_text'):
    transform=[float(n)for n in text.get('transform','1 0 0 1 0 0').split()];aa,bb,cc,dd,ee,ff=transform
    for span in text.findall('span'):
     trm=[float(n)for n in span.get('trm').split()];size=math.hypot(trm[0],trm[1])*math.hypot(aa,bb)
     for g in span.findall('g'):
      if'glyph'not in g.attrib:continue # Extra Unicode codepoints of one ligature.
      x,y=float(g.get('x')),float(g.get('y'));expected.append({'identity':native_identity(span.get('font'),g.get('glyph')),'x':aa*x+cc*y+ee,'y':bb*x+dd*y+ff,'size':size,'unicode':g.get('unicode')})
   for image in pages[index].iter('fill_image'):
    t=[float(n)for n in image.get('transform').split()];figures.append({'x':t[4],'y':t[5],'width':abs(t[0]),'height':abs(t[3])})
  if index<len(layout['pages']):
   for item in layout['pages'][index]['items']:
    if item['kind']=='glyph':
     g=actual(item)
     if g is not None:gpu.extend(g)
     else:unknown.append({'key':item['key'],'x':item['x'],'y':item['y']})
    elif item['kind']=='image':actual_figures.append({k:item[k]for k in ['x','y','width','height']})
  er=defaultdict(list);ar=defaultdict(list)
  for n,g in enumerate(expected):er[tuple(g['identity'])].append(n)
  for n,g in enumerate(gpu):ar[tuple(g['identity'])].append(n)
  pairs=[];missing=[];extra=[]
  for identity in er.keys()|ar.keys():
   ei,ai=er[identity],ar[identity]
   if ei and ai:
    E=np.array([[expected[n]['x'],expected[n]['y']]for n in ei]);A=np.array([[gpu[n]['x'],gpu[n]['y']]for n in ai]);D=np.linalg.norm(E[:,None]-A[None,:],axis=2);ri,ci=linear_sum_assignment(D)
    for r,c in zip(ri,ci):
     e,g=expected[ei[r]],gpu[ai[c]];dx=(g['x']-e['x'])*96/72;dy=(g['y']-e['y'])*96/72;pairs.append({'identity':list(identity),'reference':[e['x'],e['y']],'gpu':[g['x'],g['y']],'dxPixels':dx,'dyPixels':dy,'distancePixels':math.hypot(dx,dy),'sizeErrorPixels':abs(g['size']-e['size'])*96/72 if g['size']else None,'key':g['key']})
    missing.extend(expected[ei[n]]for n in range(len(ei))if n not in set(ri));extra.extend(gpu[ai[n]]for n in range(len(ai))if n not in set(ci))
   else:missing.extend(expected[n]for n in ei);extra.extend(gpu[n]for n in ai)
  bad=[p for p in pairs if p['distancePixels']>1 or p['sizeErrorPixels']is None or p['sizeErrorPixels']>.1];image_errors=[]
  if len(figures)!=len(actual_figures):image_errors.append('Image count differs')
  for e,a in zip(figures,actual_figures):
   errors={k:(a[k]-e[k])*96/72 for k in ['x','y','width','height']}
   if max(map(abs,errors.values()))>1:image_errors.append(errors)
  passed=index<len(pages)and index<len(layout['pages'])and not(missing or extra or unknown or bad or image_errors)
  records.append({'page':index+1,'referenceGlyphs':len(expected),'measuredGpuGlyphs':len(gpu),'unmeasuredGpuGlyphs':len(unknown),'pairedGlyphs':len(pairs),'missingReferenceGlyphs':missing,'extraGpuGlyphs':extra,'unmeasured':unknown,'misplacedOrWrongSize':sorted(bad,key=lambda x:-x['distancePixels']),'maxPositionErrorPixels':max((p['distancePixels']for p in pairs),default=0),'medianPositionErrorPixels':float(np.median([p['distancePixels']for p in pairs]))if pairs else None,'p95PositionErrorPixels':float(np.percentile([p['distancePixels']for p in pairs],95))if pairs else None,'images':{'reference':figures,'gpu':actual_figures,'errors':image_errors},'passed':passed})
 return {'policy':'Same page, same native font/glyph identity, one-to-one assignment without registration; every glyph within 1px, size within 0.1px, no missing/extra/unmeasured glyphs; image boxes within 1px. Composite tiles without primitive provenance are unmeasured, never assumed correct.','passed':all(p['passed']for p in records),'pages':records}
