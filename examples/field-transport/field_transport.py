"""Same-topology contour transport from scalar signed distance, not RGB median.
Research adapter: equal contour nesting only. Topology-changing inputs fail closed.
"""
import gzip,json,hashlib
from pathlib import Path
import contourpy
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment
from PIL import Image,ImageDraw

def clock(t):return t*t*t*(10+t*(-15+6*t))
def area(p):return .5*np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1))
def topology(mask):
    return int(ndi.label(mask)[1]),int(ndi.label(ndi.binary_fill_holes(mask)&~mask)[1])

def resample(p,n=512):
    if np.linalg.norm(p[0]-p[-1])>1e-8:p=np.vstack([p,p[0]])
    ds=np.linalg.norm(np.diff(p,axis=0),axis=1);keep=np.r_[True,ds>1e-10];p=p[keep]
    lengths=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    q=np.linspace(0,lengths[-1],n,endpoint=False)
    return np.column_stack([np.interp(q,lengths,p[:,i]) for i in range(2)])

class Atlas:
    def __init__(self,folder):
        self.folder=Path(folder);raw=(self.folder/'atlas.rgba.gz').read_bytes();meta=(self.folder/'typing-data.json').read_bytes()
        self.data=json.loads(meta);w,h=self.data['atlasSize'];self.rgba=np.frombuffer(gzip.decompress(raw),np.uint8).reshape(h,w,4)
        self.provenance=dict(atlas_sha256=hashlib.sha256(raw).hexdigest(),metadata_sha256=hashlib.sha256(meta).hexdigest(),channel='alpha: scalar signed distance; never opacity or RGB median',range_texels=self.data['range'])
    def field(self,key):
        t=self.data['tiles'][key];w,h=self.data['atlasSize'];x,y,X,Y=np.rint(np.array(t['uv'])*[w,h,w,h]).astype(int)
        return (self.rgba[y:Y,x:X,3].astype(float)/255-.5)*self.data['range']
    def loops(self,key,height=280):
        f=self.field(key)
        loops=contourpy.contour_generator(z=f).lines(0)
        points=np.concatenate(loops);lo=points.min(0);hi=points.max(0)
        # Common isotropic placement, no silhouette-dependent affine distortion.
        scale=height/(hi[1]-lo[1]);center=(lo+hi)/2
        return [resample((p-center)*scale) for p in loops]

def ring(radius=140,width=24):
    # Analytic signed distance: width/2 - abs(norm(p)-midradius).
    a=np.linspace(0,2*np.pi,512,endpoint=False);u=np.column_stack([np.cos(a),np.sin(a)])
    return [radius*u,(radius-width)*u]

def normalize(loops):
    loops=sorted([resample(p) for p in loops],key=lambda p:-abs(area(p)))
    return [p if area(p)>0 else p[::-1] for p in loops]

def raster(loops,size=512,ss=6):
    im=Image.new('L',(size*ss,size*ss));draw=ImageDraw.Draw(im)
    for i,p in enumerate(loops):
        xy=(p+size/2)*ss
        draw.polygon([tuple(q) for q in xy],fill=255 if i==0 else 0)
    return np.array(im.resize((size,size),Image.Resampling.LANCZOS))

class Transport:
    def __init__(self,start,end):
        self.a=normalize(start);b=normalize(end)
        if len(self.a)!=len(b):raise ValueError('Topology changes require a separate split/merge plan')
        if topology(raster(self.a)>127)!=(1,len(self.a)-1) or topology(raster(b)>127)!=(1,len(b)-1):raise ValueError('Expected one exterior with disjoint enclosed holes')
        if len(b)>2:
            costs=np.array([[np.linalg.norm(x.mean(0)-y.mean(0)) for y in b[1:]] for x in self.a[1:]])
            _,cols=linear_sum_assignment(costs);b=[b[0]]+[b[1+j] for j in cols]
        self.b=[]
        for x,y in zip(self.a,b):
            # Endpoint geometry only; cyclic phase minimizes boundary transport.
            costs=[np.sum((x-np.roll(y,k,axis=0))**2) for k in range(len(y))]
            self.b.append(np.roll(y,int(np.argmin(costs)),axis=0))
        self.expected=(1,len(self.a)-1)
    def contours(self,t):
        if not 0<=t<=1:raise ValueError('Time outside [0,1]')
        v=clock(t);out=[]
        for a,b in zip(self.a,self.b):
            p=(1-v)*a+v*b
            # Smooth the evolving curve in arc length, not coverage/opacity.
            # Endpoint-zero envelope restores exact endpoint contours without a switch.
            smooth=ndi.gaussian_filter1d(p,5,axis=0,mode='wrap')
            weight=16*v*v*(1-v)*(1-v)
            p=(1-weight)*p+weight*smooth
            desired=(1-v)*area(a)+v*area(b);c=p.mean(0)
            if area(p)<=0:raise ValueError("Contour collapsed or reversed orientation")
            p=c+(p-c)*np.sqrt(desired/area(p))
            out.append(p)
        return out

def crossings(a,b,same=False):
    # Proper segment intersections. Adjacent self edges are excluded.
    p=a[:,None,:];r=(np.roll(a,-1,axis=0)-a)[:,None,:]
    q=b[None,:,:];s=(np.roll(b,-1,axis=0)-b)[None,:,:]
    cross=lambda u,v:u[...,0]*v[...,1]-u[...,1]*v[...,0]
    den=cross(r,s);valid=abs(den)>1e-10
    safe=np.where(valid,den,1);u=cross(q-p,r)/safe;t=cross(q-p,s)/safe
    hits=valid&(u>1e-8)&(u<1-1e-8)&(t>1e-8)&(t<1-1e-8)
    if same:
        ids=np.arange(len(a));hits[ids,ids]=False;hits[ids,(ids+1)%len(a)]=False;hits[ids,(ids-1)%len(a)]=False
    return bool(hits.any())
