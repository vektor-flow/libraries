"""Bounded pixel-only rigid registration and collision-checked path research.
No OCR, object names, scene IDs or source drawing commands enter the matcher.
"""
from dataclasses import dataclass
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment

@dataclass
class Region:
    points: np.ndarray
    center: np.ndarray
    mass: int


def segment(mask, join=8):
    mask=np.asarray(mask,dtype=bool)
    if mask.ndim!=2 or not mask.any(): raise ValueError('Expected a nonempty 2D foreground mask')
    # Isotropic multiscale grouping; retain original material, not dilated pixels.
    grouping=ndi.maximum_filter(mask,size=2*join+1)
    labels,count=ndi.label(grouping)
    result=[]
    for k in range(1,count+1):
        y,x=np.nonzero(mask & (labels==k))
        if not len(x): continue
        p=np.column_stack((x,y)).astype(float);center=p.mean(axis=0)
        result.append(Region(p-center,center,len(p)))
    return result


def rotation(angle):
    c,s=np.cos(angle),np.sin(angle)
    return np.array([[c,-s],[s,c]])


def rigid_fit(a,b):
    # Deterministic subsampling of raster material, rotation search + refinement.
    p=a.points[::max(1,len(a.points)//1800)]
    q=b.points[::max(1,len(b.points)//1800)]
    tq=cKDTree(q)
    def score(angle):
        r=p@rotation(angle).T
        return (np.mean(tq.query(r)[0]**2)+np.mean(cKDTree(r).query(q)[0]**2))/2
    angles=np.arange(-180,180,15)*np.pi/180
    angle=min(angles,key=lambda x:(round(score(x),8),abs(x)))
    for step in [3, .5, .1]:
        angle=min(angle+np.arange(-5,6)*step*np.pi/180,key=lambda x:(round(score(x),8),abs(x)))
    error=float(np.sqrt(score(angle)))
    # Raster uncertainty must not turn a translation into a gratuitous spin.
    # Keep a real rotation when it substantially improves geometric agreement.
    translation_error=float(np.sqrt(score(0.)))
    if translation_error<=error+.35:
        return 0.,translation_error
    return float(angle),error


def match(source,target):
    if len(source)!=len(target): raise ValueError('Split/merge needs a multiscale correspondence solver; not silently forced')
    if len(source)>32: raise ValueError('Research candidate bounded to 32 regions')
    fits=[[rigid_fit(a,b) for b in target] for a in source]
    costs=np.array([[fit[1]+40*abs(np.log(a.mass/b.mass)) for b,fit in zip(target,row)] for a,row in zip(source,fits)])
    rows,cols=linear_sum_assignment(costs)
    return [dict(source=int(i),target=int(j),angle=fits[i][j][0],error=fits[i][j][1],mass_ratio=target[j].mass/source[i].mass,
                 mode='rigid' if fits[i][j][1]<2 and abs(target[j].mass/source[i].mass-1)<.035 else 'needs-deformation') for i,j in zip(rows,cols)]


def clock(t): return t*t*t*(10+t*(-15+6*t))


def positions(region,target,angle,t,amplitude):
    u=clock(t);delta=target.center-region.center
    normal=np.array([-delta[1],delta[0]])/max(np.linalg.norm(delta),1)
    center=(1-u)*region.center+u*target.center+normal*amplitude*4*u*(1-u)
    return region.points@rotation(u*angle).T+center


def raster(points,shape):
    xy=np.rint(points).astype(int);h,w=shape
    valid=(xy[:,0]>=0)&(xy[:,0]<w)&(xy[:,1]>=0)&(xy[:,1]<h)
    if not valid.all(): raise ValueError('Path leaves the canvas')
    mask=np.zeros(shape,bool);mask[xy[:,1],xy[:,0]]=True
    return mask


def plan_paths(source,target,matches,shape):
    if any(m['mode']!='rigid' for m in matches): raise ValueError('Residual deformation remains explicit; no pretend rigid fit')
    # Bounded search over simultaneous curved paths. Refuse if no candidate passes.
    # Every material particle carries unit mass; raster occupancy is not mass.
    for amplitude in [0,60,-60,120,-120,180,-180,240,-240,300,-300]:
        safe=True;minimum=1e9
        for t in np.linspace(0,1,65):
            masks=[];margins=[]
            for m in matches:
                a,b=source[m['source']],target[m['target']]
                try: mask=raster(positions(a,b,m['angle'],t,amplitude),shape)
                except ValueError: safe=False;break
                # Bound displacement to the nearest sampled time, including spin.
                travel=np.linalg.norm(b.center-a.center)
                effective_detour=abs(amplitude)*min(travel,1)
                bound=1.875*(travel+4*effective_detour+abs(m['angle'])*np.linalg.norm(a.points,axis=1).max())
                margins.append(bound/128+2)
                masks.append(mask)
            if not safe: break
            for i in range(len(masks)):
                distance=ndi.distance_transform_edt(~masks[i])
                for j in range(i):
                    clearance=float(distance[masks[j]].min())-margins[i]-margins[j]
                    minimum=min(minimum,clearance)
                    if clearance<=0: safe=False;break
                if not safe: break
            if not safe: break
        if safe: return dict(amplitude=amplitude,minimum_certified_clearance=minimum,samples=65)
    raise ValueError('No collision-free candidate within canvas; enlarge space or change constraints')


def partial_match(source,target):
    n,m=len(source),len(target)
    costs=np.full((n+m,n+m),10000.);costs[:n,m:]=2;costs[n:,:m]=2;costs[n:,m:]=0
    fits={}
    for i,a in enumerate(source):
        for j,b in enumerate(target):
            if abs(a.mass/b.mass-1)>.05:continue
            angle,error=rigid_fit(a,b)
            if error>1.4:continue
            fits[i,j]=(angle,error)
            # Geometry dominates; distance only breaks near-ties deterministically.
            costs[i,j]=error+np.linalg.norm(a.center-b.center)*1e-5
    rows,cols=linear_sum_assignment(costs)
    matches=[dict(source=int(i),target=int(j),angle=fits[i,j][0],error=fits[i,j][1],mode='rigid') for i,j in zip(rows,cols) if i<n and j<m and (i,j) in fits]
    unmatched_source=sorted(set(range(n))-{p['source'] for p in matches})
    unmatched_target=sorted(set(range(m))-{p['target'] for p in matches})
    ambiguous=sum(sum(abs(costs[p['source'],j]-costs[p['source'],p['target']])<.15 for j in range(m))>1 for p in matches)
    return dict(matches=matches,unmatched_source=unmatched_source,unmatched_target=unmatched_target,ambiguous_matches=int(ambiguous))

def infer_pixel_pair(a,b,scales=(0,2,5,9)):
    """Input masks only: no TeX, labels, object IDs or test-case metadata."""
    runs=[];candidates=[]
    for scale in scales:
        source,target=segment(a,scale),segment(b,scale)
        if max(len(source),len(target))>32:continue
        correspondence=partial_match(source,target)
        recovered=sum(source[p['source']].mass for p in correspondence['matches'])/int(np.count_nonzero(a))
        run=dict(scale=scale,source_parts=len(source),target_parts=len(target),matched_source_fraction=recovered,**correspondence)
        runs.append(run);candidates.append((recovered-.0001*len(source),source,target,run))
    if not candidates:raise ValueError('No bounded partition candidate')
    _,source,target,best=max(candidates,key=lambda x:x[0])
    return source,target,best,runs
