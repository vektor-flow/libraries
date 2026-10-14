"""Image-only coverage events: retain matches, grow births, contract deaths.
This explicit source/sink policy is not a mass-conserving split/merge optimizer.
"""
from dataclasses import dataclass
import numpy as np
from scipy import ndimage as ndi
from pixel_transport import Region,partial_match,clock,rotation

@dataclass
class CoveragePart:
    region: Region
    patch: np.ndarray
    origin: np.ndarray


def coverage_parts(image,pixel_scale=1):
    alpha=np.asarray(image,dtype=float)
    if alpha.ndim!=2 or not np.isfinite(alpha).all() or alpha.min()<0 or alpha.max()>1:raise ValueError('Expected finite 2D coverage in [0,1]')
    if not np.isfinite(pixel_scale) or pixel_scale<=0:raise ValueError('Invalid pixel scale')
    labels,n=ndi.label(alpha>0)
    if n>64:raise ValueError('Bounded coverage candidate supports at most 64 components')
    parts=[]
    for k in range(1,n+1):
        y,x=np.nonzero(labels==k);weights=alpha[y,x]
        p=np.column_stack((x,y))/pixel_scale
        center=np.average(p,axis=0,weights=weights)
        x0,y0=x.min(),y.min();x1,y1=x.max()+1,y.max()+1
        patch=np.where(labels[y0:y1,x0:x1]==k,alpha[y0:y1,x0:x1],0)
        region=Region(p-center,center,float(weights.sum()/pixel_scale**2))
        parts.append(CoveragePart(region,patch,np.array([x0,y0])))
    return parts


def plan_coverage_pair(start,end,pixel_scale=1):
    if np.shape(start)!=np.shape(end):raise ValueError('Endpoint image extents must agree')
    source=coverage_parts(start,pixel_scale);target=coverage_parts(end,pixel_scale)
    mapping=partial_match([p.region for p in source],[p.region for p in target])
    return dict(source=source,target=target,mapping=mapping,pixel_scale=pixel_scale,extent=np.array(np.shape(start)[::-1])/pixel_scale)


def event_states(plan,t,detour=0,event_lift=0):
    if not np.isfinite(t) or t<0 or t>1:raise ValueError('Time outside [0,1]')
    u=clock(t);result=[]
    for m in plan['mapping']['matches']:
        a=plan['source'][m['source']].region;b=plan['target'][m['target']].region
        delta=b.center-a.center;normal=np.array([-delta[1],delta[0]])/max(np.linalg.norm(delta),1)
        center=(1-u)*a.center+u*b.center+normal*detour*4*u*(1-u)
        result.append(dict(kind='matched',source=m['source'],target=m['target'],center=center,source_angle=u*m['angle'],target_angle=(u-1)*m['angle'],scale=1.,blend=u))
    for i in plan['mapping']['unmatched_source']:
        result.append(dict(kind='death',source=i,center=plan['source'][i].region.center+np.array([0,event_lift*u]),scale=1-u))
    for j in plan['mapping']['unmatched_target']:
        result.append(dict(kind='birth',target=j,center=plan['target'][j].region.center-np.array([0,event_lift*(1-u)]),scale=u))
    return result
