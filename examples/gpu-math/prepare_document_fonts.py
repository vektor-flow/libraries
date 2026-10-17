"""Prepare reusable optical text fonts from native Type1/TFM files, never pages."""
import argparse,gzip,json,math,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from fontTools.t1Lib import T1Font
from tex_font_metrics import load_tex_tfm as TFM
from tex_font_metrics import native_scaled
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
PT=72/72.27
FONTS={'footnotemark':('cmr6',6),'roman':('cmr10',10),'bold':('cmbx10',10),'italic':('cmti10',10),'mono':('cmtt10',10),'sans':('cmss10',10),'slanted':('cmsl10',10),'section':('cmbx12',14.4),'subsection':('cmbx12',12),'title':('cmr17',17.28),'author':('cmr12',12),'small':('cmr9',9),'smallbold':('cmbx9',9),'smallcaps':('cmcsc10',10),'footnotemono':('cmtt8',8),'titlemark':('cmsy8',8),'notemark':('cmsy6',6),'footnote':('cmr8',8)}
def refresh_metrics(table,tfm,size):
 table['size']=round(size*65536)/65536*PT
 table['spaces']={k.lower():v if k=='SLANT'else native_scaled(v,size)for k,v in tfm.fontdimens.items()}
 table['ligatures']=tfm.ligatures
 for code,s in table['symbols'].items():
  c=tfm.chars[int(code)];advance=native_scaled(c['width'],size)
  s.update(width=advance,advance=advance,height=native_scaled(c.get('height',0),size),depth=native_scaled(c.get('depth',0),size),italic=native_scaled(c.get('italic',0),size),kerns={str(k):native_scaled(v,size)for k,v in tfm.kerning.get(int(code),{}).items()})
  if 'glyphParts'in s:s['glyphParts']=[{**p,'fontSize':table['size'],'advance':advance}for p in s['glyphParts']]
def refresh_note_metrics(fonts):
 note=fonts.get('footnote')
 if not note:return
 point_size=note['size']/PT;design=min(10,round(point_size))
 note['markRaise']=TFM(subprocess.check_output(['kpsewhich',f'cmsy{design}.tfm'],text=True).strip()).fontdimens['SUP2']*point_size*PT
 mark=fonts.get('footnotemark',{}).get('symbols',{}).get('49')
 if mark:note['nativeFootnoteSep']=max(note['symbols']['77']['height'],mark['height']+note['markRaise'])
def prepare(source,output,generator,roles=None,font_spec=None):
 specification=FONTS if font_spec is None else font_spec
 if not isinstance(specification,dict)or not specification:raise ValueError('Font specification must be a nonempty role mapping')
 for role,value in specification.items():
  if not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*',role)or not isinstance(value,(list,tuple))or len(value)!=2:raise ValueError('Invalid font role specification')
  name,size=value
  if not isinstance(name,str)or not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*',name)or not isinstance(size,(int,float))or not math.isfinite(size)or not 0<size<=100:raise ValueError('Invalid optical font or point size')
 output.mkdir();data=json.loads((source/'typing-data.json').read_text());w,h=data['atlasSize'];image=Image.frombytes('RGBA',(w,h),gzip.decompress((source/'atlas.rgba.gz').read_bytes()));mapped=data['maps']['text']['symbols'];cached={}
 for token,s in mapped.items():
  if s.get('fontName')and s.get('fontCode')is not None:cached[(s['fontName'],s['fontCode'],round(s['advance'],7))]=(s,data['tiles']['text/'+token])
 for table in data.get('documentFonts',{}).values():
  for symbol in table['symbols'].values():cached[(symbol['fontName'],symbol['fontCode'],round(symbol['advance'],7))]=(symbol,data['tiles'][symbol['key']])
 # Existing shelves occupy at most this y coordinate, including tile gutters.
 uvs=[tile['uv'][3]for tile in data['tiles'].values()]+[p['uv'][3]for phases in data.get('coverage96',{}).values()for p in phases if p];y=math.ceil(max(uvs)*h)+2;x=2;row=0;fonts=dict(data.get('documentFonts',{}));added=0
 for role,(name,size)in specification.items():
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
  refresh_metrics(table,tfm,size)
  fonts[role]=table
 refresh_note_metrics(fonts)
 data['documentFonts']=fonts;(output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(image.tobytes(),mtime=0));(output/'glyph.svg').unlink(missing_ok=True);(output/'glyph.png').unlink(missing_ok=True);print(json.dumps({'newOutlines':added,'rowsUsed':y+row,'fonts':len(fonts)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--generator',type=Path,required=True);p.add_argument('--roles');p.add_argument('--font-spec',type=Path);a=p.parse_args();prepare(a.source,a.output,a.generator,a.roles.split(',')if a.roles else None,json.loads(a.font_spec.read_text())if a.font_spec else None)
