"""Native shared text-unfold algorithm: independent math oracle and indexed paths."""
from pathlib import Path
import argparse,tempfile,subprocess,shutil,math,json,random
p=argparse.ArgumentParser();p.add_argument('--compiler',default='/home/viktor/.local/bin/vkf-cuvami');p.add_argument('--oracle-output',type=Path);a=p.parse_args();root=Path(__file__).resolve().parents[2]
rng=random.Random(20261019);samples=[]
for i in range(96):
 channel=i%5
 x=rng.uniform(-.3,1.3) if channel==0 else rng.random()
 y=rng.uniform(1,10) if channel==0 else rng.uniform(0,3)
 samples.append({'index':channel,'params':[x,y]})
with tempfile.TemporaryDirectory(prefix='vkf-unfold-') as tmp:
 out=Path(tmp);shutil.copytree(root/'morphing',out/'morphing');shutil.copy2(root/'Morphing.vkf',out/'Morphing.vkf');shutil.copy2(root/'tests/morphing/gpu-unfold.vkf',out/'gpu.vkf')
 lines=['m:.Morphing','u:.morphing.unfold','g:.gpu','tests()->bit:', '    settings:m.unfold_defaults()', '    (settings.k=4 /\\ settings.velocity=0.54 /\\ settings.overshoot=0.32 /\\ settings.grow /\\ settings.loop)?! "selected defaults"', '    (u.advance(3,10,0)=3)?! "zero velocity holds"', '    (|u.reading_coordinate(1,2,0.5,4)-(1.5+3.141592653589793/4)|<0.000000001)?! "indexed line coordinate"']
 for amount in [0,.01,.1,.32,.5]:
  lines+= [f'    s{int(amount*100)}:u.back_coefficient({amount})']
  if amount>0:
   n=f's{int(amount*100)}';lines += [f'    peak{int(amount*100)}:1-2*{n}/(3*({n}+1))',f'    (|u.growth(peak{int(amount*100)},{n})-{1+amount}|<0.00000001)?! "requested overshoot peak"']
  lines += [f'    (|u.growth(0,s{int(amount*100)})|<0.000000001 /\\ u.growth(1,s{int(amount*100)})=1)?! "growth endpoints"']
 lines+=['    @:true','::tests()']
 lines += ['::g.kernel('+str(s['index'])+',['+','.join(format(x,'.17f') for x in s['params'])+'],[0])' for s in samples]
 source=out/'test.vkf';source.write_text('\n'.join(lines)+'\n');binary=out/'test';build=subprocess.run([a.compiler,'-b',str(source),'-o',str(binary)],capture_output=True,text=True);assert build.returncode==0,build.stderr
 values=subprocess.check_output([str(binary)],text=True).splitlines();assert values[:2]==['0','true'],values[:2];values=list(map(float,values[2:]));assert len(values)==len(samples)
 max_error=0
 for s,value in zip(samples,values):
  i=s['index'];x,y=s['params']
  if i==0:expected=math.sin(min(math.pi/2,max(0,x*y)))**2
  elif i==1:expected=1+(y+1)*(x-1)**3+y*(x-1)**2
  else:
   phase=(4.5*min(1,max(0,x/.8))+[0,4,2][i-2])%6;rgb=min(1,max(0,abs(phase-3)-1));f=min(1,max(0,(x-.8)/.2));f=f*f*(3-2*f);expected=rgb+(1-rgb)*f
  max_error=max(max_error,abs(value-expected));assert abs(value-expected)<2e-9,(s,value,expected)
 if a.oracle_output:a.oracle_output.write_text(json.dumps({'samples':samples,'nativeValues':values,'source':'actual native Morphing.unfold indexed kernel','independentMaxError':max_error},indent=2)+'\n')
print('PASS native unfold defaults, indexing, zero-speed hold, overshoot peaks and 96 independent numeric comparisons; max error',max_error)
