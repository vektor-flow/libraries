"""Losslessly repack reusable fields, preserving planes and all field pixels."""
import argparse, copy, gzip, hashlib, json, math
from pathlib import Path
from PIL import Image

def repack(data, image):
    data = copy.deepcopy(data)
    width, height = data['atlasSize']
    entries = list(data['tiles'].values()) + [tile for phases in data.get('coverage96', {}).values() for tile in phases if tile]
    def rect(tile):
        return tuple(round(n * (width if i % 2 == 0 else height)) for i, n in enumerate(tile['uv']))
    groups = {}
    for tile in entries:
        groups.setdefault(rect(tile), []).append(tile)
    target = Image.new('RGBA', (width, height)); shelves = []; bottom = 2; receipts = []
    for old, tiles in sorted(groups.items(), key=lambda item: (-(item[0][3]-item[0][1]), -(item[0][2]-item[0][0]), item[0])):
        w, h = old[2]-old[0], old[3]-old[1]
        shelf = next((s for s in shelves if s['x']+w+2 <= width), None)
        if shelf is None:
            if bottom+h+2 > height: raise ValueError('Repacked atlas overflow')
            shelf = {'x': 2, 'y': bottom}; shelves.append(shelf); bottom += h+2
        x, y = shelf['x'], shelf['y']; shelf['x'] += w+2
        field = image.crop(old); target.paste(field, (x,y))
        uv = [x/width,y/height,(x+w)/width,(y+h)/height]
        for tile in tiles: tile['uv'] = uv
        check = target.crop((x,y,x+w,y+h))
        if field.tobytes() != check.tobytes(): raise ValueError('Atlas field changed')
        receipts.append({'from':old,'to':[x,y,x+w,y+h],'sha256':hashlib.sha256(field.tobytes()).hexdigest()})
    return data, target, {'fields':len(groups),'rowsUsed':bottom,'unchangedFieldPixels':True,'placements':receipts}

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('source',type=Path); parser.add_argument('output',type=Path); args=parser.parse_args()
    args.output.mkdir()
    data=json.loads((args.source/'typing-data.json').read_text()); image=Image.frombytes('RGBA',tuple(data['atlasSize']),gzip.decompress((args.source/'atlas.rgba.gz').read_bytes()))
    data,image,receipt=repack(data,image)
    (args.output/'typing-data.json').write_text(json.dumps(data,separators=(',',':')))
    (args.output/'atlas.rgba.gz').write_bytes(gzip.compress(image.tobytes(),mtime=0))
    (args.output/'repack.json').write_text(json.dumps(receipt,separators=(',',':')))
    print(json.dumps({k:v for k,v in receipt.items() if k!='placements'}))
if __name__=='__main__': main()
