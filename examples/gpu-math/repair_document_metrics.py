"""Refresh document TFM metrics without changing outlines or atlas pixels."""
import argparse,json,subprocess
from pathlib import Path
from tex_font_metrics import load_tex_tfm
from prepare_document_fonts import refresh_metrics,PT

def repair(source,output):
 data=json.loads(source.read_text())
 for table in data['documentFonts'].values():
  path=subprocess.check_output(['kpsewhich',table['name']+'.tfm'],text=True).strip()
  refresh_metrics(table,load_tex_tfm(path),table['size']/PT)
 output.write_text(json.dumps(data,separators=(',',':')))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();repair(a.source,a.output)
