"""Sample direct-LaTeX field signs against independent vector winding."""
import argparse
import json
from pathlib import Path
from PIL import Image
from fontTools.pens.pointInsidePen import PointInsidePen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path


def verify(folder):
    receipt=json.loads((folder/'build-receipt.json').read_text())
    packet=json.loads((folder/'path-packet.json').read_text())
    recorded=RecordingPen()
    parse_path(packet['combinedPath'],recorded)
    texture=receipt['texture']
    image=Image.open(folder/texture['image']).convert('RGBA')
    assert list(image.size)==texture['size']
    pixels=image.load()
    padding=texture['paddingTexels']
    scale=1/texture['shapeUnitsPerTexel']
    checked=mismatches=skipped=0
    examples=[]
    # Uniform grid with non-integer mapping to exact vector coordinates.
    stride=max(1,int(max(image.size)/100))
    for py in range(0,image.height,stride):
        for px in range(0,image.width,stride):
            sample=pixels[px,py]
            median=sorted(sample[:3])[1]/255
            if abs(median-.5)*texture['distanceRangeTexels']<1:
                skipped+=1
                continue
            x=(px+.5-padding)/scale
            y=(py+.5-padding)/scale
            pen=PointInsidePen(None,(x,y),evenOdd=False)
            recorded.replay(pen)
            expected=pen.getResult()
            checked+=1
            if expected!=(median>.5):
                mismatches+=1
                if len(examples)<12:
                    examples.append({'pixel':[px,py],'expectedInside':expected,'median':median})
    result={'method':'Independent fontTools nonzero-winding versus RGB median at PNG texel centers',
        'tested':checked,'mismatches':mismatches,'nearBoundarySkipped':skipped,'examples':examples,
        'passed':mismatches==0,
        'limits':['Finite sampled sign check, excluding points within one reconstructed texel of the boundary.',
            'Does not verify GPU pixels, subpixel quality, exact distance magnitude or continuous geometry.']}
    (folder/'field-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'{folder.name}: {checked} sign checks, {mismatches} mismatches',flush=True)
    if mismatches:
        raise ValueError('Field sign check failed; preserve receipt')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    args=parser.parse_args()
    verify(args.folder)
