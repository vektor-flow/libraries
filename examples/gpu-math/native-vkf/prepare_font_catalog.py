"""Offline generic font packaging; no article, layout or PDF input is accepted.

JSON records retain all properties. The installed fixed-offset directory replaces
eager whole-library JSON parsing; record decoding and PDF writing remain VKF.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MAGIC = b'VKF-FONT-CATALOG/1              '
HEADER_SIZE = 68
SLOT_SIZE = 36


def key_hash(key):
    value = 0
    for scalar in key:
        value = (value*131+ord(scalar)) % 2147483647
    return value


def records(metrics, index):
    yield 'metrics', {k: v for k, v in metrics.items()
                      if k not in ('maps', 'documentFonts', 'tiles')}
    yield 'index', {k: v for k, v in index.items() if k not in ('keys', 'paths')}
    for style, mapping in metrics['maps'].items():
        yield 'style/'+style, {k: v for k, v in mapping.items() if k != 'symbols'}
        for token, glyph in mapping['symbols'].items():
            yield 'math/'+style+'/'+token, glyph
    for name, font in metrics['documentFonts'].items():
        yield 'font/'+name, {k: v for k, v in font.items() if k != 'symbols'}
        for code, glyph in font['symbols'].items():
            yield 'text/'+name+'/'+code, glyph
    for key, tile in metrics['tiles'].items():
        yield 'tile/'+key, tile
    for key, identifier in index['keys'].items():
        yield 'vector/'+key, identifier
    for identifier, path in index['paths'].items():
        yield 'path/'+identifier, path


def pack(entries):
    entries = list(entries)
    if len({key for key, _ in entries}) != len(entries):
        raise ValueError('Duplicate font catalog key')
    capacity = 8
    while capacity < len(entries)*2:
        capacity *= 2
    if capacity > 2097152:
        raise ValueError('Font catalog is too large')
    directory = [None]*capacity
    payload = bytearray()
    payload_start = HEADER_SIZE+capacity*SLOT_SIZE
    for key, value in entries:
        key_bytes = key.encode('utf-8')
        if not key_bytes:
            raise ValueError('Empty font catalog key')
        value_bytes = json.dumps(value, ensure_ascii=False, allow_nan=False,
                                 separators=(',', ':')).encode('utf-8')
        slot = key_hash(key) % capacity
        while directory[slot] is not None:
            slot = (slot+1) % capacity
        directory[slot] = (payload_start+len(payload), len(key_bytes), len(value_bytes))
        payload.extend(key_bytes)
        payload.extend(value_bytes)
    fixed = lambda value: f'{value:012d}'.encode('ascii')
    table = b''.join(b'0'*SLOT_SIZE if row is None else b''.join(map(fixed, row))
                     for row in directory)
    assert len(MAGIC) == 32
    return (MAGIC+fixed(capacity)+fixed(len(entries))+fixed(len(payload))
            +table+payload)


def prepare(source, output):
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError('Font preparation requires Python 3.14')
    manifest = json.loads((source/'manifest.json').read_bytes())
    payloads = {name: (source/name).read_bytes()
                for name in ['metrics.json', 'vector-index.json', 'operators.txt']}
    sha = lambda data: hashlib.sha256(data).hexdigest()
    for name, data in payloads.items():
        if sha(data) != manifest['files'][name]['sha256']:
            raise ValueError('Prepared font file hash mismatch: '+name)
    metrics = json.loads(payloads['metrics.json'])
    index = json.loads(payloads['vector-index.json'])
    if sha(payloads['metrics.json']) != index['pdfMappingSha256']:
        raise ValueError('Font metrics/vector binding mismatch')
    catalog = pack(records(metrics, index))
    output.mkdir(parents=True, exist_ok=False)
    (output/'catalog.vkfont').write_bytes(catalog)
    (output/'operators.txt').write_bytes(payloads['operators.txt'])
    result = {'schema': 'vkf.font-catalog/1', 'fontOnly': True,
              'source': str(source.resolve()),
              'records': int(catalog[44:56]),
              'files': {name: {'bytes': len(data), 'sha256': sha(data)}
                        for name, data in [('catalog.vkfont', catalog),
                                           ('operators.txt', payloads['operators.txt'])]},
              'originalFiles': manifest['files']}
    (output/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output)))
