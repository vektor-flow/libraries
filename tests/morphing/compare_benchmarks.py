"""Alternate already-built baseline/current workloads; retain raw wall timings."""
from pathlib import Path
import argparse,json,math,statistics,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
before=json.loads((a.before/'benchmark.json').read_text());after=json.loads((a.after/'benchmark.json').read_text())
assert before['compiler_sha256']==after['compiler_sha256']
rows=[]
for old,new in zip(before['cases'],after['cases'],strict=True):
 assert (a.before/(old['case']+'.vkf')).read_bytes()==(a.after/(new['case']+'.vkf')).read_bytes(), 'Workloads differ'
 for k in ['case','states','channels','iterations','coordinates_per_iteration']:assert old[k]==new[k]
 assert math.isclose(float(old['checksum']),float(new['checksum']),rel_tol=1e-12,abs_tol=1e-10),(old,new)
 times={'before':[],'after':[]}
 for i in range(8):
  for label,directory in ([('before',a.before),('after',a.after)] if i%2==0 else [('after',a.after),('before',a.before)]):
   t=time.perf_counter_ns();r=subprocess.run([str(directory.resolve()/old['case'])],capture_output=True,text=True,timeout=120);dt=(time.perf_counter_ns()-t)/1e6
   assert r.returncode==0,r.stderr
   assert math.isclose(float(r.stdout),float(old['checksum']),rel_tol=1e-12,abs_tol=1e-10)
   if i:times[label].append(dt)
 row={k:old[k] for k in ['case','states','channels','iterations','coordinates_per_iteration']}
 row.update(times);row['before_median_ms']=statistics.median(times['before']);row['after_median_ms']=statistics.median(times['after']);row['speedup']=row['before_median_ms']/row['after_median_ms'];rows.append(row)
 print(row['case'],round(row['before_median_ms'],3),round(row['after_median_ms'],3),round(row['speedup'],2),flush=True)
a.output.write_text(json.dumps({'scope':before['scope'],'method':'Alternating baseline/current execution order. First pair discarded; 7 measured pairs. Matching output checksums. Shared host, not hardware-isolated.','compiler_sha256':before['compiler_sha256'],'before_sources':before['sources'],'after_sources':after['sources'],'cases':rows},indent=2)+'\n')
