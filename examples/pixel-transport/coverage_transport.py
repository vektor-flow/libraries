"""Image-only coverage events: infer parents, bud, fade and absorb.
This explicit source/sink policy is not a mass-conserving split/merge optimizer.
"""
from dataclasses import dataclass
import numpy as np
from scipy import ndimage as ndi
from pixel_transport import Region,partial_match,clock,rotation,rigid_fit

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
    def parent(region,candidates):
        if not candidates:return None
        similar=[]
        for index,part in candidates:
            if abs(region.mass/part.region.mass-1)<.1:
                _,error=rigid_fit(region,part.region)
                if error<1.4:similar.append((error+.001*np.linalg.norm(region.center-part.region.center),index))
        if similar:return min(similar)[1]
        return min(candidates,key=lambda pair:np.linalg.norm(region.center-pair[1].region.center))[0]
    retained_source=[(m['source'],source[m['source']]) for m in mapping['matches']]
    retained_target=[(m['target'],target[m['target']]) for m in mapping['matches']]
    births={j:parent(target[j].region,retained_source or list(enumerate(source))) for j in mapping['unmatched_target']}
    deaths={i:parent(source[i].region,retained_target or list(enumerate(target))) for i in mapping['unmatched_source']}
    return dict(source=source,target=target,mapping=mapping,birth_parents=births,death_parents=deaths,pixel_scale=pixel_scale,extent=np.array(np.shape(start)[::-1])/pixel_scale)


def event_states(plan,t,detour=0,event_lift=24):
    if not np.isfinite(t) or t<0 or t>1:raise ValueError('Time outside [0,1]')
    u=clock(t);result=[];source_motion={};target_motion={}
    def curve(a,b,lift):
        delta=b-a;normal=np.array([-delta[1],delta[0]])/max(np.linalg.norm(delta),1)
        return (1-u)*a+u*b+normal*lift*4*u*(1-u)
    for m in plan['mapping']['matches']:
        a=plan['source'][m['source']].region;b=plan['target'][m['target']].region
        center=curve(a.center,b.center,detour);key=('m',m['source'])
        source_motion[m['source']]=(center,key);target_motion[m['target']]=(center,key)
        result.append(dict(kind='matched',key=key,parent=None,source=m['source'],target=m['target'],center=center,source_angle=u*m['angle'],target_angle=(u-1)*m['angle'],scale=1.,opacity=1.,blend=u))
    for i in plan['mapping']['unmatched_source']:
        start=plan['source'][i].region.center;j=plan['death_parents'][i]
        if j is None:end=start+np.array([0.,24.]);parent=None
        else:end,parent=target_motion.get(j,(plan['target'][j].region.center,('b',j)))
        result.append(dict(kind='death',key=('d',i),parent=parent,source=i,center=curve(start,end,event_lift),scale=1-.55*u,opacity=1-u))
    for j in plan['mapping']['unmatched_target']:
        end=plan['target'][j].region.center;i=plan['birth_parents'][j]
        if i is None:start=end-np.array([0.,24.]);parent=None
        else:start,parent=source_motion.get(i,(plan['source'][i].region.center,('d',i)))
        result.append(dict(kind='birth',key=('b',j),parent=parent,target=j,center=curve(start,end,-event_lift),scale=.45+.55*u,opacity=u))
    return result


def related_events(a,b):
    # Contact is intentional inside a budding/absorption family.
    return a['parent']==b['key'] or b['parent']==a['key'] or (a['parent'] is not None and a['parent']==b['parent'])
