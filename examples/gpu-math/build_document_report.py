"""Build a phone-readable static report from preserved independent comparisons."""
import argparse,gzip,hashlib,html,json,shutil,statistics
from PIL import Image,ImageDraw
from pathlib import Path

def geometry_summary(pages):
 """Keep the document-wide maximum visible, including failures and missing pages."""
 measured=[p for p in pages if p.get('geometry') is not None]
 if not measured:return None
 worst=max(measured,key=lambda p:p['geometry'].get('maxPositionErrorPixels',0))
 geometry=worst['geometry']
 glyph=max(geometry.get('glyphNeighborhoods',[]),key=lambda g:g['distancePixels'],default=None)
 return {'maxPositionErrorPixels':geometry.get('maxPositionErrorPixels'),
         'page':worst['page'],'worstGlyph':glyph,'pixelsPerInch':96,
         'measuredPages':len(measured),'totalPages':len(pages),
         'pairedGlyphs':sum(p['geometry'].get('pairedGlyphs',0)for p in measured),
         'allPagesPassed':len(measured)==len(pages)and all(p['geometry'].get('passed',False)for p in measured)}

def build_benchmark(geometry_path,comparison_path,output,verified_native=None):
 geometry=json.loads(geometry_path.read_text());comparison=json.loads(comparison_path.read_text())
 pages=[{'page':p['page'],'geometry':p}for p in geometry['pages']]
 if len(pages)!=comparison['pages']:raise ValueError('Geometry and timing page counts differ')
 summary=geometry_summary(pages)
 if summary['pairedGlyphs']!=comparison['nativeConstituentGlyphs']:raise ValueError('Geometry and timing glyph counts differ')
 output.mkdir()
 record={'comparison':comparison,'geometrySummary':summary,
         'geometryPassed':geometry['passed'],'positionTolerancePixels':geometry['positionTolerancePixels'],
         'referenceOrigins':geometry['referenceOrigins'],
         'measurementStatus':'Historical timings are withheld pending verification. No complete uncached VKF timing is established.',
         'renderer':'Existing JavaScript renderer; full VKF document layout remains unfinished.',
         'geometryEvidence':str(geometry_path.resolve()),'timingEvidence':str(comparison_path.resolve()),
         'pages':[{'page':p['page'],'passed':p['passed'],'pairedGlyphs':p['pairedGlyphs'],
                   'maxPositionErrorPixels':p['maxPositionErrorPixels']}for p in geometry['pages']]}
 if verified_native is not None:
  native=json.loads(verified_native.read_text())
  audit_path=verified_native.parent/'verification.json'
  audit=json.loads(audit_path.read_text())
  if not audit['passed'] or audit['summarySha256']!=hashlib.sha256(verified_native.read_bytes()).hexdigest():raise ValueError('Native timing audit is missing or stale')
  if native['sourceSha256']!=comparison['sourceSha256'] or native['referenceBibSha256']!=comparison['referenceBibSha256']:raise ValueError('Native timing source differs from the geometry benchmark')
  record.update(verifiedTimings=native['summary'],verifiedTimingScope=audit['scope'],
                verifiedTimingEvidence=str(audit_path.resolve()),
                measurementStatus='Fresh native-engine timings passed the independent cold-cache, complete-PDF and edit audit. Glyph-offset evidence belongs to the existing JavaScript renderer.')
 (output/'report.json').write_text(json.dumps(record,indent=2)+'\n')
 (output/'index.html').write_text(Path(__file__).with_name('benchmark-report.html').read_text())
 print('Benchmark report:',output,'worst offset:',summary['maxPositionErrorPixels'],'px; page',summary['page'])

def build(corpus,browser,output):
 output.mkdir();pixels=json.loads((browser/'pixel-comparison.json').read_text());gpu=json.loads((browser/'document-browser.json').read_text());engine=json.loads((corpus/'engine-benchmark.json').read_text())if(corpus/'engine-benchmark.json').exists()else{'engine':'Original supplied PDF; no local compilation timing','rasterizer':'pdftoppm at 96 dpi','documents':[]};sources=json.loads((corpus/'sources.json').read_text());records=[]
 for doc in pixels['documents']:
  doc['geometrySummary']=geometry_summary(doc['pages'])
  name=doc['name'];folder=output/name;folder.mkdir();shutil.copyfile(corpus/name/'source.tex',folder/'source.tex');shutil.copyfile(corpus/name/'source.pdf',folder/'reference.pdf')
  if(corpus/name/'original-source.bin').exists():shutil.copyfile(corpus/name/'original-source.bin',folder/'original-source.bin')
  if(corpus/name/'plot.png').exists():shutil.copyfile(corpus/name/'plot.png',folder/'plot.png')
  for index in range(1,max(doc['referencePages'],doc['nativePages'])+1):
   reference=corpus/name/f'reference-{index}.png'
   if not reference.exists():reference=corpus/name/f'reference-{index:02}.png'
   if reference.exists():shutil.copyfile(reference,folder/f'reference-{index:02}.png')
   for kind in ['native','difference','local-error']:
    image=browser/name/f'{kind}-{index:02}.png'
    if image.exists():shutil.copyfile(image,folder/image.name)
  for page in doc['pages']:
   index=page['page'];ref=folder/f'reference-{index:02}.png';native=folder/f'native-{index:02}.png';error=folder/f'local-error-{index:02}.png'
   if not all(p.exists()for p in [ref,native,error]):continue
   images=[Image.open(p).convert('RGB')for p in [ref,native,error]];page['closeups']=[]
   for rank,region in enumerate(page.get('spatialAccuracy',{}).get('regions',[])[:4],1):
    x0,y0,x1,y1=region['bbox'];cx=(x0+x1)//2;cy=(y0+y1)//2;box=(max(0,cx-36),max(0,cy-22),min(images[0].width,cx+36),min(images[0].height,cy+22));parts=[image.crop(box).resize((216,132),Image.Resampling.NEAREST)for image in images];combined=Image.new('RGB',(648,152),'white');draw=ImageDraw.Draw(combined)
    for i,part in enumerate(parts):combined.paste(part,(i*216,20));draw.text((i*216+4,2),['PDF','GPU','Local error'][i],fill='black')
    name_=f'closeup-{index:02}-{rank}.png';combined.save(folder/name_);page['closeups'].append(name_)
  # Full audits remain downloadable per page; keep the phone's initial JSON small.
  for page in doc['pages']:
   audit=f"audit-{page['page']:02}.json.gz";page['audit']=audit
   with gzip.open(folder/audit,'wt',encoding='utf-8')as f:json.dump(page,f,separators=(',',':'))
   spatial=page.get('spatialAccuracy',{})
   for key in ['regions','concentratedErrorRegions']:
    if key in spatial:spatial[key+'Count']=len(spatial[key]);spatial[key]=spatial[key][:4]
   glyph_pixels=page.get('glyphPixels')
   if glyph_pixels and 'glyphs'in glyph_pixels:
    glyph_pixels['worstGlyphs']=sorted(glyph_pixels.pop('glyphs'),key=lambda g:g['pixelError']if g['pixelError']is not None else 2,reverse=True)[:4]
   geometry=page.get('geometry',{})
   for key in ['missingReferenceGlyphs','extraGpuGlyphs','misplacedOrWrongSize','unmeasured']:
    if key in geometry:geometry[key+'Count']=len(geometry[key]);geometry[key]=geometry[key][:4]
  timings=next(d for d in gpu['results']if d['name']==name);baseline=next((d for d in engine['documents']if d['name']==name),{'trials':[]})
  records.append({**doc,'source':next(d for d in sources if d['name']==name),'modules':timings['modules'],'gpuTimings':timings['timings'],'latexTimings':baseline['trials']})
 summary={'accepted':pixels['accepted'],'documents':records,'policy':pixels['policy'],'pixelMode':gpu.get('pixelMode','MTSDF'),'runtimeHashes':gpu.get('runtimeHashes',{}),'geometryPolicy':'One-to-one native font/glyph matching on each original page; position <=1px, font size <=.1px; no missing, extra or unmeasured glyphs. Vector-only tiles are checked by pixels.','backend':gpu['backend'],'coldBrowserReadyMs':gpu['coldBrowserReadyMs'],'scope':gpu['scope'],'engine':engine['engine'],'rasterizer':engine['rasterizer']};(output/'report.json').write_text(json.dumps(summary,indent=2)+'\n')
 (output/'index.html').write_text(Path(__file__).with_name('document-report.html').read_text())
 print('Report:',output,'documents:',len(records),'accepted:',summary['accepted'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('browser',type=Path);p.add_argument('output',type=Path);p.add_argument('--benchmark',action='store_true',help='Read geometry.json and timing comparison.json instead of corpus/browser directories');p.add_argument('--verified-native',type=Path,help='Fresh native-timings.json with a passing SHA-bound independent verification.json');a=p.parse_args()
 if a.verified_native and not a.benchmark:p.error('--verified-native requires --benchmark')
 if a.benchmark:build_benchmark(a.corpus,a.browser,a.output,a.verified_native)
 else:build(a.corpus,a.browser,a.output)
