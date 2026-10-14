"""Image-only rigid motion, residual material transport, budding and absorption."""
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
    residual=material_plan(source,target,mapping,pixel_scale)
    births={j:parent(target[j].region,retained_source or list(enumerate(source))) for j in mapping['unmatched_target']}
    deaths={i:parent(source[i].region,retained_target or list(enumerate(target))) for i in mapping['unmatched_source']}
    return dict(source=source,target=target,mapping=mapping,material=residual,birth_parents=births,death_parents=deaths,pixel_scale=pixel_scale,extent=np.array(np.shape(start)[::-1])/pixel_scale)


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
    if plan['material'] is not None:
        result.append(dict(kind='morph',key=('morph',0),parent=None,center=np.zeros(2),opacity=1.,blend=u,lift=event_lift))
        return result
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


def material_plan(source,target,mapping,pixel_scale,max_samples=1600):
    """Bounded equal-mass sample assignment, lifted to both endpoint rasters.

    All residual components participate together, so component counts need not
    agree. No symbols, object names or source drawing instructions enter here.
    Endpoint mass differences use smooth density change on the transported
    material, rather than separate simultaneous destruction and creation.
    """
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial import cKDTree
    from scipy.spatial.distance import cdist
    def collect(parts,indices):
        points=[];weights=[]
        for i in indices:
            part=parts[i];y,x=np.nonzero(part.patch)
            points.append((np.column_stack((x,y))+part.origin)/pixel_scale)
            weights.append(part.patch[y,x]/pixel_scale**2)
        return np.concatenate(points),np.concatenate(weights)
    if not mapping['unmatched_source'] or not mapping['unmatched_target']:return None
    a,wa=collect(source,mapping['unmatched_source']);b,wb=collect(target,mapping['unmatched_target'])
    count=min(max_samples,max(len(a),len(b)))
    def sample(points,weights):
        cdf=np.cumsum(weights);q=(np.arange(count)+.5)*cdf[-1]/count
        return points[np.searchsorted(cdf,q)]
    pa=sample(a,wa);pb=sample(b,wb)
    rows,cols=linear_sum_assignment(cdist(pa,pb,'sqeuclidean'))
    pa=pa[rows];pb=pb[cols]
    def lift(points,anchors,displacements):
        distance,index=cKDTree(anchors).query(points,k=min(4,len(anchors)))
        if distance.ndim==1:return displacements[index]
        w=1/np.maximum(distance,.05)**2;w/=w.sum(axis=1)[:,None]
        return np.sum(displacements[index]*w[:,:,None],axis=1)
    return dict(source_points=a,target_points=b,source_weights=wa,target_weights=wb,
                source_displacement=lift(a,pa,pb-pa),target_displacement=lift(b,pb,pa-pb),
                sample_count=count,source_mass=float(wa.sum()),target_mass=float(wb.sum()),
                sample_transport_cost=float(np.mean(np.sum((pb-pa)**2,axis=1))))


def material_particles(material,t,lift=0):
    """Two quadratures of the same transported density, exact at endpoints.

    Quadrature weights blend, but material itself moves and deforms throughout.
    Total particle mass follows the quintic interpolation of endpoint mass.
    """
    if not np.isfinite(t) or not 0<=t<=1:raise ValueError('Time outside [0,1]')
    u=clock(t);groups=[]
    for side,fraction,weight in [('source',u,1-u),('target',1-u,u)]:
        if weight==0:continue
        points=material[side+'_points'];delta=material[side+'_displacement']
        forward=delta if side=='source' else -delta
        normal=np.column_stack((-forward[:,1],forward[:,0]))/np.maximum(np.linalg.norm(forward,axis=1)[:,None],1)
        positions=points+fraction*delta+normal*lift*4*u*(1-u)
        groups.append((positions,material[side+'_weights']*weight))
    return groups


def splat_material(material,t,size,factor,offset,lift=0):
    """Bilinear particle coverage. Raw mass is measured before saturation."""
    width,height=size;flat=np.zeros(width*height)
    for points,weights in material_particles(material,t,lift):
        p=points*factor+offset;xy=np.floor(p).astype(int);f=p-xy
        weights=weights*factor**2
        for dx,dy in [(0,0),(1,0),(0,1),(1,1)]:
            x=xy[:,0]+dx;y=xy[:,1]+dy
            w=weights*(f[:,0] if dx else 1-f[:,0])*(f[:,1] if dy else 1-f[:,1])
            valid=(x>=0)&(x<width)&(y>=0)&(y<height)
            flat+=np.bincount(y[valid]*width+x[valid],weights=w[valid],minlength=width*height)
    return np.clip(flat.reshape(height,width),0,1)
