"""Progressive KaTeX raster benchmark. TeX never enters geometric matching."""
import json,sys,subprocess
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy import ndimage as ndi
from PIL import Image,ImageDraw,ImageFont
import sympy as sp
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from pixel_transport import segment,rigid_fit,plan_paths,positions,infer_pixel_pair

# Independent algebra oracle, deliberately outside the pixel matcher.
ALGEBRA=[('x**2+2*x+1','x**2+2*x+1'),('a+b','b+a'),('a*b+a*c','a*(b+c)'),('x**2+2*x+1','(x+1)**2'),('x**2-y**2','(x-y)*(x+y)'),('(x**2-1)/(x-1)','x+1'),('x+x+x','3*x'),('(2*x+2)/2','x+1'),('x**2+1','(x+1)**2')]

def load_mask(path):return np.array(Image.open(path).convert('L'))>127

def analyse(folder,item,index):
    a,b=load_mask(folder/(item['id']+'-from.png')),load_mask(folder/(item['id']+'-to.png'))
    source,target,best,runs=infer_pixel_pair(a,b)
    valid=sp.simplify(sp.sympify(ALGEBRA[index][0])-sp.sympify(ALGEBRA[index][1]))==0
    assert valid==item['valid']
    route=None;reason='Unmatched material: split/merge, shape change or source/sink needed'
    complete=not best['unmatched_source'] and not best['unmatched_target']
    if complete:
        try:route=plan_paths(source,target,best['matches'],a.shape);reason='Rigid correspondence and conservative path check passed'
        except ValueError as e:reason=str(e)
    result=dict(id=item['id'],title=item['title'],valid_algebra=bool(valid),condition=item.get('condition'),source_mass=int(a.sum()),target_mass=int(b.sum()),mass_delta=int(b.sum())-int(a.sum()),scales=runs,selected_scale=best['scale'],complete_correspondence=complete,path=route,status=reason)
    return result,(a,b,source,target,best,route)

def render(folder,item,result,data):
    a,b,source,target,best,route=data
    w,h=1200,900;offset=np.array([120,200]);font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    titlefont=ImageFont.truetype(font,31);small=ImageFont.truetype(font,20);tiny=ImageFont.truetype(font,17)
    ff=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h}','-framerate','24','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(folder/(item['id']+'.mp4'))],stdin=subprocess.PIPE)
    max_overlap=0;masses=[];endpoint_iou=0
    for frame in range(144):
        t=max(0,min(1,(frame-12)/107))
        density=np.zeros((h,w));layers=[np.zeros((h,w)),np.zeros((h,w))];occupancy=np.zeros((h,w),np.uint16)
        moving={m['source']:m for m in best['matches']}
        for i,r in enumerate(source):
            if i in moving:
                m=moving[i];points=positions(r,target[m['target']],m['angle'],t,route['amplitude'] if route else 45)+offset;layer=0
            else:points=r.points+r.center+offset;layer=1
            base=np.floor(points).astype(int);fraction=points-base
            for dx,dy in [(0,0),(1,0),(0,1),(1,1)]:
                weights=(fraction[:,0] if dx else 1-fraction[:,0])*(fraction[:,1] if dy else 1-fraction[:,1])
                if np.any(base[:,0]+dx<0) or np.any(base[:,0]+dx>=w) or np.any(base[:,1]+dy<0) or np.any(base[:,1]+dy>=h):raise ValueError('frame clipping')
                np.add.at(layers[layer],(base[:,1]+dy,base[:,0]+dx),weights)
            xy=np.rint(points).astype(int);occupied=np.zeros((h,w),bool);occupied[xy[:,1],xy[:,0]]=1;occupancy+=occupied
        density=layers[0]+layers[1];masses.append(float(density.sum()));overlap=int(np.count_nonzero(occupancy>1));max_overlap=max(max_overlap,overlap)
        # Grey target is a reference overlay, not transported material.
        rgb=np.zeros((h,w,3))+np.array([16,25,25]);rgb[200:740,120:1080]+=b[:,:,None]*np.array([25,31,28])
        for layer,color in zip(layers,([137,228,177],[245,181,91])):
            alpha=np.minimum(1,layer)[:,:,None];rgb=rgb*(1-alpha)+np.array(color)*alpha
        image=Image.fromarray(np.uint8(np.clip(rgb,0,255)));draw=ImageDraw.Draw(image)
        draw.text((35,25),'VEKTOR FLOW · KaTeX pixel stress tests',font=small,fill='#b6c7bd');draw.text((35,62),item['title'],font=titlefont,fill='#edf3ed')
        for side,x in [('from',45),('to',650)]:
            im=Image.open(folder/(item['id']+'-'+side+'.png')).convert('L');box=im.getbbox();im=im.crop(box);im.thumbnail((480,100))
            image.paste(Image.new('RGB',im.size,'#edf3ed'),(x,160),im)
            draw.text((x,125),'SOURCE' if side=='from' else 'TARGET',font=tiny,fill='#b6c7bd')
        accepted=route is not None
        draw.text((35,755),'Checked rigid motion' if accepted else 'PARTIAL DIAGNOSTIC — not a completed transformation',font=small,fill='#89e4b1' if accepted else '#f5b55b')
        draw.text((35,790),f"Green: matched    Amber: unresolved source    Grey: target reference    {round(t*100)}%",font=tiny,fill='#b6c7bd')
        draw.text((35,820),f"Source mass {result['source_mass']} → target mass {result['target_mass']}  |  observed overlap {overlap} pixels",font=tiny,fill='#b6c7bd')
        status=result['status']+('  |  '+item['condition'] if item.get('condition') else '')
        draw.text((35,850),status[:115],font=tiny,fill='#b6c7bd')
        ff.stdin.write(image.tobytes())
        if frame==143:
            rendered=density[200:740,120:1080]>.5
            endpoint_iou=float(np.count_nonzero(rendered & b)/np.count_nonzero(rendered | b))
    ff.stdin.close();assert ff.wait()==0
    assert max(masses)-min(masses)<1e-7
    result.update(observed_max_overlap_pixels=max_overlap,rendered_endpoint_iou=endpoint_iou,deposited_mass_range=[min(masses),max(masses)],frames=144,duration=6)

if __name__=='__main__':
    folder=Path(sys.argv[1]);inputs=json.loads((folder/'inputs.json').read_text());results=[]
    for index,item in enumerate(inputs['cases']):
        result,data=analyse(folder,item,index);print(item['id'],result['status'],flush=True)
        render(folder,item,result,data);results.append(result)
        (folder/'results.json').write_text(json.dumps(dict(katex=inputs['katex'],cases=results),indent=2)+'\n')
    (folder/'concat.txt').write_text(''.join("file '%s.mp4'\n"%item['id'] for item in inputs['cases']))
