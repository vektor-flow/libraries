"""Independent audit of complete native-engine cold/warm/edit benchmarks.

Reads original inputs, per-launch cache receipts, empty-cache proofs and saved
PDFs. Does not render documents or manufacture missing timing measurements.
"""
import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

if sys.version_info[:2] != (3,14):
    raise SystemExit('Reference audit requires Python 3.14')
import pymupdf

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('benchmark',type=Path)
p.add_argument('--source',type=Path,required=True)
p.add_argument('--bibliography',type=Path,required=True)
p.add_argument('--pages',type=int,required=True)
a=p.parse_args()
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
summary_path=a.benchmark/'native-timings.json'
data=json.loads(summary_path.read_text())
report={'passed':False,'python':sys.version,'summarySha256':sha(summary_path),
        'sourceSha256':sha(a.source),'bibliographySha256':sha(a.bibliography),
        'scope':'Complete saved native PDFs; Linux file-cache eviction plus empty per-trial build/font caches. Shared mapped system-library residency is reported separately, not claimed evicted.',
        'coldRuns':[],'engines':{}}
try:
    assert data['sourceSha256']==report['sourceSha256']
    assert data['referenceBibSha256']==report['bibliographySha256']
    rows=data['samples']
    assert set(r['engine']for r in rows)=={'pdflatex','texres'}
    for engine in ['pdflatex','texres']:
        samples=[r for r in rows if r['engine']==engine]
        groups={mode:[r for r in samples if r['profile']==mode]
                for mode in ['cache-cold','warm-full-rebuild','title-punctuation']}
        assert [len(v)for v in groups.values()]==[3,9,9]
        for mode,values in groups.items():
            assert all(r['pages']==a.pages and r['totalMs']>0 for r in values)
            assert data['summary'][engine][mode]['medianMs']==statistics.median(r['totalMs']for r in values)
        for cold in groups['cache-cold']:
            directory=a.benchmark/engine/('trial-'+str(cold['trial']))
            proof=json.loads((directory/'cold-start-proof.json').read_text())
            assert proof=={'sourceOnly':True,'suppliedBbl':False,'auxiliaryFiles':False,
                           'engineBuildCacheExists':False,'generatedPkOrTfm':False}
            cache=json.loads((directory/'cache-residency.json').read_text())
            assert cache['method']=='sync; Linux drop_caches=3; root mincore without reading file contents'
            assert cache['inputResidentPages']==0
            assert sum(cache['after'][p]['resident']for p in cache['inputs'])==0
            assert str(directory/'main.tex')in cache['inputs']
            assert str(directory/'references.bib')in cache['inputs']
            assert sum(cache['after'][p]['pages']for p in cache['inputs'])>0
            assert cold['inputResidentPages']==0
            assert cold['sourceSha256']==report['sourceSha256']
            assert cold['referenceBibSha256']==report['bibliographySha256']
            pdf=directory/'cold.pdf'
            assert sha(pdf)==cold['pdfSha256']
            with pymupdf.open(pdf)as doc:
                assert len(doc)==a.pages
                assert all(len(page.get_text().strip())>20 for page in doc)
                baseline=[hashlib.sha256(page.get_text().encode()).hexdigest()for page in doc]
            log=(directory/(cold['stages'][-1]['stage']+'.txt')).read_text(errors='replace')
            assert 'There were undefined references'not in log
            assert 'There were undefined citations'not in log
            assert sum(s['blockInputs']for s in cold['stages'])>0
            edits=[r for r in groups['title-punctuation']if r['trial']==cold['trial']]
            assert [r['changed']for r in edits]==[True,False,True]
            for i,edit in enumerate(edits):
                expected=a.source.read_text()
                if edit['changed']:
                    assert expected.count(data['edit']['before'])==1
                    expected=expected.replace(data['edit']['before'],data['edit']['after'])
                assert hashlib.sha256(expected.encode()).hexdigest()==edit['sourceSha256']
                with pymupdf.open(directory/f'edit-{i}.pdf')as doc:
                    assert len(doc)==a.pages
                    actual=[hashlib.sha256(page.get_text().encode()).hexdigest()for page in doc]
                changed_pages=[i+1 for i,(x,y)in enumerate(zip(baseline,actual))if x!=y]
                assert changed_pages==edit['changedTextPages']
                assert bool(changed_pages)==edit['changed']
            report['coldRuns'].append({'engine':engine,'trial':cold['trial'],
                'pages':a.pages,'inputResidentPages':0,
                'hostResidentPages':cache['hostResidentPages'],
                'inputFiles':len(cache['inputs']),
                'cacheReceiptSha256':sha(directory/'cache-residency.json'),
                'emptyCacheProofSha256':sha(directory/'cold-start-proof.json'),
                'pdfSha256':sha(pdf),'stages':cold['stages']})
        report['engines'][engine]={'coldSamples':3,'warmSamples':9,'editSamples':9,
                                  'summary':data['summary'][engine]}
    report['passed']=True
finally:
    (a.benchmark/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'engines':list(report['engines']),'coldRuns':len(report['coldRuns'])}))
