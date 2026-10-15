"""Pack development-oracle outlines into reusable MTSDF tiles for live typing."""
import argparse,gzip,json,math,os,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from fontTools.pens.boundsPen import BoundsPen
from fontTools.svgLib.path import parse_path
from tex_font_metrics import load_tex_tfm as TFM

def prepare(root,output,generator,extras=None):
    if output.exists():raise ValueError('Use a fresh output directory')
    output.mkdir(parents=True);maps={};tiles={};atlas_width=4096;atlas_height=8192
    atlas=Image.new('RGBA',(atlas_width,atlas_height));x=y=2;row=0;cached={};font_cache={}
    env=os.environ.copy()
    if extras:
        for variable in ['TEXINPUTS','TFMFONTS','TEXFONTS','T1FONTS']:env[variable]=str(extras.resolve())+'//:'
    # Height-sorted shelves avoid wasting rows on unusually tall extension pieces.
    outlines={};placements={};shelves=[];next_y=2
    for style in ['display','text','script','scriptscript']:
        for symbol in json.loads((root/f'typing-{style}/symbol-mapping.json').read_text())['symbols'].values():
            if symbol['outlineHash'] in outlines:continue
            pen=BoundsPen(None);parse_path(symbol['outline']['svgPath'],pen);left,top,right,bottom=pen.bounds
            outlines[symbol['outlineHash']]=(math.ceil((right-left)*12)+12,math.ceil((bottom-top)*12)+12)
    for digest,(width,height) in sorted(outlines.items(),key=lambda entry:(-entry[1][1],-entry[1][0])):
        shelf=next((r for r in shelves if r['x']+width+2<=atlas_width),None)
        if shelf is None:
            if next_y+height+2>atlas_height:raise ValueError('Atlas overflow')
            shelf={'x':2,'y':next_y};shelves.append(shelf);next_y+=height+2
        placements[digest]=(shelf['x'],shelf['y']);shelf['x']+=width+2
    for style in ['display','text','script','scriptscript']:
        mapping=json.loads((root/f'typing-{style}/symbol-mapping.json').read_text());mapping['style']=style;mapping['limits']=['Measured standard glyphs and composite symbols only; expression layout is a separate runtime.','Box metrics include measured italic correction; expression layout needs separate validation.']
        for index,(token,s) in enumerate(mapping['symbols'].items()):
            folder=root/f'typing-{style}'/str(index)
            tree=ET.parse(folder/'expression.svg');uses=[e for e in tree.getroot().iter() if e.tag.endswith('}use')]
            s['italic']=0;s['skew']=0
            if len(uses)==1:
                font_info=re.search(r'Font \d+: ([^\s-]+)(?: scaled \d+)?---loaded at size (\d+) DVI units',subprocess.check_output(['dvitype','--output-level=0',str(folder/'expression.dvi')],text=True,env=env));font_name=font_info[1]
                if font_name not in font_cache:font_cache[font_name]=TFM(subprocess.check_output(['kpsewhich',font_name+'.tfm'],text=True,env=env).strip())
                code=int(uses[0].attrib['{http://www.w3.org/1999/xlink}href'].split('-')[-1])
                # Actual DVI loaded size, including scaled extension/integral fonts.
                scale=int(font_info[2])/65536*72/72.27
                s['italic']=font_cache[font_name].chars[code].get('italic',0)*scale
                s['advance']=font_cache[font_name].chars[code]['width']*scale
                s['fontXHeight']=font_cache[font_name].fontdimens.get('XHEIGHT',0)*scale
                s['fontCode']=code;s['fontName']=font_name
                s['nextLarger']=font_cache[font_name].chars[code].get('nextlarger')
                s['extension']=font_cache[font_name].chars[code].get('varchar')
                s['kerns']={str(c):v*scale for c,v in font_cache[font_name].kerning.get(code,{}).items()}
                s['skew']=font_cache[font_name].kerning.get(code,{}).get(127,0)*scale if font_name.startswith(('cmmi','rsfs')) else 0
            pen=BoundsPen(None);parse_path(s['outline']['svgPath'],pen);left,top,right,bottom=pen.bounds;s['inkBounds']=[left,top,right,bottom]
            key=f'{style}/{token}';outline_hash=s['outlineHash']
            if outline_hash not in cached:
                scale=12;padding=6;width=math.ceil((right-left)*scale)+2*padding;height=math.ceil((bottom-top)*scale)+2*padding
                x,y=placements[outline_hash]
                svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','viewBox':f'{left} {top} {right-left} {bottom-top}'})
                ET.SubElement(svg,'path',{'d':s['outline']['svgPath']});ET.ElementTree(svg).write(output/'tile.svg',encoding='unicode')
                subprocess.run([str(generator),'mtsdf','-svg',str(output/'tile.svg'),'-dimensions',str(width),str(height),'-scale',str(scale),'-translate',str(padding/scale-left),str(padding/scale-top),'-pxrange','8','-scanline','-overlap','-o',str(output/'tile.png')],capture_output=True,text=True,check=True)
                bitmap=Image.open(output/'tile.png').convert('RGBA');atlas.paste(bitmap,(x,y))
                cached[outline_hash]={'plane':[left-padding/scale,top-padding/scale,left+(width-padding)/scale,top+(height-padding)/scale],
                    'uv':[x/atlas_width,y/atlas_height,(x+width)/atlas_width,(y+height)/atlas_height]}

            tiles[key]=cached[outline_hash];s.pop('outline');s.pop('outlineHash')
        if '@ext:112' in mapping['symbols']:
            mapping['parameters']['RULE']=mapping['symbols']['@ext:112']['height']
        size=10 if style in ['display','text']else 7 if style=='script'else 5
        bold_font=TFM(subprocess.check_output(['kpsewhich',f'cmbsy{size}.tfm'],text=True,env=env).strip())
        mapping['boldParameters']={**mapping['parameters'],**{name:value*size*72/72.27 for name,value in bold_font.fontdimens.items()}}
        roman_font=TFM(subprocess.check_output(['kpsewhich',f'cmr{size}.tfm'],text=True,env=env).strip())
        mapping['textSpace']=roman_font.fontdimens['SPACE']*size*72/72.27
        mapping['textExtraSpace']=roman_font.fontdimens.get('EXTRASPACE',0)*size*72/72.27
        mapping['textFontSpaces']={}
        for family in ['mathrm','mathbf','mathit','mathsf','mathtt']:
            role=mapping['symbols'].get('@font:'+family+':A')
            if role:
                font=font_cache[role['fontName']];unit=role['advance']/font.chars[role['fontCode']]['width']
                mapping['textFontSpaces'][family]={key.lower():font.fontdimens.get(key,0)*unit for key in ['SPACE','STRETCH','SHRINK','EXTRASPACE']}
        maps[style]=mapping
    atlas.save(output/'atlas.png');(output/'atlas.rgba').write_bytes(atlas.tobytes());(output/'atlas.rgba.gz').write_bytes(gzip.compress(atlas.tobytes(),mtime=0))
    (output/'typing-data.json').write_text(json.dumps({'maps':maps,'tiles':tiles,'atlasSize':[atlas_width,atlas_height],'range':8},separators=(',',':')))
    (output/'tile.svg').unlink();(output/'tile.png').unlink();print(json.dumps({'tiles':len(tiles),'uniqueOutlines':len(cached),'rowsUsed':next_y}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--generator',type=Path,required=True);p.add_argument('--oracle-extras',type=Path)
    a=p.parse_args();prepare(a.root,a.output,a.generator,a.oracle_extras)
