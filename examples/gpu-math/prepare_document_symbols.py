"""Append native reusable symbol fields and TFM provenance; no document inputs."""
import argparse,gzip,json,math,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from fontTools.t1Lib import T1Font
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from tex_font_metrics import load_tex_tfm
PT=72/72.27
# Native definitions in plain.tex and amssymb.sty.
SYMBOLS={r'\diagup':('msbm',30,'ord'),r'\square':('msam',3,'ord'),r'\ll':('cmsy',28,'rel'),r'\circ':('cmsy',14,'bin'),r'\blacksquare':('msam',4,'ord'),r'\bullet':('cmsy',15,'bin')}
for token,code,kind in [('mho',48,'ord'),('Join',49,'rel'),('Box',50,'ord'),('Diamond',51,'ord'),('leadsto',59,'rel'),('sqsubset',60,'rel'),('sqsupset',61,'rel'),('lhd',1,'bin'),('unlhd',2,'bin'),('rhd',3,'bin'),('unrhd',4,'bin')]:
 SYMBOLS['@latexsym:\\'+token]=('lasy',code,kind)
def prepare(source,output,generator,replace=()):
 if any(token not in SYMBOLS for token in replace):raise ValueError('Replacement symbol is not in the native catalogue')
 output.mkdir();data=json.loads((source/'typing-data.json').read_text());w,h=data['atlasSize'];image=Image.frombytes('RGBA',(w,h),gzip.decompress((source/'atlas.rgba.gz').read_bytes()));fonts={};cache={};x=2;y=math.ceil(max(t['uv'][3]for t in data['tiles'].values())*h)+2;row=0;added=0
 for style,mapping in data['maps'].items():
  size=mapping['em']/PT
  for token,(family,code,kind)in SYMBOLS.items():
   if token in mapping['symbols']and token not in replace:continue
   design=(5 if size<6 else 7 if size<8 else 10)if family in ['msam','msbm']else min(10,round(size))
   name=family+str(design);scale=size*PT;identity=(name,code,size)
   if name not in fonts:
    fonts[name]=(T1Font(subprocess.check_output(['kpsewhich',name+'.pfb'],text=True).strip()),load_tex_tfm(subprocess.check_output(['kpsewhich',name+'.tfm'],text=True).strip()))
   font,tfm=fonts[name];c=tfm.chars[code];advance=c['width']*scale
   if identity not in cache:
    glyph=font.getGlyphSet()[font['Encoding'][code]];transform=(scale/1000,0,0,-scale/1000,0,0);pen=SVGPathPen(None);glyph.draw(TransformPen(pen,transform));bounds=BoundsPen(None);glyph.draw(TransformPen(bounds,transform));left,top,right,bottom=bounds.bounds;tw=math.ceil((right-left)*12)+12;th=math.ceil((bottom-top)*12)+12
    if x+tw+2>w:x=2;y+=row+2;row=0
    if y+th+2>h:raise ValueError('Native symbol atlas overflow')
    svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','viewBox':f'{left} {top} {right-left} {bottom-top}'});ET.SubElement(svg,'path',{'d':pen.getCommands()});ET.ElementTree(svg).write(output/'glyph.svg',encoding='unicode');subprocess.run([str(generator),'mtsdf','-svg',str(output/'glyph.svg'),'-dimensions',str(tw),str(th),'-scale','12','-translate',str(.5-left),str(.5-top),'-pxrange','8','-scanline','-overlap','-o',str(output/'glyph.png')],capture_output=True,check=True);image.paste(Image.open(output/'glyph.png').convert('RGBA'),(x,y));cache[identity]={'uv':[x/w,y/h,(x+tw)/w,(y+th)/h],'plane':[left-.5,top-.5,left+(tw-6)/12,top+(th-6)/12]};x+=tw+2;row=max(row,th);added+=1
   mapping['symbols'][token]={'class':kind,'width':advance,'advance':advance,'height':c.get('height',0)*scale,'depth':c.get('depth',0)*scale,'italic':c.get('italic',0)*scale,'fontName':name,'fontCode':code,'glyphParts':[{'fontName':name,'fontCode':code,'fontSize':scale,'x':0,'y':0,'advance':advance}]};data['tiles'][style+'/'+token]=cache[identity]
 (output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(image.tobytes(),mtime=0));(output/'glyph.svg').unlink(missing_ok=True);(output/'glyph.png').unlink(missing_ok=True);print(json.dumps({'newOutlines':added,'rowsUsed':y+row}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--generator',type=Path,required=True);p.add_argument('--replace',action='append',default=[]);a=p.parse_args();prepare(a.source,a.output,a.generator,a.replace)
