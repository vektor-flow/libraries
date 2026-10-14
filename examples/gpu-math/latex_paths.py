"""Real LaTeX -> DVI -> vector paths -> GPU-ready geometry + expression MTSDF.

This first slice accepts black filled paths, uses and rectangles on one page.
Unsupported paint/clip/image features fail explicitly, rather than disappearing.
"""
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from fontTools.misc.transform import Transform, Identity
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path

XLINK = '{http://www.w3.org/1999/xlink}href'
NUMBER = r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def transform(value):
    result = Identity
    rest = value
    for match in re.finditer(r'(matrix|translate|scale)\s*\(([^)]*)\)', value):
        if rest[:match.start()].strip():
            raise ValueError('Unsupported SVG transform')
        # Mark parsed sections without changing string offsets.
        rest = rest[:match.start()] + ' '*(match.end()-match.start()) + rest[match.end():]
        nums = [float(v) for v in re.findall(NUMBER, match[2])]
        if re.sub(NUMBER,'',match[2]).strip(' ,\t\n') or not all(map(math.isfinite,nums)):
            raise ValueError('Invalid transform values')
        if match[1]=='matrix' and len(nums)==6:
            local = Transform(*nums)
        elif match[1]=='translate' and len(nums) in (1,2):
            local = Identity.translate(nums[0],nums[1] if len(nums)==2 else 0)
        elif match[1]=='scale' and len(nums) in (1,2):
            local = Identity.scale(nums[0],nums[1] if len(nums)==2 else nums[0])
        else:
            raise ValueError('Unsupported SVG transform arity')
        result = result.transform(local)
    if rest.strip():
        raise ValueError('Unsupported SVG transform')
    return result


def extract(svg):
    root = ET.fromstring(svg)
    view = [float(v) for v in root.attrib['viewBox'].split()]
    if len(view)!=4 or not all(map(math.isfinite,view)) or min(view[2:])<=0:
        raise ValueError('Invalid viewBox')
    definitions = {e.attrib['id']:e for e in root.iter() if 'id' in e.attrib}
    primitives = []
    outlines = {}
    combined = SVGPathPen(None)
    origin = Identity.translate(-view[0],-view[1])

    def emit(d, placement, kind, source_id=None):
        key = digest(d.encode())
        pen = RecordingPen()
        parse_path(d, pen)
        for _, points in pen.value:
            if not all(math.isfinite(c) for point in points if point for c in point):
                raise ValueError('Non-finite path coordinate')
        outlines.setdefault(key,{'svgPath':d,'commands':pen.value})
        placed = origin.transform(placement)
        parse_path(d,TransformPen(combined,placed))
        primitives.append({'id':f'primitive-{len(primitives)}','kind':kind,
            'outline':key,'transform':list(placed),'sourceId':source_id})

    def walk(e, parent=Identity, active=()):
        tag = e.tag.rsplit('}',1)[-1]
        if tag=='defs':
            return
        allowed = {'id','transform','fill','d','x','y','width','height','version','viewBox',XLINK,'href'}
        # Metadata on root is harmless; painted elements are intentionally strict.
        if tag!='svg' and any(k not in allowed for k in e.attrib):
            raise ValueError(f'Unsupported SVG attributes on {tag}: {set(e.attrib)-allowed}')
        if e.attrib.get('fill','black') not in ('black','#000','#000000'):
            raise ValueError('This slice supports black filled geometry only')
        local = parent.transform(transform(e.attrib.get('transform','')))
        if tag in ('svg','g'):
            for child in e:
                walk(child,local,active)
        elif tag=='use':
            href=e.attrib.get(XLINK,e.attrib.get('href',''))
            if not href.startswith('#') or href[1:] not in definitions or href in active:
                raise ValueError('Unresolved/cyclic SVG use')
            shift=Identity.translate(float(e.attrib.get('x',0)),float(e.attrib.get('y',0)))
            walk(definitions[href[1:]],local.transform(shift),active+(href,))
        elif tag=='path':
            emit(e.attrib['d'],local,'path',e.attrib.get('id'))
        elif tag=='rect':
            x,y,w,h=[float(e.attrib.get(k,0)) for k in ('x','y','width','height')]
            if not all(map(math.isfinite,[x,y,w,h])) or w<0 or h<0:
                raise ValueError('Invalid rectangle')
            if w and h:
                emit(f'M{x} {y}H{x+w}V{y+h}H{x}Z',local,'rule')
        else:
            raise ValueError(f'Unsupported SVG element: {tag}')

    walk(root)
    if not primitives:
        raise ValueError('No drawable geometry')
    packet={'schema':'vkf.latex-path-packet/1','units':'SVG pt (1/72 inch), top-down',
        'sourceViewBox':view,'bounds':[0,0,view[2],view[3]],'outlines':outlines,
        'primitives':primitives,'fillRule':'nonzero','combinedPath':combined.getCommands()}
    return packet


def compile_expression(source, output, engine, converter, generator, document=False):
    if output.exists():
        raise ValueError('Use a fresh output directory; existing evidence is preserved')
    output.mkdir(parents=True)
    body=source.read_text()
    text=body if document else (
        '\\documentclass{article}\n\\usepackage{amsmath,amssymb}\n\\pagestyle{empty}\n'
        '\\begin{document}\n\\noindent $\\displaystyle\n'+body+
        '$\n\\end{document}\n')
    (output/'expression.tex').write_text(text)
    commands=[]
    fontmap=subprocess.run(['kpsewhich','pdftex.map'],capture_output=True,text=True,check=True).stdout.strip()
    if not fontmap or not Path(fontmap).is_file():
        raise ValueError('A resolved pdftex.map is required for this standard-font slice')
    def run(args, name):
        command=[str(a) for a in args]
        commands.append(command)
        proc=subprocess.run(command,cwd=output,capture_output=True,text=True,timeout=60)
        (output/f'{name}.stdout.log').write_text(proc.stdout)
        (output/f'{name}.stderr.log').write_text(proc.stderr)
        if proc.returncode:
            raise RuntimeError(f'{name} failed: inspect {output}')
        return proc.stdout
    run([engine,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error',
        '-recorder','expression.tex'],'latex')
    # Check one page before converting. Empty page templates can produce extras.
    output_log=(output/'expression.log').read_text(errors='replace')
    if not re.search(r'Output written on expression\.dvi \(1 page,', output_log):
        raise ValueError('This slice requires exactly one DVI page')
    run([converter,'--no-fonts=0','--exact-bbox','--precision=8',
        f'--fontmap={fontmap}','--output=expression.svg','expression.dvi'],'dvisvgm')
    converter_log=(output/'dvisvgm.stderr.log').read_text()
    if re.search(r'warning|unsupported|ignored|missing|not found',converter_log,re.IGNORECASE):
        raise ValueError('Converter reported a possible omission; inspect its log')
    packet=extract((output/'expression.svg').read_text())
    (output/'path-packet.json').write_text(json.dumps(packet,indent=2)+'\n')
    w,h=packet['bounds'][2:]
    # One combined filled path is essential: bare msdfgen -svg only imports
    # the last path. Every LaTeX use/rule has been expanded and placed first.
    normalized=ET.Element('svg',{'xmlns':'http://www.w3.org/2000/svg',
        'viewBox':f'0 0 {w} {h}'})
    ET.SubElement(normalized,'path',{'d':packet['combinedPath']})
    ET.ElementTree(normalized).write(output/'normalized.svg',encoding='unicode')
    scale,padding=8,8
    width,height=math.ceil(w*scale)+2*padding,math.ceil(h*scale)+2*padding
    run([generator,'mtsdf','-svg','normalized.svg','-dimensions',width,height,
        '-scale',scale,'-translate',padding/scale,padding/scale,'-pxrange',8,
        '-overlap','-scanline','-seed',0,'-printmetrics','-o','expression-mtsdf.png'],'msdfgen')
    from PIL import Image
    with Image.open(output/'expression-mtsdf.png') as bitmap:
        if bitmap.mode!='RGBA' or bitmap.size!=(width,height):
            raise ValueError('Invalid expression MTSDF bitmap')
        (output/'expression-mtsdf.rgba').write_bytes(bitmap.tobytes())
    # Record actual tool bytes, engine identity, recorder inputs and Type1 fonts.
    versions={name:subprocess.run([str(tool),'--version'],capture_output=True,text=True).stdout.strip()
        for name,tool in [('latex',engine),('dvisvgm',converter)]}
    inputs={}
    for line in (output/'expression.fls').read_text().splitlines():
        if line.startswith('INPUT '):
            path=Path(line[6:])
            if not path.is_absolute():
                path=output/path
            if path.is_file():
                inputs[str(path.resolve())]=digest(path.read_bytes())
    dvi_fonts=run(['dvitype','--output-level=0','expression.dvi'],'dvitype')
    font_names=set(re.findall(r'Font \d+: ([^\s-]+)',dvi_fonts))
    map_text=Path(fontmap).read_text()
    inputs[fontmap]=digest(Path(fontmap).read_bytes())
    font_files={}
    for name in sorted(font_names):
        entries=[line for line in map_text.splitlines() if line.split() and line.split()[0]==name]
        if len(entries)!=1:
            raise ValueError(f'Expected one explicit standard-font mapping for {name}')
        filenames=[name+'.tfm']+re.findall(r'<<?([^\s<>]+\.(?:pfb|enc))',entries[0])
        resolved=[]
        for filename in filenames:
            location=subprocess.run(['kpsewhich',filename],capture_output=True,text=True,check=True).stdout.strip()
            if not location or not Path(location).is_file():
                raise ValueError(f'Cannot resolve standard font input {filename}')
            inputs[location]=digest(Path(location).read_bytes())
            resolved.append(location)
        font_files[name]={'mapEntry':entries[0],'files':resolved}
    texture={'type':'mtsdf','format':'linear rgba8unorm','size':[width,height],
        'shapeUnitsPerTexel':1/scale,'paddingTexels':padding,'distanceRangeTexels':8,
        'zero':0.5,'sign':'positive inside','alpha':'true distance, not coverage',
        'image':'expression-mtsdf.png','quadBounds':[-padding/scale,-padding/scale,
            (width-padding)/scale,(height-padding)/scale]}
    receipt={'schema':'vkf.latex-field-build/1','sourceSha256':digest(source.read_bytes()),
        'documentSha256':digest(text.encode()),'versions':versions,'commands':commands,
        'toolSha256':{str(t):digest(Path(t).read_bytes()) for t in [engine,converter,generator]},
        'inputFiles':inputs,'fontMappings':font_files,'texture':texture,
        'counts':{'primitives':len(packet['primitives']),'uniqueOutlines':len(packet['outlines']),
            'rules':sum(p['kind']=='rule' for p in packet['primitives'])},
        'outputs':{name:digest((output/name).read_bytes()) for name in
            ['expression.dvi','expression.svg','normalized.svg','path-packet.json','expression-mtsdf.png','expression-mtsdf.rgba']},
        'limits':['Real TeX Live LaTeX verified; MiKTeX not installed or verified.',
            'One page, black filled paths/uses/rectangles only; other features rejected.',
            'CPU preparation; finite sampled distance texture; no GPU execution or VKF integration.']}
    (output/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt['counts']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--engine',default='latex')
    parser.add_argument('--converter',default='dvisvgm')
    parser.add_argument('--generator',type=Path,required=True)
    parser.add_argument('--document',action='store_true',help='Input is a full LaTeX document instead of math body')
    args=parser.parse_args()
    def executable(name):
        found=shutil.which(str(name))
        if not found:
            raise ValueError(f'Executable unavailable: {name}')
        return Path(found).absolute()  # Preserve latex alias: argv[0] selects the TeX format.
    compile_expression(args.source.resolve(),args.output.resolve(),executable(args.engine),
        executable(args.converter),executable(args.generator),args.document)
