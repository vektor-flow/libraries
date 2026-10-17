"""Unpack generic font-only resources for native VKF, without document inputs.

Preparation is offline; runtime parsing, lookup and PDF generation are VKF.
The payloads retain exactly the same bytes as the existing indexed font bundle.
"""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path


def prepare(source, output):
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError('Font preparation requires Python 3.14')
    metrics = gzip.decompress((source/'pdf-metrics.json.gz').read_bytes())
    index = gzip.decompress((source/'pdf-vector-index.json.gz').read_bytes())
    operators = (source/'pdf-paths.bin').read_bytes()
    decoded = json.loads(index)
    sha = lambda data: hashlib.sha256(data).hexdigest()
    if decoded['schema'] != 'vkf.pdf-vector-index/1':
        raise ValueError('Unsupported indexed font resource')
    if sha(metrics) != decoded['pdfMappingSha256']:
        raise ValueError('Font metrics and vectors do not match')
    operators.decode('ascii')
    for path in decoded['paths'].values():
        offset, length = path['offset'], path['length']
        if (type(offset) is not int or type(length) is not int or offset < 0
                or length < 0 or offset+length > len(operators)):
            raise ValueError('Invalid indexed font range')
    if not set(decoded['keys'].values()) <= decoded['paths'].keys():
        raise ValueError('Missing indexed font paths')
    output.mkdir(parents=True, exist_ok=False)
    payloads = {'metrics.json': metrics, 'vector-index.json': index,
                'operators.txt': operators}
    manifest = {'schema': 'vkf.native-font-files/1', 'fontOnly': True,
                'source': str(source.resolve()), 'keys': len(decoded['keys']),
                'paths': len(decoded['paths']), 'files': {}}
    for name, data in payloads.items():
        (output/name).write_bytes(data)
        manifest['files'][name] = {'bytes': len(data), 'sha256': sha(data)}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    arguments = parser.parse_args()
    print(json.dumps(prepare(arguments.source, arguments.output)))
