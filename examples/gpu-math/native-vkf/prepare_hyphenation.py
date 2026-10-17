"""Python 3.14 preparation of reusable language trie data, never word results."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def prepare(output):
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError('Hyphenation preparation requires Python 3.14')
    core = Path(__file__).resolve().parent.parent/'latex-modules/core'
    command = ['node', '--input-type=module', '-e',
               'import {patterns,exceptions} from '+json.dumps((core/'english-hyphenation.mjs').as_uri())+'; console.log(JSON.stringify({patterns,exceptions}));']
    data = json.loads(subprocess.check_output(command, text=True))
    nodes = [{'children': {}, 'weights': []}]
    for pattern in data['patterns']:
        node = 0
        index = 0
        weights = [0]
        for char in pattern:
            if '0' <= char <= '9':
                weights[index] = int(char)
            else:
                if char not in '.abcdefghijklmnopqrstuvwxyz':
                    raise ValueError('Unsupported English pattern character')
                if char not in nodes[node]['children']:
                    nodes[node]['children'][char] = len(nodes)
                    nodes.append({'children': {}, 'weights': []})
                node = nodes[node]['children'][char]
                index += 1
                weights.append(0)
        nodes[node]['weights'] = weights
    edge_records = []
    weight_records = []
    node_records = []
    for node in nodes:
        children = sorted(node['children'].items())
        weights = node['weights']
        if len(children)>27 or len(weights)>99:
            raise ValueError('Language record exceeds asset field width')
        node_records.append(f'{len(edge_records):08d}{len(children):02d}{len(weight_records):08d}{len(weights):02d}')
        edge_records.extend(char+f'{child:08d}' for char, child in children)
        weight_records.extend(map(str, weights))
    exceptions = ''.join(raw+'\n' for raw in data['exceptions'])
    magic = 'VKF-HYPHENATION/1'.ljust(32)
    asset = (magic+f'{len(nodes):08d}{len(edge_records):08d}{len(weight_records):08d}{len(data["exceptions"]):08d}{len(exceptions.encode()):08d}'+''.join(node_records)+''.join(edge_records)+''.join(weight_records)+exceptions).encode('ascii')
    output.mkdir(parents=True, exist_ok=False)
    (output/'english.vkhyphen').write_bytes(asset)
    # Preserve the original Plain TeX copying notice with the prepared derivative.
    shutil.copy2(core/'hyphen.tex', output/'hyphen.tex')
    manifest = {'format': 'VKF-HYPHENATION/1', 'python': sys.version,
                'patterns': len(data['patterns']), 'defaultExceptions': len(data['exceptions']),
                'nodes': len(nodes), 'edges': len(edge_records), 'weights': len(weight_records),
                'bytes': len(asset), 'assetSha256': hashlib.sha256(asset).hexdigest(),
                'sourceSha256': hashlib.sha256((core/'english-hyphenation.mjs').read_bytes()).hexdigest(),
                'precomputedWordResults': False, 'runtimeDecisions': 'VKF'}
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output)))
