"""Check inter-frame topology and curve crossings, independently of movie samples."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from field_transport import Atlas,Transport,ring,raster,topology,crossings
p=argparse.ArgumentParser();p.add_argument('atlas',type=Path);p.add_argument('output',type=Path);args=p.parse_args();atlas=Atlas(args.atlas)
cases=[('ring-D',ring(),atlas.loops('display/D')),('O-D',atlas.loops('display/O'),atlas.loops('display/D')),('8-B',atlas.loops('display/8'),atlas.loops('display/B')),('0-D',atlas.loops('display/0'),atlas.loops('display/D'))];results=[]
for name,a,b in cases:
 plan=Transport(a,b);last=None;velocity=None;peak=0.;gap=float("inf")
 for t in (np.arange(311)+.5)/311:
  loops=plan.contours(float(t));assert topology(raster(loops,ss=1)>127)==plan.expected
  for i,x in enumerate(loops):
   assert not crossings(x,x,True)
   for y in loops[:i]:
    assert not crossings(x,y)
    vertices=cKDTree(x).query(y)[0].min()
    bound=vertices-.5*(np.linalg.norm(np.roll(x,-1,axis=0)-x,axis=1).max()+np.linalg.norm(np.roll(y,-1,axis=0)-y,axis=1).max())
    assert bound>0,(name,t,'touching contours',bound)
    gap=min(gap,float(bound))
  current=np.stack(loops)
  if last is not None:
   v=current-last
   if velocity is not None:peak=max(peak,float(np.linalg.norm(v-velocity,axis=-1).max()))
   velocity=v
  last=current
 result=dict(case=name,inter_frame_samples=311,topology=plan.expected,crossings=0,minimum_boundary_gap_lower_bound_pixels=gap,max_boundary_second_difference_pixels=peak);results.append(result);print(result,flush=True)
args.output.write_text(json.dumps(results,indent=2)+'\n')
