"""Append independently prepared package glyphs to a reusable font atlas."""
import argparse,gzip,json,math,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
from glyph_provenance import DVI

def prepare(source,root,output,generator,extras=None,skip_existing=False):
 if output.exists():raise ValueError('Use a fresh output directory')
 output.mkdir();data=json.loads((source/'typing-data.json').read_text());w,h=data['atlasSize'];image=Image.frombytes('RGBA',(w,h),gzip.decompress((source/'atlas.rgba.gz').read_bytes()))
 x=2;y=math.ceil(max(t['uv'][3]for t in data['tiles'].values())*h)+2;row=0;cache={};added=0
 for style,mapping in data['maps'].items():
  package=json.loads((root/f'typing-{style}/symbol-mapping.json').read_text())
  if abs(mapping['em']-package['em'])>1e-6:raise ValueError('Package and base optical sizes differ')
  for index,(token,symbol)in enumerate(package['symbols'].items()):
   if token in mapping['symbols']:
    if skip_existing:continue
    raise ValueError('Duplicate package glyph: '+token)
   parts=DVI(root/f'typing-{style}'/str(index)/'expression.dvi',extras).read();path=symbol['outline']['svgPath'];pen=BoundsPen(None);parse_path(path,pen)
   if not pen.bounds:raise ValueError('Empty native package glyph: '+token)
   left,top,right,bottom=pen.bounds;digest=symbol['outlineHash']
   if digest not in cache:
    scale=8;padding=6;tw=math.ceil((right-left)*scale)+2*padding;th=math.ceil((bottom-top)*scale)+2*padding
    if x+tw+2>w:x=2;y+=row+2;row=0
    if y+th+2>h:raise ValueError('Package font atlas overflow')
    svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','viewBox':f'{left} {top} {right-left} {bottom-top}'});ET.SubElement(svg,'path',{'d':path});ET.ElementTree(svg).write(output/'glyph.svg',encoding='unicode')
    subprocess.run([str(generator),'mtsdf','-svg',str(output/'glyph.svg'),'-dimensions',str(tw),str(th),'-scale',str(scale),'-translate',str(padding/scale-left),str(padding/scale-top),'-pxrange','8','-scanline','-overlap','-o',str(output/'glyph.png')],capture_output=True,check=True)
    image.paste(Image.open(output/'glyph.png').convert('RGBA'),(x,y));cache[digest]={'uv':[x/w,y/h,(x+tw)/w,(y+th)/h],'plane':[left-padding/scale,top-padding/scale,left+(tw-padding)/scale,top+(th-padding)/scale]};x+=tw+2;row=max(row,th);added+=1
   measured={k:v for k,v in symbol.items()if k not in ['outline','outlineHash']};measured.update(glyphParts=parts,inkBounds=list(pen.bounds))
   if len(parts)==1:measured.update(fontName=parts[0]['fontName'],fontCode=parts[0]['fontCode'],advance=parts[0]['advance'])
   mapping['symbols'][token]=measured;data['tiles'][style+'/'+token]=cache[digest]
 (output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(image.tobytes(),mtime=0));(output/'glyph.svg').unlink(missing_ok=True);(output/'glyph.png').unlink(missing_ok=True)
 print(json.dumps({'newOutlines':added,'rowsUsed':y+row}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('root',type=Path);p.add_argument('output',type=Path);p.add_argument('--generator',type=Path,required=True);p.add_argument('--oracle-extras',type=Path);p.add_argument('--skip-existing',action='store_true');a=p.parse_args();prepare(a.source,a.root,a.output,a.generator,a.oracle_extras,a.skip_existing)
