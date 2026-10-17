"""Prepare lossless layout metrics without GPU atlas/coverage payloads.

No article, reference PDF, font compiler or external executable is used. Keep
every symbol metric and glyph part: the only removed data is GPU paint data.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def prepare(directory):
    raw = (directory / 'typing-data.json').read_bytes()
    data = json.loads(raw)
    mapping = {key: value for key, value in data.items()
               if key in ['maps', 'documentFonts', 'fontProfile', 'atlasSize',
                          'range', 'vectorTextCompanion']}
    # Layout uses planes for clickable footnote bounds; UVs belong to preview.
    mapping['tiles'] = {key: {'plane': value['plane']}
                        for key, value in data['tiles'].items()}
    payload = json.dumps(mapping, separators=(',', ':'), ensure_ascii=False).encode()
    target = directory / 'pdf-metrics.json.gz'
    target.write_bytes(gzip.compress(payload, mtime=0))
    vectors_path = directory / 'pdf-vectors.json.gz'
    vectors = json.loads(gzip.decompress(vectors_path.read_bytes()))
    if vectors['mappingSha256'] != hashlib.sha256(raw).hexdigest():
        raise ValueError('Vector bundle does not match original font mapping')
    vectors['pdfMappingSha256'] = hashlib.sha256(payload).hexdigest()
    vectors_path.write_bytes(gzip.compress(json.dumps(vectors, separators=(',', ':')).encode(), mtime=0))
    # Index reusable font programs once. Runtime decodes only the glyph paths it
    # actually paints, instead of inflating/parsing every installed alphabet.
    paths, chunks, offset = {}, [], 0
    for key, value in vectors['paths'].items():
        operators = value['operators'].encode()
        paths[key] = {'bounds': value['bounds'], 'offset': offset, 'length': len(operators)}
        chunks.append(operators)
        offset += len(operators)
    (directory / 'pdf-paths.bin').write_bytes(b''.join(chunks))
    index = {**vectors, 'schema': 'vkf.pdf-vector-index/1', 'paths': paths}
    (directory / 'pdf-vector-index.json.gz').write_bytes(gzip.compress(json.dumps(index, separators=(',', ':')).encode(), mtime=0))
    return {'metricsBytes': len(payload), 'compressedBytes': target.stat().st_size,
            'mappingSha256': vectors['mappingSha256'], 'pdfMappingSha256': vectors['pdfMappingSha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    print(json.dumps(prepare(parser.parse_args().directory)))
