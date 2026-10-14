"""Encode existing accepted shared-body frames and verify every decoded count."""
import sys,json,subprocess,argparse
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pixel-transport'))
from continuous_transport import presentation_alpha
p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('cases',nargs='*');args=p.parse_args()
out=args.folder/'coalescence';cases=args.cases or ['06-cancel','07-collect','08-fraction']
for case in cases:
    target=out/(case+'-verification.json')
    row=json.loads(target.read_text());frames=np.load(out/(case+'-frames.npz'))['frames'];video=out/(case+'.mp4')
    ff=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1280x720','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','3','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
    for im in [frames[0]]*24+list(frames)+[frames[-1]]*24:
        alpha=presentation_alpha(im.astype(np.float32)/255)
        rgb=np.array([16,25,25],np.float32)+alpha[:,:,None]*np.array([221,218,212],np.float32)
        ff.stdin.write(np.uint8(np.clip(rgb,0,255)).tobytes())
    ff.stdin.close();assert ff.wait()==0
    decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(video),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE);counts=[]
    endpoint_iou={}
    for k in range(len(frames)+48):
        data=decoder.stdout.read(720*1280*3);assert len(data)==720*1280*3
        mask=np.frombuffer(data,np.uint8).reshape(720,1280,3)[:,:,0]>126
        counts.append(int(ndi.label(mask)[1]))
        if k in [0,24,len(frames)+23,len(frames)+47]:
            want=frames[0 if k<25 else -1]>127
            endpoint_iou[k]=float(np.count_nonzero(mask&want)/np.count_nonzero(mask|want))
    assert not decoder.stdout.read(1);assert decoder.wait()==0
    expected=[row['counts'][0]]*24+row['counts']+[row['counts'][-1]]*24
    mismatch=[i for i,(x,y) in enumerate(zip(counts,expected)) if x!=y]
    (out/(case+'-decoded.json')).write_text(json.dumps(dict(counts=counts,mismatches=mismatch,endpoint_iou=endpoint_iou))+'\n')
    assert not mismatch and all(x==1 for x in endpoint_iou.values()),(case,mismatch,endpoint_iou)
    print('Verified',case,flush=True)

if all((out/(case+'-decoded.json')).exists() for case in cases):
    listing=out/'concat.txt';listing.write_text(''.join(f"file '{case}.mp4'\n" for case in cases))
    subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(out/'coalescence-katex-animations.mp4')],check=True)
