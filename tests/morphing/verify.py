"""Independent native Morphing qualification. Python is a test oracle, not runtime."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
import numpy as np
from scipy.interpolate import CubicSpline
from numpy.polynomial import Polynomial

p=argparse.ArgumentParser();p.add_argument('--compiler',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[2];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
shutil.copy2(root/'Morphing.vkf',out/'Morphing.vkf');shutil.copytree(root/'morphing',out/'morphing')
report={'compiler':str(a.compiler),'compiler_sha256':hashlib.sha256(a.compiler.read_bytes()).hexdigest(),'sources':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [root/'Morphing.vkf',*(root/'morphing').glob('*.vkf')]},'passed':False}
def compile_run(name,text,success=True):
 source=out/(name+'.vkf');source.write_text(text);binary=out/name
 build=subprocess.run([str(a.compiler),'-b',str(source),'-o',str(binary)],capture_output=True,text=True,timeout=120)
 (out/(name+'-build.log')).write_text(build.stdout+build.stderr)
 assert build.returncode==0,build.stderr
 run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=60)
 (out/(name+'-run.log')).write_text(run.stdout+run.stderr)
 assert (run.returncode==0)==success,(name,run.stdout,run.stderr)
 return run.stdout

def fmt(x):return format(float(x),'.17f')
def vec(x):return '['+','.join(map(fmt,np.asarray(x).ravel()))+']'
def reference(knots,values,q,mode,start,end):
 i=min(len(knots)-2,np.searchsorted(knots,q,side='right')-1);h=knots[i+1]-knots[i];u=(q-knots[i])/h
 s=start and i==0;e=end and i==len(knots)-2
 poly=Polynomial([0,1])
 if s and e:poly=Polynomial([0,0,0,10,-15,6])
 elif s:poly=Polynomial([0,0,0,6,-8,3])
 elif e:poly=Polynomial([1])-Polynomial([0,0,0,6,-8,3])(Polynomial([1,-1]))
 at=knots[i]+h*poly(u);d=poly.deriv()(u);dd=poly.deriv(2)(u)/h
 if mode:
  curve=CubicSpline(knots,values,axis=0,bc_type='natural');v=curve(at);first=curve(at,1);second=curve(at,2)
 else:
  first=(values[i+1]-values[i])/h;v=values[i]+(at-knots[i])*first;second=np.zeros_like(first)
 return v,first*d,second*d*d+first*dd
try:
 compile_run('core',(root/'tests/morphing/core.vkf').read_text())
 compile_run('material',(root/'tests/morphing/material.vkf').read_text())
 compile_run('biological',(root/'tests/morphing/biological.vkf').read_text())
 lines=['m:.Morphing','tests()->bit:'];rng=np.random.default_rng(41);samples=0;cases=0
 for count in [2,3,5,9]:
  knots=np.r_[0,np.cumsum(rng.uniform(.4,2,count-1))];values=rng.normal(size=(count,3))
  for mode in [0,1]:
   for start,end in [(False,False),(True,False),(False,True),(True,True)]:
    name='p'+str(cases);lines.append(f'    {name}:m.prepare({vec(knots)},{vec(values)},3,{mode},{str(start).lower()},{str(end).lower()})')
    for q in np.r_[knots,(knots[:-1]+knots[1:])/2]:
     want=reference(knots,values,q,mode,start,end);sample='s'+str(samples);lines.append(f'    {sample}:m.sample({name},{fmt(q)})')
     for field,expected in zip(['value','first','second'],want):
      for c,x in enumerate(expected):lines.append(f'    (|{sample}.{field}.({c})-({fmt(x)})|<{fmt(1e-8*(1+abs(x)))})?! "independent spline {samples} {field} {c}"')
     for c,x in enumerate(want[0]):
      lines.append(f'    channel{samples}_{c}:m.channel({name},[{fmt(q)}],{c})')
      lines.append(f'    (|channel{samples}_{c}.(0)-({fmt(x)})|<{fmt(1e-8*(1+abs(x)))})?! "independent channel {samples} {c}"')
     samples+=1
    cases+=1
  lines+=['    @:true','::tests()'];compile_run('oracle-'+str(count),'\n'.join(lines)+'\n')
  lines=['m:.Morphing','tests()->bit:']
 report.update(curve_cases=cases,sampled_states=samples,scalar_comparisons=samples*9,channel_comparisons=samples*3)
 invalid={
 'duplicate-coordinate':'m.prepare([0,0],[1,2],1,1,false,false)',
 'wrong-width':'m.prepare([0,1],[1,2],2,1,false,false)',
 'invalid-mode':'m.prepare([0,1],[1,2],1,3,false,false)',
 'outside-coordinate':'m.sample(m.prepare([0,1],[1,2],1,0,false,false),2)',
 'material-birth':'m.prepare_material([0,1],[0,1,2],[1,2],[0,1],1,0,false,false)',
 'empty-state':'m.prepare_material([0,1],[0,0,1],[1],[0],1,0,false,false)',
 'duplicate-layer':'m.bind_view("view",["same","same"],[0,1,2],m.prepare([0,1],[0,1,2,3],2,0,false,false))',
 'empty-polygon': 'b.polygon_field([0,0,0.2,0.2],[0,2],9)',
 'invalid-channel':'m.channel(m.prepare([0,1],[0,1],1,0,false,false),[0,1],1)',
 }
 for name,expr in invalid.items():compile_run(name,'m:.Morphing\nb:.morphing.biological\n::'+expr+'\n',False)
 report['rejections']=list(invalid);report['passed']=True
finally:(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
