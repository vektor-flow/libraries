"""Check encoded endpoints and near-end shapes without emitting still previews."""
import sys,json,subprocess,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
folder=Path(sys.argv[1]);out=folder/'weight-sweep';results=[]
movies=sorted(out.glob('*-252.mp4'))
assert len(movies)==18,('Expected three complete six-case movies',len(movies))
for movie in movies:
    name=movie.stem;candidate,case=name.split('-',1);case=case.rsplit('-',1)[0]
    source=np.asarray(Image.open(folder/(case+'-from.png')).convert('L'))[450:1170,800:2080]>127
    target=np.asarray(Image.open(folder/(case+'-to.png')).convert('L'))[450:1170,800:2080]>127
    indices=[0,24,270,272,275,299]
    expression='+'.join(f'eq(n\\,{n})' for n in indices)
    data=subprocess.check_output(['ffmpeg','-v','error','-i',str(movie),'-vf',f'select={expression}', '-fps_mode','vfr','-f','rawvideo','-pix_fmt','rgb24','-'])
    frames=np.frombuffer(data,np.uint8).reshape(-1,720,1280,3);assert len(frames)==len(indices)
    overlaps={}
    for index,rgb in zip(indices,frames):
        actual=rgb[:,:,0]>126;expected=source if index<25 else target
        overlaps[index]=float(np.count_nonzero(actual&expected)/max(np.count_nonzero(actual|expected),1))
    assert overlaps[0]==1 and overlaps[24]==1 and overlaps[275]==1 and overlaps[299]==1,(name,overlaps)
    assert overlaps[270]>.97 and overlaps[272]>.99,(name,overlaps)
    row=json.loads((out/(name+'.json')).read_text());areas=np.array(row['details']['areas']);normal=max(areas[0],areas[-1],1)
    event_indices=np.flatnonzero(np.diff(row['counts']))+1
    results.append(dict(movie=movie.name,sha256=hashlib.sha256(movie.read_bytes()).hexdigest(),silhouette_iou=overlaps,
        max_event_area_step=float(max((abs(areas[k]-areas[k-1])/normal for k in event_indices),default=0)),
        area_error_max=row['details']['max_area_error'],area_reversal=row['costs']['reversal'],hole_reversal=row['costs']['topology']))
    print(name,overlaps,flush=True)
(out/'encoded-shape-verification.json').write_text(json.dumps(results,indent=2)+'\n')
