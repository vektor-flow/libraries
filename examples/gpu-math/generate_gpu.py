"""Generate GPU segment data and executable ESM from real LaTeX path packets."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from fontTools.pens.basePen import BasePen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform
from fontTools.svgLib.path import parse_path


def distance_to_chord(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)


def midpoint(a,b):
    return ((a[0]+b[0])/2,(a[1]+b[1])/2)


class Segments(BasePen):
    def __init__(self,tolerance):
        super().__init__(None)
        self.tolerance=tolerance
        self.segments=[]
        self.start=self.current=None
    def _moveTo(self,p):
        self.start=self.current=p
    def _lineTo(self,p):
        if p!=self.current:
            self.segments.append((*self.current,*p))
        self.current=p
    def flatten(self,points,depth=0):
        if max(distance_to_chord(p,points[0],points[-1]) for p in points[1:-1])<=self.tolerance:
            self._lineTo(points[-1])
            return
        if depth>=24:
            raise ValueError('Curve subdivision budget exceeded')
        levels=[points]
        while len(levels[-1])>1:
            row=levels[-1]
            levels.append([midpoint(a,b) for a,b in zip(row,row[1:])])
        self.flatten([row[0] for row in levels],depth+1)
        self.flatten([row[-1] for row in reversed(levels)],depth+1)
    def _curveToOne(self,a,b,c):
        self.flatten([self.current,a,b,c])
    def _qCurveToOne(self,a,b):
        self.flatten([self.current,a,b])
    def _closePath(self):
        self._lineTo(self.start)
    def _endPath(self):
        raise ValueError('Open contours are unsupported by the filled-geometry generator')


def generate(packet_path,output,tolerance=.01,texels_per_unit=8):
    if output.exists():
        raise ValueError('Use a fresh output directory')
    if not math.isfinite(tolerance) or tolerance<=0 or not math.isfinite(texels_per_unit) or texels_per_unit<=0:
        raise ValueError('Tolerance and texel scale must be finite and positive')
    packet=json.loads(packet_path.read_text())
    if packet['schema']!='vkf.latex-path-packet/1' or packet['fillRule']!='nonzero':
        raise ValueError('Unsupported source packet')
    pen=Segments(tolerance)
    for p in packet['primitives']:
        parse_path(packet['outlines'][p['outline']]['svgPath'],TransformPen(pen,Transform(*p['transform'])))
    if not pen.segments or len(pen.segments)>100000:
        raise ValueError('Segment budget exceeded or empty geometry')
    data=b''.join(struct.pack('<4f',*segment) for segment in pen.segments)
    unpacked=list(struct.iter_unpack('<4f',data))
    if not all(math.isfinite(v) for segment in unpacked for v in segment):
        raise ValueError('Segment coordinates exceed float32 range')
    quant_error=max(math.hypot(s[i]-q[i],s[i+1]-q[i+1]) for s,q in zip(pen.segments,unpacked) for i in (0,2))
    w,h=packet['bounds'][2:]
    padding=8
    width,height=math.ceil(w*texels_per_unit)+2*padding,math.ceil(h*texels_per_unit)+2*padding
    if max(width,height)>4096:
        raise ValueError('Texture dimension budget exceeded')
    texture={'type':'sdf','format':'linear rgba8unorm','size':[width,height],
        'distanceRangeTexels':8,'shapeUnitsPerTexel':1/texels_per_unit,'paddingTexels':padding,
        'quadBounds':[-padding/texels_per_unit,-padding/texels_per_unit,
            (width-padding)/texels_per_unit,(height-padding)/texels_per_unit]}
    # Conservative distance bins and scanline crossings avoid a full edge scan
    # per texel. Only geometry compilation prepares these; pixels are GPU-built.
    tile=16
    columns=math.ceil(width/tile); rows=math.ceil(height/tile)
    bins=[[] for _ in range(columns*rows)]
    crossing_rows=[[] for _ in range(height)]
    for index,(ax,ay,bx,by) in enumerate(unpacked):
        radius=4/texels_per_unit
        left=max(0,math.floor(((min(ax,bx)-radius)*texels_per_unit+padding)/tile))
        right=min(columns-1,math.floor(((max(ax,bx)+radius)*texels_per_unit+padding)/tile))
        top=max(0,math.floor(((min(ay,by)-radius)*texels_per_unit+padding)/tile))
        bottom=min(rows-1,math.floor(((max(ay,by)+radius)*texels_per_unit+padding)/tile))
        for ty in range(top,bottom+1):
            for tx in range(left,right+1): bins[ty*columns+tx].append(index)
        if ay!=by:
            first=max(0,math.ceil(min(ay,by)*texels_per_unit+padding-.5))
            last=min(height-1,math.ceil(max(ay,by)*texels_per_unit+padding-.5)-1)
            for py in range(first,last+1):
                y=(py+.5-padding)/texels_per_unit
                x=ax+(y-ay)*(bx-ax)/(by-ay)
                crossing_rows[py].append((x,1 if by>ay else -1))
    ranges=[]; indices=[]
    for bucket in bins:
        ranges.append((len(indices),len(bucket)));indices.extend(bucket)
    row_ranges=[]; crossings=[]
    for row in crossing_rows:
        row_ranges.append((len(crossings),len(row)))
        winding=0
        for x,delta in sorted(row):
            winding+=delta;crossings.append((x,winding))
    assets={'segments.bin':data,
        'tile-ranges.bin':b''.join(struct.pack('<2I',*v) for v in ranges),
        'tile-indices.bin':struct.pack('<'+'I'*len(indices),*indices),
        'row-ranges.bin':b''.join(struct.pack('<2I',*v) for v in row_ranges),
        'crossings.bin':b''.join(struct.pack('<2f',*v) for v in crossings)}
    metadata={'schema':'vkf.generated-latex-gpu/1','sourcePacketSha256':hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        'segmentSha256':hashlib.sha256(data).hexdigest(),'segmentCount':len(pen.segments),
        'assets':{name:hashlib.sha256(value).hexdigest() for name,value in assets.items()},
        'tileSize':tile,'tileColumns':columns,'maxTileSegments':max(map(len,bins)),
        'segmentStrideBytes':16,'coordinates':'top-down SVG pt, positive distance inside',
        'curveToleranceUnits':tolerance,'float32EndpointMaxErrorUnits':quant_error,'texture':texture,
        'limits':['Distance is to flattened line segments, not exact original Bezier curves.',
            'Distance uses conservative local bins; winding uses float32 scanline crossing lookup.',
            'Boundary rounding/quantization may affect small counters and thin features.']}
    output.mkdir(parents=True)
    for name,value in assets.items(): (output/name).write_bytes(value)
    (output/'gpu-manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    here=Path(__file__).parent
    for filename in ['compute-field.wgsl','mtsdf.wgsl','gpu-generated-runtime.mjs','field-packet.mjs']:
        (output/filename).write_bytes((here/filename).read_bytes())
    module='''// Generated from real LaTeX output; no TeX parser or font atlas at runtime.
import {createGeneratedLatex} from './gpu-generated-runtime.mjs';
export const metadata = METADATA;
export async function create(device,format='rgba8unorm') {
  return createGeneratedLatex({device,format,metadata,base:import.meta.url});
}
'''.replace('METADATA',json.dumps(metadata,separators=(',',':')))
    (output/'expression.gpu.mjs').write_text(module)
    print(json.dumps({'segments':len(pen.segments),'texture':texture['size']}))
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tolerance',type=float,default=.01)
    parser.add_argument('--texels-per-unit',type=float,default=8)
    args=parser.parse_args()
    generate(args.packet,args.output,args.tolerance,args.texels_per_unit)
