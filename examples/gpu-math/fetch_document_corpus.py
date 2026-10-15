"""Fetch unmodified upstream LaTeX examples into a fresh evidence folder."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
SOURCES={
 'small2e':('base/small2e.tex','6995024e85f537d32eef704a81d7f53b84aa06cb23361559d3fea3b6c5653627'),
 'sample2e':('base/sample2e.tex','f135855f870c31f1101001bdb75b11e94a23c2605f7ab5dffa1299d53b1977cc'),
 'testmath':('required/amsmath/testmath.tex','9b311f1835266833ad40130e7a7a6361a950c965d308c02d567361e72ce74aa5')}
def fetch(output):
 output.mkdir();rows=[]
 for name,(path,expected)in SOURCES.items():
  url='https://raw.githubusercontent.com/latex3/latex2e/main/'+path;raw=urllib.request.urlopen(url,timeout=30).read();folder=output/name;folder.mkdir();(folder/'source.tex').write_bytes(raw);actual=hashlib.sha256(raw).hexdigest();rows.append({'name':name,'url':url,'sha256':actual,'bytes':len(raw),'matchesReviewedSource':actual==expected})
 (output/'sources.json').write_text(json.dumps(rows,indent=2)+'\n')
 if not all(r['matchesReviewedSource']for r in rows):raise SystemExit('Upstream changed; preserve downloads and review before adopting new reference bytes')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);fetch(p.parse_args().output)
