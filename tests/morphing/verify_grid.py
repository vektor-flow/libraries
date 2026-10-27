"""Compare the bulk 2D field with scalar VKF and an independent f64 oracle."""
from pathlib import Path
import argparse, hashlib, json, random, shutil, struct, subprocess

def number(x):return format(float(x),'.17f')
def vector(xs):return '['+','.join(map(number,xs))+']'
def clamp(x,a,b):return min(b,max(a,x))
def scalar(values,size,stride,carriers,x,y,scale,neck):
    combined=None
    for k in range(carriers):
        base=k*stride;ex=values[base+2]*scale;ey=values[base+3]*scale
        xx=(x-values[base])/ex;yy=(y-values[base+1])/ey
        outside=max(max(abs(xx)-1,abs(yy)-1),-1.)
        gx=clamp((xx+1)*(size-1)/2,0,size-1);gy=clamp((yy+1)*(size-1)/2,0,size-1)
        ix=int(min(gx//1,size-2));iy=int(min(gy//1,size-2));fx=gx-ix;fy=gy-iy
        at=base+4+iy*size+ix
        value=(1-fx)*(1-fy)*values[at]
        value=value+fx*(1-fy)*values[at+1]
        value=value+(1-fx)*fy*values[at+size]
        value=value+fx*fy*values[at+size+1]
        value=(value-max(outside,0))*min(ex,ey)
        if combined is None:combined=value
        elif neck<=0:combined=max(combined,value)
        else:
            h=max(neck-abs(combined-value),0)/neck
            combined=max(combined,value)+neck*h*h/4
    return combined

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--compiler',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    root=Path(__file__).resolve().parents[2];out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'Morphing.vkf').symlink_to(root/'Morphing.vkf');(out/'morphing').symlink_to(root/'morphing',target_is_directory=True)
    rng=random.Random(7391);lines=['g:.morphing.grid','f:.morphing.field','p:.morphing.presentation'];expected=[];counts=[]
    for case in range(20):
        size=[3,7,9,17,33][case%5];carriers=case%4+1;stride=4+size*size
        if size==33:carriers=1
        values=[]
        for k in range(carriers):values += [rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(.2,1.8),rng.uniform(.2,1.8)]+[rng.uniform(-1,1) for _ in range(size*size)]
        xs=[-4.,-1.,0.,1.,4.]+[rng.uniform(-3,3) for _ in range(case%9)]
        ys=[-3.,0.,3.]+[rng.uniform(-2,2) for _ in range(case%7)]
        scale=[.125,.65,1.,2.5][case%4];neck=[0.,.07,.3][case%3]
        values=[float(number(x)) for x in values];xs=[float(number(x)) for x in xs];ys=[float(number(x)) for x in ys]
        want=[scalar(values,size,stride,carriers,x,y,scale,neck) for y in ys for x in xs];expected.append(want);counts.append(len(want))
        lines += [f'case{case}()->bit:',f'    values:{vector(values)}',f'    xs:{vector(xs)}',f'    ys:{vector(ys)}',f'    actual:g.sample(values,{size},{stride},{carriers},xs,ys,{number(scale)},{number(neck)})','    i:0',f'    i<{len(want)}?>',f'        reference:f.cohort(values,2,{size},{stride},{carriers},xs.(i%{len(xs)}),ys.(i//{len(xs)}),0,{number(scale)},{number(neck)})','        (actual.(i)=reference)?! "bulk differs from scalar kernel"','        .i:i+1','    ::actual','    @:true']
    lines += [f'case{i}()' for i in range(20)]
    source=out/'grid.vkf';source.write_text('\n'.join(lines)+'\n')
    b=subprocess.run([a.compiler,'-b',str(source),'-o',str(out/'grid'),'--optimizer-policy','mask-1'],capture_output=True,text=True,timeout=180);(out/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:raise RuntimeError(b.stderr)
    r=subprocess.run([str(out/'grid')],capture_output=True,text=True,timeout=90);(out/'run.log').write_text(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(r.stderr)
    actual=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('[')]
    assert len(actual)==len(expected)
    worst=0.;comparisons=0
    for got,want in zip(actual,expected):
        assert len(got)==len(want)
        for x,y in zip(got,want):
            worst=max(worst,abs(x-y));assert abs(x-y)<2e-13*(1+abs(y));comparisons+=1
    # Keep exact zero-crossing/negative/empty classifications in the clipper.
    for value in [-1.,0.,1.]:
        probe=out/f'clip-{int(value)}.vkf';probe.write_text('p:.morphing.presentation\n::p.triangles('+vector([value]*25)+',5,1,[1,1,1,1])\n')
        binary=probe.with_suffix('');b=subprocess.run([a.compiler,'-b',str(probe),'-o',str(binary)],capture_output=True,text=True,timeout=90);assert b.returncode==0,b.stderr
        run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);assert run.returncode==0,run.stderr
        vertices=json.loads(run.stdout);assert (len(vertices)==0)==(value<0)
    report={'passed':True,'cases':20,'nativeScalarComparisons':comparisons,'independentPythonComparisons':comparisons,'maximumAbsoluteError':worst,'sameScalarOperationOrder':True,'grids':[3,7,9,17,33],'carriers':[1,2,3,4],'compilerSha256':hashlib.sha256(Path(a.compiler).read_bytes()).hexdigest()}
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
