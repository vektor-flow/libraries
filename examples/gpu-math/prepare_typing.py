"""Pack development-oracle outlines into reusable MTSDF tiles for live typing."""
import argparse,gzip,json,math,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path

def prepare(root,output,generator):
    if output.exists():raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True);maps={};tiles={};atlas=Image.new('RGBA',(2048,2048));x=y=2;row=0
    for style in ['display','script','scriptscript']:
        mapping=json.loads((root/f'typing-{style}/symbol-mapping.json').read_text());mapping['style']=style
        from fontTools.tfmLib import TFM
        font_cache={}
        for index,(token,s) in enumerate(mapping['symbols'].items()):
            folder=root/f'typing-{style}'/str(index)
            font_name=re.search(r'Font \d+: ([^\s-]+)',subprocess.check_output(['dvitype','--output-level=0',str(folder/'expression.dvi')],text=True))[1]
            if font_name not in font_cache: font_cache[font_name]=TFM(subprocess.check_output(['kpsewhich',font_name+'.tfm'],text=True).strip())
            tree=ET.parse(folder/'expression.svg')
            path=next(e for e in tree.getroot().iter() if e.tag.endswith('}path'))
            code=int(path.attrib['id'].split('-')[-1])
            s['italic']=font_cache[font_name].chars[code].get('italic',0)*mapping['em']
            pen=BoundsPen(None);parse_path(s['outline']['svgPath'],pen);left,top,right,bottom=pen.bounds
            scale=12;padding=6;width=math.ceil((right-left)*scale)+2*padding;height=math.ceil((bottom-top)*scale)+2*padding
            if x+width+2>2048:x=2;y+=row+2;row=0
            if y+height+2>2048:raise ValueError('Atlas overflow')
            key=f'{style}/{token}';svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','viewBox':f'{left} {top} {right-left} {bottom-top}'})
            ET.SubElement(svg,'path',{'d':s['outline']['svgPath']});ET.ElementTree(svg).write(output/'tile.svg',encoding='unicode')
            proc=subprocess.run([str(generator),'mtsdf','-svg',str(output/'tile.svg'),'-dimensions',str(width),str(height),'-scale',str(scale),'-translate',str(padding/scale-left),str(padding/scale-top),'-pxrange','8','-scanline','-overlap','-o',str(output/'tile.png')],capture_output=True,text=True,check=True)
            bitmap=Image.open(output/'tile.png').convert('RGBA');atlas.paste(bitmap,(x,y))
            tiles[key]={'plane':[left-padding/scale,top-padding/scale,left+(width-padding)/scale,top+(height-padding)/scale],
                'uv':[x/2048,y/2048,(x+width)/2048,(y+height)/2048]}
            # Browser layout needs metric data only, not duplicated vector paths.
            s.pop('outline');s.pop('outlineHash')
            x+=width+2;row=max(row,height)
        maps[style]=mapping
    atlas.save(output/'atlas.png');(output/'atlas.rgba').write_bytes(atlas.tobytes());(output/'atlas.rgba.gz').write_bytes(gzip.compress(atlas.tobytes(),mtime=0))
    (output/'typing-data.json').write_text(json.dumps({'maps':maps,'tiles':tiles,'atlasSize':[2048,2048],'range':8},separators=(',',':')))
    (output/'tile.svg').unlink();(output/'tile.png').unlink();print(json.dumps({'tiles':len(tiles),'rowsUsed':y+row}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--generator',type=Path,required=True)
    a=p.parse_args();prepare(a.root,a.output,a.generator)
