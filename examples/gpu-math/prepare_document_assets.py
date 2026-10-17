"""Prepare source PDF illustration primitives as reusable vector distance fields.

Only supplied illustration PDFs are inputs. The document reference PDF, TeX
compiler and reference page positions are never read. Embedded fonts stay with
the local project artifacts, rather than being added to the shared font bundle.
"""
import argparse,copy,gzip,hashlib,io,json,math,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import pymupdf
import pathops
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from prepare_pdf_vectors import PdfPen

def drawing_path(drawing):
    path=pathops.Path();last=None
    for item in drawing['items']:
        kind=item[0]
        if kind in ['l','c']:
            start=tuple(item[1])
            if last!=start:path.moveTo(*start)
            if kind=='l':path.lineTo(*item[2]);last=tuple(item[2])
            else:path.cubicTo(*item[2],*item[3],*item[4]);last=tuple(item[4])
        elif kind=='re':
            r=item[1];path.moveTo(r.x0,r.y0);path.lineTo(r.x1,r.y0);path.lineTo(r.x1,r.y1);path.lineTo(r.x0,r.y1);path.close();last=None
        elif kind=='qu':
            q=item[1];path.moveTo(*q.ul);path.lineTo(*q.ur);path.lineTo(*q.lr);path.lineTo(*q.ll);path.close();last=None
        else:raise ValueError('Unsupported PDF path item: '+kind)
    if drawing.get('closePath'):path.close()
    path.fillType=pathops.FillType.EVEN_ODD if drawing.get('even_odd')else pathops.FillType.WINDING
    return path

def prepare(pdf,output,generator):
    output.mkdir();doc=pymupdf.open(pdf)
    if len(doc)!=1:raise ValueError('Illustration must have one page')
    page=doc[0];width,height=page.rect.width,page.rect.height
    if page.rotation:raise ValueError('Rotated source PDF page is not supported')
    if page.get_images():raise ValueError('Embedded raster images in PDF illustration are not supported')
    drawings=page.get_drawings(extended=True)
    if any(p['type']=='group'and(p['blendmode']!='Normal'or p['opacity']!=1 or p['knockout'])for p in drawings):raise ValueError('PDF transparency group requires a separate adapter')
    crop=pathops.Path();crop.moveTo(0,0);crop.lineTo(width,0);crop.lineTo(width,height);crop.lineTo(0,height);crop.close()
    for clipping in [p for p in drawings if p['type']=='clip']:
        remainder=pathops.op(crop,drawing_path(clipping),pathops.PathOp.DIFFERENCE)
        if abs(remainder.area)>.0001:raise ValueError('PDF clipping inside the illustration page needs separate runs')
    drawings=[p for p in drawings if p['type']not in['clip','group']]
    runs=[];events=[];fonts={};fields={};traces=page.get_texttrace();text_orders=[s['seqno']for s in traces]
    def append(path,color,order):
        if len(color)!=3:raise ValueError('PDF color must be RGB')
        path=pathops.op(path,crop,pathops.PathOp.INTERSECTION)
        if not path.verbs:return
        if runs and runs[-1]['color']==list(color)and not any(runs[-1]['lastOrder']<n<order for n in text_orders):runs[-1]['path']=pathops.op(runs[-1]['path'],path,pathops.PathOp.UNION);runs[-1]['lastOrder']=order
        else:runs.append({'path':path,'color':list(color),'order':order,'lastOrder':order})
    for drawing in drawings:
        for mode,color in [('fill',drawing.get('fill')),('stroke',drawing.get('color'))]:
            if color is None:continue
            if drawing.get(mode+'_opacity',1)!=1:raise ValueError('Translucent PDF paths are not supported')
            path=drawing_path(drawing)
            if mode=='stroke':
                if drawing['width']<=0:raise ValueError('Device hairline requires an analytic adapter')
                caps=drawing['lineCap']
                if len(set(caps))>1:raise ValueError('Mixed stroke caps are not supported')
                dashes=re.fullmatch(r'\[([^\]]*)\]\s*([-\d.]+)',drawing['dashes'])
                if not dashes:raise ValueError('Unsupported dash pattern')
                dash=[float(n)for n in dashes[1].split()]or None
                path.stroke(drawing['width'],pathops.LineCap(caps[0]),pathops.LineJoin(int(drawing['lineJoin'])),10,dash,float(dashes[2]));path.convertConicsToQuads(.01)
            append(path,color,drawing['seqno'])
    # Runs stop at every interleaved text event; painting order is retained.
    for index,run in enumerate(runs):
        key='path:'+str(index);fields[key]={'path':run['path']};events.append((run['order'],{'kind':'field','key':key,'x':0,'y':0,'color':run['color']+[1]}))
    for xref,ext,kind,name,*_ in page.get_fonts(full=True):
        if ext!='ttf':raise ValueError('Source PDF font requires TrueType outlines: '+name)
        font=TTFont(io.BytesIO(doc.extract_font(xref)[3]));fonts[name.split('+')[-1]]=(font,font.getGlyphSet(),font.getGlyphOrder())
    for span in traces:
        if span['dir']!=(1.,0.)or span['opacity']!=1 or span['type']!=0:raise ValueError('Unsupported PDF text transform or paint')
        name=span['font'].split('+')[-1]
        if name not in fonts:raise ValueError('Missing embedded PDF font: '+name)
        font,glyphs,order=fonts[name];size=span['size'];scale=size/font['head'].unitsPerEm
        for char,gid,origin,bbox in span['chars']:
            if gid<0:
                if char==32:continue
                raise ValueError('Missing source PDF glyph index')
            key=f'font:{name}:{gid}:{size:.8f}'
            if key not in fields:
                path=pathops.Path();glyphs[order[gid]].draw(TransformPen(path.getPen(),(scale,0,0,-scale,0,0)))
                if not path.verbs:continue
                fields[key]={'path':path}
            events.append((span['seqno'],{'kind':'glyph','key':key,'x':origin[0],'y':origin[1],'color':list(span['color'])+[1],'nativeGlyph':{'fontName':name.lower(),'glyphName':order[gid],'fontGlyphId':gid,'fontSize':size,'unicode':chr(char)}}))
    # One local atlas per illustration. Every field retains its own world plane.
    atlas_width=4096;placements={};shelves=[];bottom=2;field_scale=6;padding=6
    for key,field in fields.items():
        l,t,r,b=field['path'].bounds;field['bounds']=(l,t,r,b);field['size']=(math.ceil((r-l)*field_scale)+2*padding,math.ceil((b-t)*field_scale)+2*padding)
    for key,field in sorted(fields.items(),key=lambda p:(-p[1]['size'][1],-p[1]['size'][0])):
        w,h=field['size']
        if w+4>atlas_width:raise ValueError('Illustration field exceeds atlas width')
        shelf=next((s for s in shelves if s['x']+w+2<=atlas_width),None)
        if shelf is None:shelf={'x':2,'y':bottom};shelves.append(shelf);bottom+=h+2
        placements[key]=(shelf['x'],shelf['y']);shelf['x']+=w+2
    atlas_height=2**math.ceil(math.log2(max(4,bottom)))
    if atlas_height>8192:raise ValueError('Illustration atlas limit: 4096x8192')
    atlas=Image.new('RGBA',(atlas_width,atlas_height));tiles={};vectors={}
    for key,field in fields.items():
        path=field['path'];path.convertConicsToQuads(.01);pen=SVGPathPen(None);path.draw(pen);l,t,r,b=field['bounds'];w,h=field['size'];x,y=placements[key]
        pdf_pen=PdfPen();path.draw(pdf_pen);vectors[key]={'bounds':[l,t,r,b],'operators':'\n'.join(pdf_pen.commands)}
        svg=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg','viewBox':f'{l} {t} {r-l} {b-t}'});ET.SubElement(svg,'path',{'d':pen.getCommands()});ET.ElementTree(svg).write(output/'field.svg',encoding='unicode')
        subprocess.run([str(generator),'mtsdf','-svg',str(output/'field.svg'),'-dimensions',str(w),str(h),'-scale',str(field_scale),'-translate',str(1-l),str(1-t),'-pxrange','8','-scanline','-overlap','-o',str(output/'field.png')],capture_output=True,check=True)
        atlas.paste(Image.open(output/'field.png').convert('RGBA'),(x,y));tiles[key]={'plane':[l-1,t-1,l+(w-padding)/field_scale,t+(h-padding)/field_scale],'uv':[x/atlas_width,y/atlas_height,(x+w)/atlas_width,(y+h)/atlas_height]}
    spec={'schema':'vkf.document-vector-asset/1','widthBp':width,'heightBp':height,'atlasSize':[atlas_width,atlas_height],'tiles':tiles,'items':[item for _,item in sorted(events,key=lambda v:v[0])],'source':{'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'name':pdf.name,'scope':'Supplied source illustration only; embedded font outlines and opaque paths, independent of the document reference PDF.'}}
    spec['vectors']=vectors
    (output/'asset.json').write_text(json.dumps(spec,separators=(',',':')));(output/'atlas.rgba.gz').write_bytes(gzip.compress(atlas.tobytes(),mtime=0));(output/'field.svg').unlink(missing_ok=True);(output/'field.png').unlink(missing_ok=True)
    print(json.dumps({'asset':pdf.name,'fields':len(fields),'items':len(events),'atlasSize':spec['atlasSize']}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('pdf',type=Path);p.add_argument('output',type=Path);p.add_argument('--generator',type=Path,required=True);a=p.parse_args();prepare(a.pdf,a.output,a.generator)
