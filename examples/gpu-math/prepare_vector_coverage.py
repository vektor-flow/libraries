"""Append reusable glyph masks from an input illustration's embedded fonts.

The source illustration and its prepared atlas are the only inputs. The document
reference PDF, surrounding text, and reference page coordinates are never read.
Masks apply only at the explicitly prepared illustration scale and 96dpi.
"""
import argparse,gzip,hashlib,io,json,math
from pathlib import Path
import freetype,pymupdf
from PIL import Image

def prepare(pdf,source,output,scale):
 output.mkdir();spec=json.loads((source/'asset.json').read_text())
 if hashlib.sha256(pdf.read_bytes()).hexdigest()!=spec['source']['sha256']:raise ValueError('Source illustration hash mismatch')
 w,h=spec['atlasSize'];new_h=h*2
 if new_h>8192:raise ValueError('Coverage atlas exceeds device limit')
 atlas=Image.new('RGBA',(w,new_h));atlas.paste(Image.frombytes('RGBA',(w,h),gzip.decompress((source/'atlas.rgba.gz').read_bytes())),(0,0))
 for tile in spec['tiles'].values():tile['uv'][1]*=h/new_h;tile['uv'][3]*=h/new_h
 doc=pymupdf.open(pdf);fonts={}
 for xref,ext,kind,name,*_ in doc[0].get_fonts(full=True):
  if ext!='ttf':raise ValueError('Coverage requires embedded TrueType fonts')
  fonts[name.split('+')[-1].lower()]=freetype.Face(io.BytesIO(doc.extract_font(xref)[3]))
 coverage={};metrics={};x=2;y=h+2;row=0
 for item in spec['items']:
  key=item['key'];g=item.get('nativeGlyph')
  if not g or key in coverage:continue
  face=fonts[g['fontName']];pixels=g['fontSize']*scale*96/72;rounded=max(1,math.floor(pixels+.5));face.set_pixel_sizes(0,rounded)
  matrix=freetype.Matrix(round(pixels/rounded*65536),0,0,round(pixels/rounded*65536));phases=[]
  for phase in range(4):
   face.set_transform(matrix,freetype.Vector(phase*16,0));face.load_glyph(g['fontGlyphId'],freetype.FT_LOAD_NO_BITMAP|freetype.FT_LOAD_NO_HINTING);face.glyph.render(freetype.FT_RENDER_MODE_NORMAL)
   bitmap=face.glyph.bitmap;tw,th=bitmap.width,bitmap.rows
   if not tw or not th:phases.append(None);continue
   if x+tw+2>w:x=2;y+=row+2;row=0
   if y+th+2>new_h:raise ValueError('Illustration coverage atlas overflow')
   alpha=Image.frombytes('L',(bitmap.pitch,th),bytes(bitmap.buffer)).crop((0,0,tw,th));tile=Image.new('RGBA',(tw,th),(255,255,255,255));tile.putalpha(alpha);atlas.paste(tile,(x,y))
   phases.append({'uv':[x/w,y/new_h,(x+tw)/w,(y+th)/new_h],'rect':[face.glyph.bitmap_left,-face.glyph.bitmap_top,tw,th]});x+=tw+2;row=max(row,th)
  coverage[key]=phases;metrics[key]={'scale':scale,'rawPositions':True}
 spec['atlasSize']=[w,new_h];spec['coverage96']=coverage;spec['coverage96Metrics']=metrics;spec['coverage96Policy']='Embedded input illustration fonts only; unhinted FreeType, four x phases, explicit illustration scale at 96dpi.'
 (output/'asset.json').write_text(json.dumps(spec,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(atlas.tobytes(),mtime=0));print(json.dumps({'glyphs':len(coverage),'scale':scale,'atlasSize':spec['atlasSize']}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--scale',type=float,required=True);a=p.parse_args()
 if not math.isfinite(a.scale)or a.scale<=0:raise ValueError('Scale must be positive')
 prepare(a.pdf,a.source,a.output,a.scale)
