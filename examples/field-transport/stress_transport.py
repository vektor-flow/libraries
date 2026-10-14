"""Seeded endpoint-only regression families; unsuccessful cases stay in reports."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from field_transport import ring,topology
from scene_transport import draw_scene
from rigid_routes import RoutedScene

def generated(seed,count,angle=0,varied=False):
 rng=np.random.default_rng(seed);theta=np.linspace(0,2*np.pi,count,endpoint=False)
 slots=np.column_stack([190*np.cos(theta),120*np.sin(theta)])
 perm=rng.permutation(count);a=[];b=[]
 rotation=np.array([[np.cos(angle),np.sin(angle)],[-np.sin(angle),np.cos(angle)]])
 for i in range(count):
  radius=18+3*i
  body=ring(radius,8) if i%2 else [ring(radius,8)[0]*[1,.7]]
  if varied and i%3==0:
   theta=np.linspace(0,2*np.pi,512,endpoint=False)
   body=[np.column_stack([np.cos(theta),np.sin(theta)])*(radius*(1+.2*np.cos(3*theta)))[:,None]]
  a.append([(p+slots[i])@rotation for p in body]);b.append([(p+slots[perm[i]])@rotation for p in body])
 if varied:
  scale=float(rng.uniform(.65,1.2));shift=rng.uniform(-40,40,2)
  a=[[p*scale+shift for p in body] for body in a];b=[[p*scale+shift for p in body] for body in b]
 return a,b

def main():
 parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--seeds',type=int,default=8);parser.add_argument('--start-seed',type=int,default=0);parser.add_argument('--varied',action='store_true');args=parser.parse_args();results=[]
 for seed in range(args.start_seed,args.start_seed+args.seeds):
  count=2+seed%(6 if args.varied else 5)
  angles=[float(np.random.default_rng(seed+7000).uniform(0,np.pi))]*2 if args.varied else [0,np.pi/2]
  for index,angle in enumerate(angles):
   result=dict(seed=seed,count=count,angle=float(angle),varied=args.varied,reverse=args.varied and index==1)
   a,b=generated(seed,count,angle,args.varied)
   if result["reverse"]:a,b=b,a
   try:
    scene=RoutedScene(a,b)
    for t in np.linspace(0,1,81):
     frame=draw_scene(scene.contours(float(t)),ss=8)
     if topology(frame>127)!=scene.expected:raise ValueError(('Topology changed',float(t),topology(frame>127),scene.expected))
    result.update(passed=True,samples=81)
   except Exception as exc:result.update(passed=False,error=repr(exc))
   results.append(result);print(result,flush=True)
 args.output.write_text(json.dumps(dict(generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=results,passed=sum(r['passed'] for r in results),total=len(results),scope='Generated translation/permutation families only; not arbitrary morph or branching coverage'),indent=2)+'\n')
 if not all(r['passed'] for r in results):raise SystemExit('Generated failures retained')
if __name__=='__main__':main()
