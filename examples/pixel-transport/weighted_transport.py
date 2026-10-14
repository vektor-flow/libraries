"""Bounded surface/trajectory parameter search, evaluated across endpoint pairs.

This is an offline candidate family, not a general variational transport solver.
Weights rank dimensionless measured costs; configuration knobs are kept separate.
"""
from dataclasses import dataclass
import numpy as np
from scipy import ndimage as ndi
from lineage_transport import patch_at, distance_field
from pixel_transport import clock

@dataclass(frozen=True)
class Configuration:
    curvature: float = 0.
    area: float = 0.
    neck: float = 0.
    temporal: float = 0.

# Costs are dimensionless and normalized again across the entire common sweep.
WEIGHTS = {
    'A-area': dict(area=5., reversal=4., vibration=2., thin=1., perimeter=1., transport=1., event=1., topology=3., boundary=2.),
    'B-balanced': dict(area=3., reversal=3., vibration=3., thin=3., perimeter=2., transport=1., event=1., topology=3., boundary=2.),
    'C-rounded': dict(area=2., reversal=2., vibration=3., thin=5., perimeter=5., transport=1., event=1., topology=3., boundary=2.),
}
CONFIGURATIONS = [Configuration()] + [
    Configuration(curvature=c, area=a, neck=n, temporal=s)
    for c,a,n,s in [(0.045,.7,.08,5.),(.08,1.,.12,8.),(.14,1.,.18,12.),(.22,.85,.24,16.)]
]


def calibrate(field, area):
    """Continuous subpixel contour offset, minimizing squared area error."""
    low,high=-float(field.max())-1.,-float(field.min())+1.
    for _ in range(30):
        mid=(low+high)/2
        if np.clip(field+mid+.5,0,1).sum()<area:low=mid
        else:high=mid
    return np.clip(field+(low+high)/2+.5,0,1)


def rounded_connect(alpha, radius):
    """Capsule connections with rounded contact surfaces; no Manhattan strands.

    Only connects lobes within one identity. Length/thickness costs remain in
    the sweep so this local repair is not mistaken for solved cell division.
    """
    result=alpha.copy();added=0
    for _ in range(32):
        labels,count=ndi.label(result>.5)
        if count==1:return result,added
        if not count:raise ValueError('Surface vanished')
        sizes=np.bincount(labels.ravel());sizes[0]=0
        main=labels==sizes.argmax()
        distance,nearest=ndi.distance_transform_edt(~main,return_indices=True)
        q=np.array(np.unravel_index(np.where((labels>0)&~main,distance,np.inf).argmin(),alpha.shape))
        p=nearest[:,q[0],q[1]];d=q-p
        y,x=np.mgrid[:alpha.shape[0],:alpha.shape[1]]
        u=np.clip(((y-p[0])*d[0]+(x-p[1])*d[1])/max(float(d@d),1),0,1)
        capsule=np.clip(radius-np.hypot(y-p[0]-u*d[0],x-p[1]-u*d[1])+.5,0,1)
        added+=int(np.count_nonzero((capsule>.5)&(result<=.5)))
        result=np.maximum(result,capsule)
    raise ValueError('Unresolved surface fragments')


def configure(plan, config):
    for node in plan['nodes']:
        def target_area(n):
            return sum(target_area(c) for c in n.children) if n.children else float(n.final.patch.sum())
        node.target_area=target_area(node)
    if config==Configuration():return
    plan['track_fade']=.16
    def surface(node,t):
        raw,repairs=patch_at(node,t)
        if t==0 or t==1:return raw,repairs
        # Preserve an inferred rigid mapping. No morphology just for styling.
        if node.parent is None and not node.children and hasattr(node,'rigid_angle'):
            return raw,repairs
        u=clock(t)
        envelope=clock(min(t/.16,1))*clock(min((1-t)/.16,1))
        area=(1-u)*node.part.patch.sum()+u*node.target_area
        radius=np.sqrt(max(area,1)/np.pi)
        sigma=max(.001,config.curvature*radius*envelope)
        pad=int(np.ceil(4*sigma+config.neck*radius+5))
        padded=np.pad(raw,pad)
        field=ndi.gaussian_filter(distance_field(padded),sigma,mode='nearest')
        desired=(1-config.area*envelope)*raw.sum()+config.area*envelope*area
        alpha=calibrate(field,desired)
        alpha,extra=rounded_connect(alpha,max(.75,config.neck*radius*envelope))
        # Alternate area projection and local connection; retain feasibility if
        # exact area conflicts with a connected shape in this candidate family.
        for _ in range(2):
            if abs(alpha.sum()-desired)<.1:break
            alpha=calibrate(distance_field(alpha),desired)
            alpha,more=rounded_connect(alpha,max(.75,config.neck*radius*envelope));extra+=more
        return alpha,repairs+extra
    plan['surface']=surface


def sequence_cost(images,metrics,source_area,target_area,events,scale):
    areas=np.array([float(im.sum()/255) for im in images]);times=np.linspace(0,1,len(images))
    wanted=source_area+(target_area-source_area)*np.array([clock(float(t)) for t in times])
    normal=max(source_area,target_area,1.)
    delta=np.diff(areas);sign=np.sign(target_area-source_area)
    reversal=float(np.abs(delta).sum()-abs(areas[-1]-areas[0]))/normal
    thin=[];perimeter=[];holes=[];boundary=[];previous_image=None;previous_delta=None
    for encoded in images:
        image=encoded/255
        mask=image>.5
        holes.append(max(0,ndi.label(~mask)[1]-1))
        if previous_image is not None:
            change=image-previous_image
            if previous_delta is not None:boundary.append(float(np.abs(change-previous_delta).sum()/normal))
            previous_delta=change
        previous_image=image
        opened=ndi.binary_opening(mask,iterations=max(1,int(round(scale))))
        thin.append(np.count_nonzero(mask&~opened)/max(mask.sum(),1))
        edge=np.abs(np.diff(image,axis=0)).sum()+np.abs(np.diff(image,axis=1)).sum()
        perimeter.append(edge**2/max(image.sum(),1))
    # Endpoint-normalized excess avoids rewarding loss of legitimate glyph detail.
    baseline=np.linspace(thin[0],thin[-1],len(thin))
    excess_thin=float(np.mean(np.maximum(0,np.array(thin)-baseline)))
    base_perimeter=np.linspace(perimeter[0],perimeter[-1],len(perimeter))
    excess_perimeter=float(np.mean(np.maximum(0,np.array(perimeter)/np.maximum(base_perimeter,1)-1)))
    velocity={};previous={};accelerations=[];distances=[]
    for row in metrics:
        current={i:np.array(c) for i,c in zip(row['ids'],row['centers'])};new_velocity={}
        for i,c in current.items():
            if i in previous:
                v=(c-previous[i])/np.sqrt(normal);distances.append(float(v@v))
                if i in velocity:accelerations.append(float(np.sum((v-velocity[i])**2)))
                new_velocity[i]=v
        velocity=new_velocity;previous=current
    ideal=(np.arange(len(events))+.5)/max(len(events),1)
    return dict(area=float(np.mean(((areas-wanted)/normal)**2)),reversal=max(0.,reversal),
        vibration=float(np.mean(accelerations) if accelerations else 0)+float(np.mean(np.diff(areas,n=2)**2))/normal**2,
        thin=excess_thin,perimeter=excess_perimeter,transport=float(np.sum(distances)),
        topology=float((np.abs(np.diff(holes)).sum()-abs(holes[-1]-holes[0]))/max(max(holes),1)),
        boundary=float(np.mean(boundary)) if boundary else 0.,
        event=float(np.mean((np.array(events)-ideal)**2)) if len(events) else 0.), dict(
        holes=holes,areas=areas.tolist(),desired_areas=wanted.tolist(),max_area_error=float(np.max(np.abs(areas-wanted))/normal),
        max_area_step=float(np.max(np.abs(delta))/normal),max_thin_fraction=float(max(thin)))


def rank(rows):
    """Common normalization across all candidates/cases, never per weight set."""
    keys=list(next(iter(WEIGHTS.values())))
    # A sparse penalty must not become effectively infinite because most cases
    # score zero (e.g. holes). Normalize by the median positive observation.
    scales={}
    for key in keys:
        positive=[r['costs'][key] for r in rows if r['costs'][key]>1e-12]
        scales[key]=float(np.median(positive)) if positive else 1.
    results={}
    for name,weights in WEIGHTS.items():
        scored=[]
        for candidate in sorted(set(r['candidate'] for r in rows)):
            subset=[r for r in rows if r['candidate']==candidate]
            score=float(np.mean([sum(weights[k]*r['costs'][k]/scales[k] for k in keys)/sum(weights.values()) for r in subset]))
            scored.append(dict(candidate=candidate,score=score))
        results[name]=sorted(scored,key=lambda r:r['score'])
    return dict(normalization=scales,weights=WEIGHTS,rankings=results)
