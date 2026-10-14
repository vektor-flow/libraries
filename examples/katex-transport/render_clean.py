"""One visible state; preserve high-resolution KaTeX alpha, no overlays or labels.
Correspondence and motion come from the existing blind image-pair plan.
"""
import json,sys,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from pixel_transport import segment,positions,clock

base=Path(sys.argv[1]);high=Path(sys.argv[2]);W,H=1280,720;scale=3
case=json.loads((base/'results.json').read_text())['cases'][1]
assert case['id']=='02-reorder' and case['path']
entry=next(s for s in case['scales'] if s['scale']==case['selected_scale'])
a=np.asarray(Image.open(base/'02-reorder-from.png').convert('L'))>127
b=np.asarray(Image.open(base/'02-reorder-to.png').convert('L'))>127
source,target=segment(a,entry['scale']),segment(b,entry['scale'])
alpha=np.asarray(Image.open(high/'02-reorder-from.png').convert('L'))
labels,count=ndi.label(alpha>0)
assert count==len(source)==3
sprites=[]
for r in source:
    distances=[]
    for k in range(1,count+1):
        yy,xx=np.nonzero(labels==k);distances.append(np.linalg.norm(np.array([xx.mean(),yy.mean()])/scale-r.center))
    k=int(np.argmin(distances))+1;assert min(distances)<1
    yy,xx=np.nonzero(labels==k);x0,y0=xx.min()-2,yy.min()-2;x1,y1=xx.max()+3,yy.max()+3
    isolated=np.where(labels[y0:y1,x0:x1]==k,alpha[y0:y1,x0:x1],0).astype('uint8')
    sprites.append((Image.fromarray(isolated),np.array([x0,y0])))
ff=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-movflags','+faststart',str(high/'katex-one-animation.mp4')],stdin=subprocess.PIPE)
for frame in range(210):
    t=max(0,min(1,(frame-30)/149));u=clock(t)
    total=np.zeros((H,W),float)
    for m in entry['matches']:
        r=source[m['source']];sprite,crop=sprites[m['source']]
        samples=positions(r,target[m['target']],m['angle'],t,case['path']['amplitude'])
        center=samples.mean(axis=0)*scale+np.array([W/2-480*scale,H/2-270*scale])
        angle=m['angle']*u;c,s=np.cos(angle),np.sin(angle)
        R=np.array([[c,-s],[s,c]]);K=center-R@(scale*r.center)
        v=-R.T@K-crop
        coefficients=(c,s,v[0],-s,c,v[1])
        rendered=sprite.transform((W,H),Image.Transform.AFFINE,coefficients,resample=Image.Resampling.BICUBIC)
        coverage=np.asarray(rendered)/255
        total=1-(1-total)*(1-coverage)
    pixels=np.array([16,25,25])[None,None,:]+total[:,:,None]*np.array([221,218,212])[None,None,:]
    image=Image.fromarray(np.uint8(np.clip(pixels,0,255)))
    if frame in [0,105,209]:image.save(high/f'clean-check-{frame}.png')
    ff.stdin.write(image.tobytes())
ff.stdin.close();assert ff.wait()==0
(high/'clean-verification.json').write_text(json.dumps({'source':'KaTeX 0.19.0 browser alpha at device scale 3','mapping':'Original endpoint-only pixel correspondence and checked path','visible_layers':'One evolving expression only; no reference states, ghosts, labels or diagnostics','frames':210,'fps':30,'duration':7,'viewport':[W,H],'scope':'Presentation correction; original approximate endpoint matching limitations remain'},indent=2)+'\n')
print('Rendered clean 7-second KaTeX movie.')
