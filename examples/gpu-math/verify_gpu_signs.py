"""Independent vector winding check of actual GPU-generated field readback."""
import argparse
import json
from pathlib import Path
from PIL import Image
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.pointInsidePen import PointInsidePen
from fontTools.misc.transform import Transform
from fontTools.svgLib.path import parse_path

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args();report=json.loads((args.receipt/'webgpu-verification.json').read_text());results=[]
    for case in report['results']:
        name=case['name']
        source=args.root/('independent-long-packet.json' if name=='long' else 'direct-latex-pinned/fraction/path-packet.json')
        packet=json.loads(source.read_text());pen=RecordingPen()
        for p in packet['primitives']:
            parse_path(packet['outlines'][p['outline']]['svgPath'],TransformPen(pen,Transform(*p['transform'])))
        texture=case['metadata']['texture'];w,h=texture['size']
        bitmap=Image.frombytes('RGBA',(w,h),(args.receipt/f'{name}-field.rgba').read_bytes());pixels=bitmap.load()
        tested=mismatches=0;step=max(1,max(w,h)//24)
        for y in range(0,h,step):
            for x in range(0,w,step):
                encoded=pixels[x,y][0]/255
                if abs(encoded-.5)*texture['distanceRangeTexels']<1:continue
                point=((x+.5-texture['paddingTexels'])*texture['shapeUnitsPerTexel'],
                    (y+.5-texture['paddingTexels'])*texture['shapeUnitsPerTexel'])
                inside=PointInsidePen(None,point,evenOdd=False);pen.replay(inside)
                tested+=1;mismatches+=inside.getResult()!=(encoded>.5)
        results.append({'case':name,'tested':tested,'mismatches':mismatches,'passed':mismatches==0})
    output={'cases':results,'passed':all(r['passed'] for r in results),
        'limits':['Finite non-boundary sample; not exact distance magnitude or continuous geometry proof.']}
    (args.receipt/'gpu-field-signs.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output))
    if not output['passed']:raise SystemExit('GPU field sign check failed')
