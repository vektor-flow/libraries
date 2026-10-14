"""Raster fixtures → blind segmentation/matching → verified motion → MP4."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw,ImageFont
from pixel_transport import segment,match,plan_paths,positions,clock

W,H=1200,900
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def sentence(text):
    font=ImageFont.truetype(FONT,38);box=font.getbbox(text)
    image=Image.new('L',(box[2]+4,box[3]-box[1]+4));ImageDraw.Draw(image).text((2,2-box[1]),text,font=font,fill=255)
    return image

def paste(image,sprite,center,angle=0):
    sprite=sprite.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
    image.paste(sprite,(round(center[0]-sprite.width/2),round(center[1]-sprite.height/2)))

def fixture(kind):
    a=Image.new('L',(W,H));b=Image.new('L',(W,H))
    first=sentence('Ideas can change the world.')
    second=sentence('Motion can explain a thought.')
    if kind=='sentences':
        paste(a,first,(600,270));paste(a,second,(600,630))
        paste(b,second,(600,270));paste(b,first,(600,630))
    elif kind=='rotation':
        paste(a,first,(600,440));paste(b,first,(600,440),32)
    else:
        # Same foreground colour; geometry alone identifies these disconnected objects.
        x=ImageDraw.Draw(a);y=ImageDraw.Draw(b)
        x.polygon([(230,320),(150,520),(310,520)],fill=255)
        x.ellipse((820,330,1010,520),fill=255);x.ellipse((864,374,966,476),fill=0)
        y.polygon([(910,320),(830,520),(990,520)],fill=255)
        y.ellipse((140,330,330,520),fill=255);y.ellipse((184,374,286,476),fill=0)
    return np.array(a)>127,np.array(b)>127

def render(out,kind):
    a,b=fixture(kind)
    source,target=segment(a,join=9),segment(b,join=9)
    print(kind,'regions',len(source),len(target),flush=True)
    matches=match(source,target);print('matches',matches,flush=True)
    route=plan_paths(source,target,matches,(H,W));print('route',route,flush=True)
    Image.fromarray(a).save(out/(kind+'-source.png'));Image.fromarray(b).save(out/(kind+'-target.png'))
    ff=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate','24','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out/(kind+'.mp4'))],stdin=subprocess.PIPE)
    titles={'sentences':'Real sentences exchange places','rotation':'Recognize rotation, preserve the letters','objects':'Objects travel around each other'}
    heading=ImageFont.truetype(FONT,35);small=ImageFont.truetype(FONT,21)
    min_mass=1e99;max_mass=0
    for f in range(180):
        t=max(0,min(1,(f-12)/143))
        density=np.zeros((H,W),float)
        for m in matches:
            points=positions(source[m['source']],target[m['target']],m['angle'],t,route['amplitude'])
            # Bilinear deposition: every source pixel retains exactly unit mass.
            base=np.floor(points).astype(int);frac=points-base
            for dx,dy in [(0,0),(1,0),(0,1),(1,1)]:
                weights=(frac[:,0] if dx else 1-frac[:,0])*(frac[:,1] if dy else 1-frac[:,1])
                np.add.at(density,(base[:,1]+dy,base[:,0]+dx),weights)
        mass=float(density.sum());min_mass=min(min_mass,mass);max_mass=max(max_mass,mass)
        alpha=np.minimum(1,density)
        rgb=np.array([16,25,25])[None,None,:]+alpha[:,:,None]*np.array([121,203,152])[None,None,:]
        frame=Image.fromarray(np.uint8(np.clip(rgb,0,255)))
        draw=ImageDraw.Draw(frame)
        draw.text((45,35),'VEKTOR FLOW · PIXEL TRANSPORT RESEARCH',font=small,fill='#b6c7bd')
        draw.text((45,75),titles[kind],font=heading,fill='#edf3ed')
        draw.text((45,795),'Pixels only → segmentation → matching → rigid paths',font=small,fill='#b6c7bd')
        draw.text((45,830),f'Conserved material: {sum(x.mass for x in source):,}  ·  No object overlap  ·  {round(t*100)}%',font=small,fill='#b6c7bd')
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    if ff.wait():raise RuntimeError('Video encoding failed')
    assert max_mass-min_mass<1e-7
    receipt=dict(kind=kind,matches=matches,path=route,mass_range=[min_mass,max_mass],duration=7.5,source_regions=len(source),target_regions=len(target),note='Binary foreground masks; heuristic grouping and rigid registration, not arbitrary RGB segmentation or split/merge solver')
    (out/(kind+'-verification.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print('Rendered',kind,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output');parser.add_argument('kinds',nargs='*',default=['sentences','rotation','objects']);args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    for kind in args.kinds:render(out,kind)
