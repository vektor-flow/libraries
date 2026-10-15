"""Audit exhaustive grid coverage and publish a compact, phone-readable result."""
import argparse,json,hashlib,shutil
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np

def build(root,corpus,frozen,rules,mapping_path=None):
 path=root/'report.json';report=json.loads(path.read_text());
 if not(root/'report-capture.json').exists():shutil.copyfile(path,root/'report-capture.json')
 assert report['complete'],'Never publish an incomplete scan as complete'
 total=0;pixels=0;geometry=[]
 for doc in report['documents']:
  current=json.loads((root/doc['name']/'layout.json').read_text());previous=json.loads((frozen/doc['name']/'layout.json').read_text());audit=json.loads((frozen/doc['name']/'geometry-comparison.json').read_text());canonical=lambda v:hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest();same=canonical(current['pages'])==canonical(previous['pages']);mapping=json.loads((frozen/'document-browser.json').read_text())['runtimeHashes']['typing-data.json']==report['runtimeHashes']['typing-data.json'];
  if not(same and mapping):
   if mapping_path is None:raise ValueError('Changed geometry/fonts require --mapping for a fresh native glyph audit')
   assert hashlib.sha256(mapping_path.read_bytes()).hexdigest()==report['runtimeHashes']['typing-data.json'],'Audit mapping does not match captured runtime'
   from compare_document_geometry import compare_geometry
   audit=compare_geometry(corpus/doc['name']/'source.pdf',current,json.loads(mapping_path.read_text()),root/doc['name']/'reference-geometry.xml',corpus.parent/'oracle-packages');(root/doc['name']/'geometry-comparison.json').write_text(json.dumps(audit))

  geometry.append({'document':doc['name'],'layoutSha256':canonical(current['pages']),'matchesFrozenLayout':same,'mappingMatchesFrozen':mapping,'passed':audit['passed'],'missingGlyphs':sum(len(p['missingReferenceGlyphs'])for p in audit['pages']),'extraGlyphs':sum(len(p['extraGpuGlyphs'])for p in audit['pages']),'movedOrWrongSize':sum(len(p['misplacedOrWrongSize'])for p in audit['pages'])})
  doc['referencePdfSha256']=hashlib.sha256((corpus/doc['name']/'source.pdf').read_bytes()).hexdigest()
  for page in doc['pages']:
   for level in page['levels']:
    level['geometryPassed']=bool(page['number']<=len(audit['pages'])and audit['pages'][page['number']-1]['passed']);level['passed']=level['passed']and level['geometryPassed']
    assert len(level['tiles'])==level['columns']*level['rows'];seen=set();count=0
    for tile in level['tiles']:
     key=(tile['row'],tile['column']);assert key not in seen;seen.add(key);assert tile['x']==tile['column']*report['tileSize']and tile['y']==tile['row']*report['tileSize'];assert tile['width']==min(report['tileSize'],level['width']-tile['x'])and tile['height']==min(report['tileSize'],level['height']-tile['y']);count+=tile['width']*tile['height']
    assert count==level['width']*level['height'];level['coveredPixels']=count;level['coverageComplete']=True;total+=len(level['tiles']);pixels+=count
    # Display thumbnails retain aspect ratio; full-resolution acceptance pixels
    # remain untouched. Blank cells stay visible in the contact sheet.
    folder=root/doc['name']/f"page-{page['number']:02}"/f"zoom-{level['zoom']}";sheet=Image.new('RGB',(level['columns']*100,level['rows']*110),'white');draw=ImageDraw.Draw(sheet)
    for tile in level['tiles']:
     x=tile['column']*100;y=tile['row']*110
     if tile.get('evidence'):
      image=Image.open(folder/(tile['evidence']+'-gpu.png')).convert('RGB');reference=np.asarray(Image.open(folder/(tile['evidence']+'-reference.png')).convert('RGB'));actual=np.asarray(image);delta=abs(reference.astype(np.int16)-actual.astype(np.int16));union=(reference.mean(2)<178)|(actual.mean(2)<178);tile['meanAbsoluteRGBError']=float(delta.mean()/255);tile['meanAbsoluteRGBErrorOnInkUnion']=float(delta[union].mean()/255)if union.any()else 0.;tile['pixelsDifferingOver8Codes']=int((delta.max(2)>8).sum());image.thumbnail((96,96));sheet.paste(image,(x+2,y+12))
     draw.rectangle((x,y,x+99,y+109),outline='#4c9c72'if tile['passed']else'#c42e38',width=2);draw.text((x+3,y),f"{tile['row']+1},{tile['column']+1}",fill='black')
    sheet.save(folder/'grid.png')
 report['geometryVerification']={'source':'Frozen native font/glyph audit reused ONLY after exact page/item hash and mapping hash equality. Native PDFs unchanged.','documents':geometry};report['accepted']=report['accepted']and all(g['passed']for g in geometry);report['ruleChecks']=json.loads((rules/'all-bars/rules.json').read_text());report['tileCount']=total;report['coveredPixels']=pixels;report['coverageAudited']=True;path.write_text(json.dumps(report,separators=(',',':'))+'\n');(root/'index.html').write_text(Path(__file__).with_name('document-zoom-report.html').read_text())
 for name,source in [('rule-before.png',rules/'before/sqrt-28.6.png'),('rule-after.png',rules/'all-bars/sqrt-28.6.png')]:
  image=Image.open(source);image.crop((0,0,min(image.width,800),min(image.height,550))).save(root/name)
 for name in ['DOCUMENT-SOURCE-NOTICES.txt','LPPL-1.3c.txt']:shutil.copyfile(corpus.parent/'document-report'/name,root/name)
 print(json.dumps({'pages':sum(len(d['pages'])for d in report['documents']),'tiles':total,'coveredPixels':pixels,'accepted':report['accepted']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('corpus',type=Path);p.add_argument('frozen',type=Path);p.add_argument('rules',type=Path);p.add_argument('--mapping',type=Path);a=p.parse_args();build(a.root,a.corpus,a.frozen,a.rules,a.mapping)
