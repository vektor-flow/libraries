"""Dev-only reusable 96dpi glyph coverage cache. No article/reference PDF input.

Matches the reference rasterizer's unhinted Type1 glyph coverage and quarter-pixel
x phases. Arbitrary zoom continues to use the independently prepared MTSDF tiles.
"""
import argparse,gzip,json,math,subprocess,os
from pathlib import Path
import freetype
from fontTools.tfmLib import TFM
from fontTools.t1Lib import T1Font
from PIL import Image,ImageOps
from tex_font_metrics import native_scaled

class MuPdfFont:
 """Offline single-font glyph masks; no author document or reference PDF."""
 def __init__(self,path,type1):
  import pymupdf
  self.pdf=pymupdf
  if type1 is None:
   self.doc=pymupdf.open(path);self.page=self.doc[0];self.page.set_mediabox(pymupdf.Rect(0,0,96,96));self.fontName=self.page.get_fonts()[0][4]
  else:
   self.doc=pymupdf.open();self.page=self.doc.new_page(width=96,height=96);self.fontName='native'
   font=self.page.insert_font(fontname=self.fontName,fontfile=path,set_simple=True)
   names=type1['Encoding'];self.doc.xref_set_key(font,'Encoding','<< /Type /Encoding /Differences [0 '+' '.join('/'+name for name in names)+'] >>')
  self.stream=self.doc.get_new_xref();self.doc.update_object(self.stream,'<<>>');self.doc.update_stream(self.stream,b'');self.page.set_contents(self.stream)
 def mask(self,code,size,phase,yphase=0):
  text=f'BT /{self.fontName} {size:.4f} Tf 1 0 0 1 {48+phase*.1875:.4f} {48-yphase*.75:.4f} Tm <{code:02x}> Tj ET'
  self.doc.update_stream(self.stream,text.encode('ascii'))
  pix=self.page.get_pixmap(matrix=self.pdf.Matrix(96/72,96/72),alpha=False)
  alpha=ImageOps.invert(Image.frombytes('RGB',(pix.width,pix.height),pix.samples).getchannel('R'));bounds=alpha.getbbox()
  return (alpha.crop(bounds),[bounds[0]-64,bounds[1]-64,bounds[2]-bounds[0],bounds[3]-bounds[1]])if bounds else(None,None)

def prepare(source,output,extras=None,rasterizer='freetype',bitmap_templates=None):
 output.mkdir();data=json.loads((source/'typing-data.json').read_text());w,h=data['atlasSize'];atlas=Image.frombytes('RGBA',(w,h),gzip.decompress((source/'atlas.rgba.gz').read_bytes()));x=2;y=math.ceil(max(t['uv'][3]*h for t in data['tiles'].values()))+2;row=0;faces={};rasterFonts={};cache={};coverage={}if rasterizer=='mupdf'else dict(data.get('coverage96',{}));metrics={}if rasterizer=='mupdf'else dict(data.get('coverage96Metrics',{}));y=math.ceil(max([y]+[t['uv'][3]*h for phases in coverage.values()for t in phases if t]))+2;env=os.environ.copy()
 if extras:
  for v in ['TFMFONTS','T1FONTS']:env[v]=str(extras.resolve())+'//:'
 def find(name):
  value=subprocess.run(['kpsewhich',name],capture_output=True,text=True,env=env).stdout.strip();return value or None
 symbols={style+'/'+key:s for style,m in data['maps'].items()for key,s in m['symbols'].items()}
 parts={}
 for key,s in list(symbols.items()):
  glyphs=s.get('glyphParts',[])
  if not glyphs or len(glyphs)==1 and not glyphs[0]['x'] and not glyphs[0]['y']:continue
  if not all(g.get('fontName')and g.get('fontSize')and g.get('advance')is not None for g in glyphs):continue
  parts[key]=[]
  for g in glyphs:
   component='coverage/'+g['fontName']+'/'+format(g['fontSize'],'.6f')+'/'+str(g['fontCode'])
   symbols[component]={**g,'size':g['fontSize']}
   parts[key].append({'key':component,'x':g['x'],'y':g['y']})
 for font in data.get('documentFonts',{}).values():
  for s in font['symbols'].values():symbols[s['key']]={**s,'size':font['size']}
 missing=set();font_tfms={}
 for key,s in symbols.items():
  name=s.get('fontName');code=s.get('fontCode')
  if key in coverage and metrics.get(key,{}).get('font')==name:continue
  if name is None or code is None or s.get('advance')is None:continue
  if name not in faces:
   p=find(name+'.pfb');t=find(name+'.tfm')
   if t:font_tfms[name]=TFM(t)
   if not p or not t:
    faces[name]=None;missing.add(name)
    template=bitmap_templates/(name+'.pdf')if bitmap_templates else None
    if rasterizer=='mupdf'and t and template and template.is_file():faces[name]=(None,None,font_tfms[name]);rasterFonts[name]=MuPdfFont(str(template),None);missing.discard(name)
   else:
    faces[name]=(freetype.Face(p),T1Font(p),font_tfms[name])
    if rasterizer=='mupdf':rasterFonts[name]=MuPdfFont(p,faces[name][1])
  if not faces[name]:
   if name in font_tfms:
    tfm=font_tfms[name];size=s.get('size')or next((p['fontSize']for p in s.get('glyphParts',[])if p.get('fontSize')),None)or s['advance']/tfm.chars[code]['width']
    metrics[key]={'size':size,'advance':native_scaled(tfm.chars[code]['width'],size/(72/72.27)),'font':name,'bitmap':True,'pkDpi':600}
   continue
  face,type1,tfm=faces[name];glyphs=s.get('glyphParts',[]);exact_size=s.get('size')or(glyphs[0].get('fontSize')if len(glyphs)==1 else None)or s['advance']/tfm.chars[code]['width'];size=round(exact_size,4);identity=(name,code,size);metrics[key]={'size':exact_size,'advance':s['advance'],'font':name,**({'bitmap':True,'pkDpi':600}if type1 is None else{})}
  if identity in cache:coverage[key]=cache[identity];metrics[key]['yPhases']=len(cache[identity])//4;continue
  if rasterizer!='mupdf':
   pixels=size*96/72;rounded=max(1,math.floor(pixels+.5));face.set_pixel_sizes(0,rounded);matrix=freetype.Matrix(int(pixels/rounded*65536),0,0,int(pixels/rounded*65536));gid=face.get_name_index(type1['Encoding'][code].encode())
  yPhases=(1 if size*96/72>=8 else 2 if size*96/72>=4 else 4)if rasterizer=='mupdf'else 1;metrics[key]['yPhases']=yPhases
  phases=[]
  for phaseIndex in range(4*yPhases):
   phase=phaseIndex%4;yphase=(phaseIndex//4)/yPhases
   if rasterizer=='mupdf':
    alpha,rect=rasterFonts[name].mask(code,size,phase,yphase)
    if alpha is None:phases.append(None);continue
    tw,th=alpha.size
   else:
    face.set_transform(matrix,freetype.Vector(phase*16,0));face.load_glyph(gid,freetype.FT_LOAD_NO_BITMAP|freetype.FT_LOAD_NO_HINTING);face.glyph.render(freetype.FT_RENDER_MODE_NORMAL);bitmap=face.glyph.bitmap;tw,th=bitmap.width,bitmap.rows
    if not tw or not th:phases.append(None);continue
   if x+tw+2>w:x=2;y+=row+2;row=0
   if y+th+2>h:raise ValueError('Coverage atlas overflow')
   if rasterizer!='mupdf':
    raw=bytes(bitmap.buffer);alpha=Image.frombytes('L',(bitmap.pitch,th),raw).crop((0,0,tw,th));rect=[face.glyph.bitmap_left,-face.glyph.bitmap_top,tw,th]
   image=Image.new('RGBA',(tw,th),(255,255,255,255));image.putalpha(alpha);atlas.paste(image,(x,y));phases.append({'uv':[x/w,y/h,(x+tw)/w,(y+th)/h],'rect':rect});x+=tw+2;row=max(row,th)
  cache[identity]=phases;coverage[key]=phases
 data['coverage96']=coverage;data['coverage96Metrics']=metrics;data['coverage96Parts']={key:value for key,value in parts.items()if all(g['key']in coverage for g in value)};data['coverage96Rasterizer']=rasterizer;data['coverage96Policy']='Reusable native font masks at 96dpi, four x phases and adaptive y phases, '+rasterizer+'. No page data. MTSDF remains the fallback at other scales/transforms.';(output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(atlas.tobytes(),mtime=0));print(json.dumps({'keys':len(coverage),'newUniqueGlyphs':len(cache),'rowsUsed':y+row,'missingFontFiles':sorted(missing)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--oracle-extras',type=Path);p.add_argument('--rasterizer',choices=['freetype','mupdf'],default='freetype');p.add_argument('--bitmap-font-templates',type=Path);a=p.parse_args();prepare(a.source,a.output,a.oracle_extras,a.rasterizer,a.bitmap_font_templates)
