"""Keep actual algebra operations in the benchmark, including unsolved cases."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from field_transport import Atlas,topology
from scene_transport import Scene,endpoint,fit,draw_scene
from rigid_routes import RoutedScene
p=argparse.ArgumentParser();p.add_argument('atlas',type=Path);p.add_argument('layouts',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
atlas=Atlas(args.atlas);results=[]
for item in json.loads(args.layouts.read_text()):
 try:
  a,b=fit(endpoint(atlas,item['from']),endpoint(atlas,item['to']))
  scene=Scene(a,b,exact_first=True)
  if all(part[3] and abs(part[4])<1e-7 and abs(part[5]-1)<1e-7 for part in scene.parts):scene=RoutedScene(a,b)
  else:raise ValueError('Nonrigid/branching correspondence still requires a validated planner')
  centers=[]
  for t in np.linspace(0,1,623):
   bodies=scene.contours(float(t));im=draw_scene(bodies,ss=8)
   if topology(im>127)!=scene.expected:raise ValueError(('Topology changed',float(t),topology(im>127),scene.expected))
   centers.append([body[0].mean(0).tolist() for body in bodies])
  positions=np.array(centers)[::2]
  result=dict(case=item['id'],passed=True,sampled_states=623,topology=scene.expected,
      offset_knots=scene.offsets.tolist(),peak_center_step_px=float(abs(np.diff(positions,axis=0)).max()),
      peak_center_second_difference=float(abs(np.diff(positions,n=2,axis=0)).max()))
 except Exception as exc:result=dict(case=item['id'],passed=False,error=repr(exc))
 results.append(result);print(item['id'],result['passed'],result.get('error',''),flush=True)
args.output.write_text(json.dumps(dict(cases=results,atlas=atlas.provenance,
 layouts_sha256=hashlib.sha256(args.layouts.read_bytes()).hexdigest(),
 scope='Sampled geometry checks; not proof of continuous collision freedom or general branching'),indent=2)+'\n')
if not all(r['passed'] for r in results):raise SystemExit('Unsolved math cases remain in the report')
