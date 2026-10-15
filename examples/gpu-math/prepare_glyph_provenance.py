"""Attach auditable constituent glyphs to single/composite distance-field tiles."""
import argparse,json
from pathlib import Path
from glyph_provenance import DVI

def prepare(mapping,root,output,extras=None):
 data=json.loads(mapping.read_text());counts={}
 for style,m in data['maps'].items():
  catalogue=json.loads((root/f'typing-{style}/symbol-mapping.json').read_text())['symbols'];total=0
  for index,key in enumerate(catalogue):
   parts=DVI(root/f'typing-{style}'/str(index)/'expression.dvi',extras).read();m['symbols'][key]['glyphParts']=parts;total+=len(parts)
  counts[style]=total
 output.write_text(json.dumps(data,separators=(',',':')));print(counts)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mapping',type=Path);p.add_argument('root',type=Path);p.add_argument('output',type=Path);p.add_argument('--oracle-extras',type=Path);a=p.parse_args();prepare(a.mapping,a.root,a.output,a.oracle_extras)
