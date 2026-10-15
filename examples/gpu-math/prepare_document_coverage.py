"""Dev-only reusable 96dpi glyph coverage cache. No document/PDF input.

Matches the reference rasterizer's unhinted Type1 glyph coverage and quarter-pixel
x phases. Arbitrary zoom continues to use the independently prepared MTSDF tiles.
"""
import argparse,gzip,json,math,subprocess,os
from pathlib import Path
import freetype
from fontTools.tfmLib import TFM
from fontTools.t1Lib import T1Font
from PIL import Image

def prepare(source,output,extras=None):
 output.mkdir();data=json.loads((source/'typing-data.json').read_text());w,h=data['atlasSize'];atlas=Image.frombytes('RGBA',(w,h),gzip.decompress((source/'atlas.rgba.gz').read_bytes()));x=2;y=math.ceil(max(t['uv'][3]*h for t in data['tiles'].values()))+2;row=0;faces={};cache={};coverage={};metrics={};env=os.environ.copy()
 if extras:
  for v in ['TFMFONTS','T1FONTS']:env[v]=str(extras.resolve())+'//:'
 def find(name):
  value=subprocess.run(['kpsewhich',name],capture_output=True,text=True,env=env).stdout.strip();return value or None
 symbols={style+'/'+key:s for style,m in data['maps'].items()for key,s in m['symbols'].items()}
 for font in data.get('documentFonts',{}).values():
  for s in font['symbols'].values():symbols[s['key']]=s
 missing=set()
 for key,s in symbols.items():
  name=s.get('fontName');code=s.get('fontCode')
  if name is None or code is None or not s.get('advance'):continue
  if name not in faces:
   p=find(name+'.pfb');t=find(name+'.tfm')
   if not p or not t:faces[name]=None;missing.add(name);continue
   faces[name]=(freetype.Face(p),T1Font(p),TFM(t))
  if not faces[name]:continue
  face,type1,tfm=faces[name];size=round(s['advance']/tfm.chars[code]['width'],4);identity=(name,code,size);metrics[key]={'size':s['advance']/tfm.chars[code]['width'],'advance':s['advance'],'font':name}
  if identity in cache:coverage[key]=cache[identity];continue
  pixels=size*96/72;rounded=max(1,math.floor(pixels+.5));face.set_pixel_sizes(0,rounded);matrix=freetype.Matrix(int(pixels/rounded*65536),0,0,int(pixels/rounded*65536));gid=face.get_name_index(type1['Encoding'][code].encode());phases=[]
  for phase in range(4):
   face.set_transform(matrix,freetype.Vector(phase*16,0));face.load_glyph(gid,freetype.FT_LOAD_NO_BITMAP|freetype.FT_LOAD_NO_HINTING);face.glyph.render(freetype.FT_RENDER_MODE_NORMAL);bitmap=face.glyph.bitmap;tw,th=bitmap.width,bitmap.rows
   if not tw or not th:phases.append(None);continue
   if x+tw+2>w:x=2;y+=row+2;row=0
   if y+th+2>h:raise ValueError('Coverage atlas overflow')
   raw=bytes(bitmap.buffer);alpha=Image.frombytes('L',(bitmap.pitch,th),raw).crop((0,0,tw,th));image=Image.new('RGBA',(tw,th),(255,255,255,255));image.putalpha(alpha);atlas.paste(image,(x,y));phases.append({'uv':[x/w,y/h,(x+tw)/w,(y+th)/h],'rect':[face.glyph.bitmap_left,-face.glyph.bitmap_top,tw,th]});x+=tw+2;row=max(row,th)
  cache[identity]=phases;coverage[key]=phases
 data['coverage96']=coverage;data['coverage96Metrics']=metrics;data['coverage96Policy']='Reusable Type1 glyph masks at 96dpi, four x phases, unhinted FreeType. No page data. MTSDF remains the fallback at other scales/transforms.';(output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(atlas.tobytes(),mtime=0));print(json.dumps({'keys':len(coverage),'uniqueGlyphs':len(cache),'rowsUsed':y+row,'missingFontFiles':sorted(missing)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--oracle-extras',type=Path);a=p.parse_args();prepare(a.source,a.output,a.oracle_extras)
