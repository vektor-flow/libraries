"""Append exact PK font geometry from offline single-font templates.

Input templates contain font programs only (prepare_bitmap_font_templates.py).
The independent renderer never loads PDF or launches TeX. Rectangle runs preserve
bitmap font edges at arbitrary zoom instead of smoothing them into new curves.
"""
import argparse,json,gzip,shutil
from pathlib import Path
from pypdf import PdfReader
from pypdf.generic import ContentStream

def font_geometry(path):
 reader=PdfReader(path);font=next(iter(reader.pages[0]['/Resources']['/Font'].values())).get_object()
 if font['/Subtype']!='/Type3':raise ValueError('Bitmap font template must contain Type3 glyphs')
 matrix=list(map(float,font['/FontMatrix']))
 if matrix[1]or matrix[2]or matrix[4]or matrix[5]or matrix[0]!=matrix[3]:raise ValueError('Unsupported bitmap font transform')
 names={};code=0
 for value in font['/Encoding']['/Differences']:
  if isinstance(value,int):code=value
  else:names[code]=str(value);code+=1
 glyphs={}
 for code,name in names.items():
  stream=font['/CharProcs'].get(name)
  if stream is None or name=='/.notdef':continue
  transform=None;runs=[]
  for args,op in ContentStream(stream.get_object(),reader).operations:
   if op==b'cm':transform=list(map(float,args))
   elif op==b'INLINE IMAGE':
    settings=args['settings'];w=int(settings['/W']);h=int(settings['/H'])
    if not settings.get('/IM')or settings.get('/BPC')!=1 or not transform or transform[1]or transform[2]:raise ValueError('Unsupported native bitmap image')
    raw=args['data'];pitch=(w+7)//8;decode=list(map(int,settings.get('/D',[0,1])));paint=1 if decode==[1,0]else 0
    active={}
    for row in range(h+1):
     current={};col=0
     while row<h and col<w:
      if ((raw[row*pitch+col//8]>>(7-col%8))&1)!=paint:col+=1;continue
      start=col
      while col<w and ((raw[row*pitch+col//8]>>(7-col%8))&1)==paint:col+=1
      key=(start,col);current[key]=active.get(key,row)
     for (l,r),top in active.items():
      if (l,r)not in current:
       a,b,c,d,e,f=transform;runs.append([e+l*a/w,-(f+(h-top)*d/h),(r-l)*a/w,(row-top)*d/h])
     active=current
  glyphs[code]=runs
 return matrix[0],glyphs

def prepare(source,templates,output):
 output.mkdir();data=json.loads((source/'typing-data.json').read_text());fonts={p.stem:font_geometry(p)for p in templates.glob('*.pdf')};symbols={style+'/'+key:s for style,m in data['maps'].items()for key,s in m['symbols'].items()};rects={}
 for key,s in symbols.items():
  parts=s.get('glyphParts',[])
  if not parts or not all(p['fontName']in fonts for p in parts):continue
  out=[]
  for p in parts:
   factor,glyphs=fonts[p['fontName']];scale=factor*round(p['fontSize'],4)
   if p['fontCode']not in glyphs:raise ValueError('Missing bitmap font character')
   for x,y,w,h in glyphs[p['fontCode']]:out.append([p['x']+x*scale,p['y']+y*scale,w*scale,h*scale])
  rects[key]=out
 data['bitmapGlyphRects']=rects;data['bitmapGlyphPolicy']='Merged exact native PK pixel rectangles, offline font templates only; no document/reference PDF input.';(output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));shutil.copy2(source/'atlas.rgba.gz',output/'atlas.rgba.gz');print(json.dumps({'keys':len(rects),'rectangles':sum(map(len,rects.values()))}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('templates',type=Path);p.add_argument('output',type=Path);a=p.parse_args();prepare(a.source,a.templates,a.output)
