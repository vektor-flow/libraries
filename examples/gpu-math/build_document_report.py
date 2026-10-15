"""Build a phone-readable static report from preserved independent comparisons."""
import argparse,gzip,html,json,shutil,statistics
from PIL import Image,ImageDraw
from pathlib import Path

def build(corpus,browser,output):
 output.mkdir();pixels=json.loads((browser/'pixel-comparison.json').read_text());gpu=json.loads((browser/'document-browser.json').read_text());engine=json.loads((corpus/'engine-benchmark.json').read_text())if(corpus/'engine-benchmark.json').exists()else{'engine':'Original supplied PDF; no local compilation timing','rasterizer':'pdftoppm at 96 dpi','documents':[]};sources=json.loads((corpus/'sources.json').read_text());records=[]
 for doc in pixels['documents']:
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
   geometry=page.get('geometry',{})
   for key in ['missingReferenceGlyphs','extraGpuGlyphs','misplacedOrWrongSize','unmeasured']:
    if key in geometry:geometry[key+'Count']=len(geometry[key]);geometry[key]=geometry[key][:4]
  timings=next(d for d in gpu['results']if d['name']==name);baseline=next((d for d in engine['documents']if d['name']==name),{'trials':[]})
  records.append({**doc,'source':next(d for d in sources if d['name']==name),'modules':timings['modules'],'gpuTimings':timings['timings'],'latexTimings':baseline['trials']})
 summary={'accepted':pixels['accepted'],'documents':records,'policy':pixels['policy'],'pixelMode':gpu.get('pixelMode','MTSDF'),'runtimeHashes':gpu.get('runtimeHashes',{}),'geometryPolicy':'One-to-one native font/glyph matching on each original page; position <=1px, font size <=.1px; no missing, extra or unmeasured glyphs. Vector-only tiles are checked by pixels.','backend':gpu['backend'],'coldBrowserReadyMs':gpu['coldBrowserReadyMs'],'scope':gpu['scope'],'engine':engine['engine'],'rasterizer':engine['rasterizer']};(output/'report.json').write_text(json.dumps(summary,indent=2)+'\n')
 (output/'index.html').write_text(Path(__file__).with_name('document-report.html').read_text())
 print('Report:',output,'documents:',len(records),'accepted:',summary['accepted'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('browser',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.corpus,a.browser,a.output)
