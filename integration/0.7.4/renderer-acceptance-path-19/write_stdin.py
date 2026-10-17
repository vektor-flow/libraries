"""Generate current CLI stdin; does not create the run directory or execute it."""
import argparse
import json
import sys
from pathlib import Path
from prepare import HERE, check, stdin_text

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--case', choices=['original', 'edited-full'], required=True)
parser.add_argument('--run-dir', type=Path, required=True)
parser.add_argument('--layout', action='store_true')
args = parser.parse_args()
manifest = json.loads((HERE / 'fixtures.json').read_text())
check(manifest['binding'])
binding = json.loads(Path(manifest['binding']['path']).read_text())
for ref in binding['inputs']:
    check(ref)
source = manifest['original' if args.case == 'original' else 'edited']
check(source)
if not args.run_dir.is_absolute() or args.run_dir.exists():
    raise ValueError('Supply a fresh absolute root-admitted run directory')
sys.stdout.write(stdin_text(binding, source['path'], args.run_dir, args.layout))
