"""Prepare reusable optical text fonts from native Type1/TFM files, never pages."""
import argparse,gzip,json,math,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from fontTools.t1Lib import T1Font
from tex_font_metrics import load_tex_tfm as TFM
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
PT=72/72.27
FONTS={'footnotemark':('cmr6',6),'roman':('cmr10',10),'bold':('cmbx10',10),'italic':('cmti10',10),'mono':('cmtt10',10),'sans':('cmss10',10),'slanted':('cmsl10',10),'section':('cmbx12',14.4),'subsection':('cmbx12',12),'title':('cmr17',17.28),'author':('cmr12',12),'small':('cmr9',9),'footnote':('cmr8',8)}
def prepare(source,output,generator,roles=None):
 output.mkdir();data=json.loads((source/'typing-data.json').read_text());w,h=data['atlasSize'];image=Image.frombytes('RGBA',(w,h),gzip.decompress((source/'atlas.rgba.gz').read_bytes()));mapped=data['maps']['text']['symbols'];cached={}
 for token,s in mapped.items():
  if s.get('fontName')and s.get('fontCode')is not None:cached[(s['fontName'],s['fontCode'],round(s['advance'],7))]=(s,data['tiles']['text/'+token])
 for table in data.get('documentFonts',{}).values():
  for symbol in table['symbols'].values():cached[(symbol['fontName'],symbol['fontCode'],round(symbol['advance'],7))]=(symbol,data['tiles'][symbol['key']])
 # Existing shelves occupy at most this y coordinate, including tile gutters.
 uvs=[tile['uv'][3]for tile in data['tiles'].values()]+[p['uv'][3]for phases in data.get('coverage96',{}).values()for p in phases if p];y=math.ceil(max(uvs)*h)+2;x=2;row=0;fonts=dict(data.get('documentFonts',{}));added=0
 for role,(name,size)in FONTS.items():
  if roles and role not in roles:continue
  font=T1Font(subprocess.check_output(['kpsewhich',name+'.pfb'],text=True).strip());tfm=TFM(subprocess.check_output(['kpsewhich',name+'.tfm'],text=True).strip());glyphs=font.getGlyphSet();scale=size*PT;table={'name':name,'size':scale,'symbols':{},'spaces':{k.lower():v*scale for k,v in tfm.fontdimens.items()},'encoding':font['Encoding']}
  for code,c in tfm.chars.items():
   advance=c['width']*scale;key=f'@document:{role}:{code}';existing=cached.get((name,code,round(advance,7)))
   if existing:s,tile=existing
   else:
    glyph=glyphs.get(font['Encoding'][code]);pen=SVGPathPen(None)
    if glyph is None:continue
    glyph.draw(TransformPen(pen,(scale/1000,0,0,-scale/1000,0,0)));path=pen.getCommands();bounds=BoundsPen(glyphs);glyph.draw(TransformPen(bounds,(scale/1000,0,0,-scale/1000,0,0)))
    if not bounds.bounds:continue
    left,top,right,bottom=bounds.bounds;padding=6;tw=math.ceil((right-left)*6)+12;th=math.ceil((bottom-top)*6)+12
    if x+tw+2>w:x=2;y+=row+2;row=0
    if y+th+2>h:raise ValueError('Document font atlas overflow')
    svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','viewBox':f'{left} {top} {right-left} {bottom-top}'});ET.SubElement(svg,'path',{'d':path});ET.ElementTree(svg).write(output/'glyph.svg',encoding='unicode');subprocess.run([str(generator),'mtsdf','-svg',str(output/'glyph.svg'),'-dimensions',str(tw),str(th),'-scale','6','-translate',str(padding/6-left),str(padding/6-top),'-pxrange','8','-scanline','-overlap','-o',str(output/'glyph.png')],capture_output=True,check=True)
    image.paste(Image.open(output/'glyph.png').convert('RGBA'),(x,y));tile={'plane':[left-padding/6,top-padding/6,left+(tw-padding)/6,top+(th-padding)/6],'uv':[x/w,y/h,(x+tw)/w,(y+th)/h]};x+=tw+2;row=max(row,th);added+=1
    s={'width':advance,'height':c.get('height',0)*scale,'depth':c.get('depth',0)*scale,'advance':advance,'italic':c.get('italic',0)*scale,'fontName':name,'fontCode':code,'kerns':{str(k):v*scale for k,v in tfm.kerning.get(code,{}).items()}}
   table['symbols'][str(code)]={**s,'key':'text/'+key};data['tiles']['text/'+key]=tile
  fonts[role]=table
 note=fonts.get('footnote');
 if note:note['markRaise']=TFM(subprocess.check_output(['kpsewhich','cmsy8.tfm'],text=True).strip()).fontdimens['SUP2']*8*PT
 data['documentFonts']=fonts;(output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(image.tobytes(),mtime=0));(output/'glyph.svg').unlink();(output/'glyph.png').unlink();print(json.dumps({'newOutlines':added,'rowsUsed':y+row,'fonts':len(fonts)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--generator',type=Path,required=True);p.add_argument('--roles');a=p.parse_args();prepare(a.source,a.output,a.generator,a.roles.split(',')if a.roles else None)
