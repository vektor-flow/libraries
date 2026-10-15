"""Replace PK-derived text-companion outlines with reusable CM-Super Type1 fields.
Native TFM advances, boxes and DVI placements are preserved. PDF references stay
unchanged; their historical Type3 bitmap rasterization remains independent.
"""
import argparse,gzip,json,math,re,subprocess
from pathlib import Path
from PIL import Image
from fontTools.t1Lib import T1Font
from tex_font_metrics import load_tex_tfm as TFM
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
import xml.etree.ElementTree as ET

def prepare(source,output,fontdir,generator,add_text_bullet=False):
 output.mkdir();data=json.loads((source/'typing-data.json').read_text());w,h=data['atlasSize'];atlas=Image.frombytes('RGBA',(w,h),gzip.decompress((source/'atlas.rgba.gz').read_bytes()));uvs=[p['uv'][3]for p in data['tiles'].values()]+[p['uv'][3]for phases in data.get('coverage96',{}).values()for p in phases if p];x=2;y=math.ceil(max(uvs)*h)+2;row=0;encoding_path=fontdir/'cm-super-ts1.enc' if(fontdir/'cm-super-ts1.enc').exists()else fontdir/'fonts/enc/dvips/cm-super/cm-super-ts1.enc';text=re.sub('%[^\n]*','',encoding_path.read_text());encoding=re.findall(r'/([^\s/\[\]]+)',text[text.index('[')+1:text.index(']')]);fonts={};cached={};updated=[]
 if add_text_bullet:
  for style,m in data['maps'].items():
   if '@text:bullet' in m['symbols']:continue
   name='tcrm'+('0500'if style=='scriptscript'else'0700'if style=='script'else'1000');tfm=TFM(subprocess.check_output(['kpsewhich',name+'.tfm'],text=True).strip());size=m['em'];code=136;metric=tfm.chars[code];advance=metric['width']*size
   m['symbols']['@text:bullet']={'class':'ord','width':advance,'advance':advance,'height':metric.get('height',0)*size,'depth':metric.get('depth',0)*size,'italic':0,'fontName':name,'fontCode':code,'oracleToken':'\\textbullet','kerns':{},'glyphParts':[{'fontName':name,'fontCode':code,'fontSize':size,'x':0,'y':0,'advance':advance}]}
 for style,m in data['maps'].items():
  for token,s in m['symbols'].items():
   name=s.get('fontName')
   if not name or not name.startswith('tcrm')or s.get('vectorFontSource'):continue
   code=s['fontCode'];identity=(name,code);key=style+'/'+token
   if identity not in cached:
    if name not in fonts:
     p=fontdir/('sfrm'+name[4:]+'.pfb')if(fontdir/('sfrm'+name[4:]+'.pfb')).exists()else fontdir/'fonts/type1/public/cm-super'/('sfrm'+name[4:]+'.pfb');font=T1Font(str(p));tfm=TFM(subprocess.check_output(['kpsewhich',name+'.tfm'],text=True).strip());fonts[name]=(font,tfm,p.name)
    font,tfm,pfb=fonts[name];size=s['advance']/tfm.chars[code]['width'];glyph=font.getGlyphSet()[encoding[code]];parts=s.get('glyphParts')or[{'x':0,'y':0}];dx,dy=parts[0]['x'],parts[0]['y'];transform=(size/1000,0,0,-size/1000,dx,dy);pen=SVGPathPen(None);glyph.draw(TransformPen(pen,transform));bounds=BoundsPen(None);glyph.draw(TransformPen(bounds,transform));left,top,right,bottom=bounds.bounds;tw=math.ceil((right-left)*12)+12;th=math.ceil((bottom-top)*12)+12
    if x+tw+2>w:x=2;y+=row+2;row=0
    if y+th+2>h:raise ValueError('Vector text companion atlas overflow')
    svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','viewBox':f'{left} {top} {right-left} {bottom-top}'});ET.SubElement(svg,'path',{'d':pen.getCommands()});ET.ElementTree(svg).write(output/'glyph.svg',encoding='unicode');subprocess.run([str(generator),'mtsdf','-svg',str(output/'glyph.svg'),'-dimensions',str(tw),str(th),'-scale','12','-translate',str(.5-left),str(.5-top),'-pxrange','8','-scanline','-overlap','-o',str(output/'glyph.png')],capture_output=True,check=True);atlas.paste(Image.open(output/'glyph.png').convert('RGBA'),(x,y));cached[identity]=({'uv':[x/w,y/h,(x+tw)/w,(y+th)/h],'plane':[left-.5,top-.5,left+(tw-6)/12,top+(th-6)/12]},[left,top,right,bottom],pfb);x+=tw+2;row=max(row,th)
   tile,ink,pfb=cached[identity];data['tiles'][key]=tile;s['inkBounds']=ink;s['vectorFontSource']={'program':pfb,'encoding':'cm-super-ts1.enc','nativeMetrics':name};updated.append(key)
 data['vectorTextCompanion']={'source':'CM-Super 0.3.4; native TFM metrics retained','updatedKeys':list(dict.fromkeys(data.get('vectorTextCompanion',{}).get('updatedKeys',[])+updated)),'rowsUsed':y+row if updated else data.get('vectorTextCompanion',{}).get('rowsUsed',y)};(output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(atlas.tobytes(),mtime=0));(output/'glyph.svg').unlink(missing_ok=True);(output/'glyph.png').unlink(missing_ok=True);print(json.dumps({'updatedKeys':len(updated),'outlines':len(cached),'rowsUsed':y+row}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--font-directory',type=Path,required=True);p.add_argument('--generator',type=Path,required=True);p.add_argument('--add-text-bullet',action='store_true');a=p.parse_args();prepare(a.source,a.output,a.font_directory,a.generator,a.add_text_bullet)
