"""Check PNG predictors and RGBA fallback with an independent PDF rasterizer."""
import argparse
import json
import subprocess
from pathlib import Path

import pymupdf
from PIL import Image


def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    rgb = Image.new('RGB', (2, 2))
    rgb.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)])
    rgb.save(output/'rgb.png')
    gray = Image.new('L', (2, 2)); gray.putdata([0, 85, 170, 255]); gray.save(output/'gray.png')
    rgba = Image.new('RGBA', (2, 2)); rgba.putdata([(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 128), (0, 0, 0, 0)])
    (output/'rgba.raw').write_bytes(rgba.tobytes())
    module = Path(__file__).resolve().parent/'vector-pdf.mjs'
    script = r'''
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
const {exportVectorPdf}=await import(pathToFileURL(process.argv[2]));
const output=process.argv[3],vectors={schema:'vkf.pdf-vectors/1',keys:{},paths:{}};
for(const name of ['rgb','gray','rgba']){
 const source=name==='rgba'?{width:2,height:2,rgba:new Uint8Array(await readFile(resolve(output,'rgba.raw')))}:{png:new Uint8Array(await readFile(resolve(output,name+'.png')))};
 const layout={pages:[{width:20,height:20,items:[{kind:'image',asset:'image',x:0,y:0,width:20,height:20}]}]};
 await writeFile(resolve(output,name+'.pdf'),await exportVectorPdf(layout,vectors,{images:{image:source}}));
}
'''
    subprocess.run(['node', '--input-type=module', '-', str(module), str(output)], input=script, text=True, check=True)
    expected = {'rgb': [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)],
                'gray': [(n, n, n) for n in [0, 85, 170, 255]],
                'rgba': [(255, 0, 0), (0, 255, 0), (127, 127, 255), (255, 255, 255)]}
    checks = []
    for name, colors in expected.items():
        doc = pymupdf.open(output/(name+'.pdf'))
        for zoom in [1, 16]:
            pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB)
            actual = [pix.pixel(x*zoom, y*zoom) for x, y in [(5, 5), (15, 5), (5, 15), (15, 15)]]
            assert all(max(abs(a-b) for a, b in zip(pixel, reference, strict=True)) <= 1 for pixel, reference in zip(actual, colors, strict=True))
            checks.append({'source': name, 'zoom': zoom, 'pixels': actual})
    (output/'verification.json').write_text(json.dumps({'passed': True, 'checks': checks}, indent=2))
    return checks


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('output', type=Path)
    print(json.dumps(verify(parser.parse_args().output.resolve())))
