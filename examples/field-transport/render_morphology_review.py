"""Render one review clip per solver; stack clips externally for comparison.

No GPU execution. Geometry and validation are replayed from benchmark inputs.
The lossless clip is decoded and checked against every submitted RGB frame.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--solver-dir',type=Path);p.add_argument('--label',required=True)
    p.add_argument('--cases',nargs='+',required=True)
    p.add_argument('--planner',choices=['combined','validated'],default='combined')
    p.add_argument('--diagnostic',action='store_true',help='Render rejected baseline frames with validation explicitly disabled')
    args=p.parse_args()
    if args.output.exists():p.error('Output must be new')
    if args.solver_dir:sys.path.insert(0,str(args.solver_dir.resolve()))
    from combined_transport import CombinedScene
    if args.planner=="validated":
        from validated_transport import ValidatedCombinedScene as CombinedScene
    cases={item['id']:item for item in json.loads(args.inputs.read_text())}
    if set(args.cases)-cases.keys():p.error('Unknown cases')
    hashes=[];receipts=[]
    ff=subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','720x640','-framerate','60','-i','-','-an','-c:v','libx264rgb','-crf','0','-preset','fast',str(args.output)],stdin=subprocess.PIPE)
    try:
        for name in args.cases:
            item=cases[name]
            a,b=[[[np.array(q) for q in body] for body in side] for side in item['geometry']]
            plan=CombinedScene(a,b)
            for index,t in enumerate(np.linspace(0,1,156)):
                ims,_=plan.images(float(t),validate=not args.diagnostic);mask=np.max(ims,axis=0)
                # Identical, fixed spatial mapping in both comparison panels.
                ink=Image.fromarray(mask[140:580,420:860]).resize((560,560),Image.Resampling.LANCZOS)
                image=Image.new('RGB',(720,640),(12,20,26))
                image.paste((65,221,235),(80,60,640,620),ink)
                draw=ImageDraw.Draw(image)
                draw.text((24,12),args.label,fill='white',font_size=24)
                draw.text((24,42),name+' | '+','.join(k for k,_ in plan.groups),fill=(180,190,200),font_size=19)
                raw=image.tobytes()
                for _ in range(13 if index in [0,155] else 1):
                    ff.stdin.write(raw);hashes.append(hashlib.sha256(raw).hexdigest())
            receipts.append(dict(case=name,diagnostic_validation_disabled=args.diagnostic,kinds=[k for k,_ in plan.groups],motion_states=156,frames=180))
            print(name,flush=True)
    finally:
        ff.stdin.close();status=ff.wait()
    if status:raise RuntimeError('Encoding failed')
    decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(args.output),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    for index,want in enumerate(hashes):
        raw=decoder.stdout.read(720*640*3)
        if hashlib.sha256(raw).hexdigest()!=want:raise ValueError(('Decoded frame differs',index))
    if decoder.stdout.read(1) or decoder.wait():raise ValueError('Unexpected decoded stream')
    args.output.with_suffix('.json').write_text(json.dumps(dict(cases=receipts,frames=len(hashes),fps=60,decoded_frames_exact=True,sha256=hashlib.sha256(args.output.read_bytes()).hexdigest()),indent=2)+'\n')


if __name__=='__main__':main()
