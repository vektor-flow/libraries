"""Endpoint-only monotone lineage candidate. No formula or glyph metadata.
The older pooled-density renderer remains available as prior research evidence.
"""
from dataclasses import dataclass,field
from collections import deque
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment
from coverage_transport import coverage_parts,CoveragePart
from pixel_transport import Region,partial_match,clock

@dataclass
class Node:
    id:int
    part:CoveragePart
    targets:list
    parent:object=None
    birth:float=0.
    split:float=2.
    children:list=field(default_factory=list)
    goal:object=None
    final:object=None


def center(part,scale):
    return (part.origin+(np.array(part.patch.shape[::-1])-1)/2)/scale


def subpart(part,keep,scale):
    patch=part.patch*keep;y,x=np.nonzero(patch)
    x0,x1=x.min(),x.max()+1;y0,y1=y.min(),y.max()+1
    alpha=patch[y0:y1,x0:x1];origin=part.origin+[x0,y0]
    y,x=np.nonzero(alpha);points=(np.column_stack((x,y))+origin)/scale
    weights=alpha[y,x];c=np.average(points,axis=0,weights=weights)
    return CoveragePart(Region(points-c,c,float(weights.sum()/scale**2)),alpha,origin)


def bisect(part,direction,scale):
    """Connected geodesic partition, preserving every endpoint alpha sample."""
    mask=part.patch>.5
    if ndi.label(mask)[1]!=1:raise ValueError('Input component is not visibly connected')
    y,x=np.nonzero(mask);projection=x*direction[0]+y*direction[1]
    seeds=[(int(y[projection.argmin()]),int(x[projection.argmin()])),(int(y[projection.argmax()]),int(x[projection.argmax()]))]
    if seeds[0]==seeds[1]:raise ValueError('Insufficient source material for a split')
    labels=np.zeros(mask.shape,np.uint8);queue=deque()
    for k,(yy,xx) in enumerate(seeds,1):labels[yy,xx]=k;queue.append((yy,xx))
    h,w=mask.shape
    while queue:
        yy,xx=queue.popleft()
        for dy,dx in [(0,1),(1,0),(0,-1),(-1,0)]:
            a,b=yy+dy,xx+dx
            if 0<=a<h and 0<=b<w and mask[a,b] and not labels[a,b]:
                labels[a,b]=labels[yy,xx];queue.append((a,b))
    nearest=ndi.distance_transform_edt(~mask,return_distances=False,return_indices=True)
    labels=labels[tuple(nearest)]
    return [subpart(part,labels==k,scale) for k in [1,2]]


def make_plan(start,end,scale=3):
    original_source=coverage_parts(start,scale);original_target=coverage_parts(end,scale)
    reverse=len(original_source)>len(original_target)
    source,target=(original_target,original_source) if reverse else (original_source,original_target)
    if not source or not target:raise ValueError('Blank endpoint needs a separately planned birth/death policy')
    n,m=len(source),len(target)
    matching=partial_match([p.region for p in source],[p.region for p in target])
    assignment={match['source']:[match['target']] for match in matching['matches']}
    free_source=[i for i in range(n) if i not in assignment]
    used={j for values in assignment.values() for j in values};free_target=[j for j in range(m) if j not in used]
    if free_source:
        costs=np.array([[np.linalg.norm(source[i].region.center-target[j].region.center)+20*abs(np.log(source[i].region.mass/target[j].region.mass)) for j in free_target] for i in free_source])
        rows,cols=linear_sum_assignment(costs)
        for i,j in zip(rows,cols):assignment[free_source[i]]=[free_target[j]]
    used={j for values in assignment.values() for j in values}
    for j in range(m):
        if j not in used:
            i=min(range(n),key=lambda i:np.linalg.norm(source[i].region.center-target[j].region.center)+12*len(assignment[i]))
            assignment[i].append(j)
    nodes=[]
    def build(part,indices,parent=None):
        node=Node(len(nodes),part,indices,parent);nodes.append(node)
        node.goal=np.average([center(target[j],scale) for j in indices],axis=0,weights=[target[j].region.mass for j in indices])
        if len(indices)==1:node.final=target[indices[0]];return node
        locations=np.array([center(target[j],scale) for j in indices]);axis=int(np.var(locations,axis=0).argmax())
        ordered=sorted(indices,key=lambda j:center(target[j],scale)[axis]);half=len(ordered)//2
        left,right=ordered[:half],ordered[half:]
        direction=np.mean([center(target[j],scale) for j in right],axis=0)-np.mean([center(target[j],scale) for j in left],axis=0)
        pieces=bisect(part,direction,scale)
        node.children=[build(p,ids,node) for p,ids in zip(pieces,[left,right])]
        return node
    roots=[build(source[i],assignment[i]) for i in range(n)]
    for match in matching['matches']:
        root=roots[match['source']]
        if len(root.targets)==1:root.rigid_angle=match['angle']
    # Event slots approximate a linear count ramp. A late split has a deformation
    # cost, so candidates may move earlier instead of forcing a rushed finish.
    internal=[node for node in nodes if node.children];pending=roots[:];order=[]
    while pending:
        node=pending.pop(0)
        if node.children:order.append(node);pending.extend(node.children)
    for k,node in enumerate(order):
        ideal=(k+.5)/max(len(internal),1)
        low=node.birth+.10;high=.78
        candidates=np.linspace(max(low,ideal-.12),min(high,max(low,ideal+.12)),17)
        if not len(candidates) or candidates[0]>candidates[-1]:raise ValueError('Too many serial splits for bounded schedule')
        deformation=sum(np.linalg.norm(center(c.part,scale)-c.goal) for c in node.children)/100
        node.split=float(min(candidates,key=lambda t:20*(t-ideal)**2+.025*deformation/(1-t)**2))
        for child in node.children:child.birth=node.split
    # Plan passing lanes before objects touch. Waiting for contact can require
    # a large instantaneous sideways displacement for tall glyphs.
    graph={root.id:set() for root in roots}
    for i,first in enumerate(roots):
        for second in roots[:i]:
            initial=center(first.part,scale)[0]-center(second.part,scale)[0]
            if any(initial*(center(target[a],scale)[0]-center(target[b],scale)[0])<0 for a in first.targets for b in second.targets):
                graph[first.id].add(second.id);graph[second.id].add(first.id)
    colors={}
    for root in sorted(roots,key=lambda node:-len(graph[node.id])):
        if not graph[root.id]:continue
        used={colors[j] for j in graph[root.id] if j in colors}
        colors[root.id]=next(k for k in range(len(roots)) if k not in used)
    levels=max(colors.values(),default=-1)+1
    lanes=np.linspace(-65,65,levels) if levels>2 else np.linspace(-50,50,max(levels,1))
    for root in roots:root.lane=float(lanes[colors[root.id]]) if root.id in colors else 0.
    return dict(roots=roots,nodes=nodes,scale=scale,reverse=reverse,source_count=len(original_source),target_count=len(original_target),events=sorted(n.split for n in internal))


def active_nodes(plan,t):
    result=[]
    def visit(node):
        if node.children and t>node.split:
            for child in node.children:visit(child)
        else:result.append(node)
    for node in plan['roots']:visit(node)
    return result


def desired_center(node,t,scale):
    if node.parent is None:
        u=clock(t)
        lane=getattr(node,'lane',0.)
        travel=clock(float(np.clip((t-.12)/.76,0,1))) if lane else u
        passing=clock(min(t/.5,1))*clock(min((1-t)/.5,1))
        return (1-travel)*center(node.part,scale)+travel*node.goal+np.array([0.,lane*passing])
    parent=desired_center(node.parent,t,scale)
    v=clock(float(np.clip((t-node.birth)/(1-node.birth),0,1)))
    return parent+(1-v)*(center(node.part,scale)-center(node.parent.part,scale))+v*(node.goal-node.parent.goal)


def distance_field(alpha):
    mask=alpha>.5
    value=ndi.distance_transform_edt(mask)-ndi.distance_transform_edt(~mask)
    value-=.5*np.sign(value)
    partial=(alpha>0)&(alpha<1);value[partial]=alpha[partial]-.5
    return value


def patch_at(node,t):
    a=node.part.patch
    if node.children:return a,0
    b=node.final.patch
    v=clock(float(np.clip((t-node.birth)/(1-node.birth),0,1)))
    if v==0:return a,0
    if v==1:return b,0
    if abs(getattr(node,'rigid_angle',0.))>1e-6:
        angle=np.degrees(node.rigid_angle)
        left=ndi.rotate(a,-angle*v,reshape=True,order=1,prefilter=False)
        right=ndi.rotate(b,angle*(1-v),reshape=True,order=1,prefilter=False)
        shape=np.maximum(left.shape,right.shape)+4
        aligned=[]
        for image in [left,right]:
            padding=shape-np.array(image.shape)
            padded=np.pad(image,[(int(d//2),int(d-d//2)) for d in padding])
            aligned.append(ndi.shift(padded,(padding%2)/2,order=1,prefilter=False))
        return connected_alpha((1-v)*aligned[0]+v*aligned[1])
    if not hasattr(node,'fields'):

        node.fields=[distance_field(np.pad(p,3)) for p in [a,b]]
    shape=np.maximum(2,np.rint((1-v)*np.array(a.shape)+v*np.array(b.shape)).astype(int))
    fields=[]
    for patch,sdf in zip([a,b],node.fields):
        y=np.linspace(3,patch.shape[0]+2,shape[0]);x=np.linspace(3,patch.shape[1]+2,shape[1])
        yy,xx=np.meshgrid(y,x,indexing='ij')
        fields.append(ndi.map_coordinates(sdf,[yy,xx],order=1,mode='constant',cval=-100))
    alpha=np.clip((1-v)*fields[0]+v*fields[1]+.5,0,1)
    alpha,repair=connected_alpha(alpha)
    return alpha,repair


def connected_alpha(alpha):
    """Join raster-only cracks inside one planned object; never join identities."""
    alpha=alpha.copy();repair=0
    for _ in range(64):
        labels,n=ndi.label(alpha>.5)
        if n==1:return alpha,repair
        if n==0:raise ValueError('Object vanished during rasterization')
        sizes=np.bincount(labels.ravel());sizes[0]=0;main=labels==sizes.argmax()
        distance,nearest=ndi.distance_transform_edt(~main,return_indices=True)
        q=np.unravel_index(np.where((labels>0)&~main,distance,np.inf).argmin(),alpha.shape)
        p=tuple(nearest[:,q[0],q[1]])
        line=np.rint(np.linspace(p,q,int(np.ceil(np.linalg.norm(np.array(q)-p)))+1)).astype(int)
        previous=line[0]
        for point in line:
            alpha[point[0],point[1]]=1;alpha[previous[0],point[1]]=1
            previous=point;repair+=1
    raise ValueError('Excessive disconnected raster fragments')


def stamp(alpha,c,clearance=1):
    corner=c-(np.array(alpha.shape[::-1])-1)/2
    origin=np.floor(corner).astype(int)-2;fraction=corner-np.floor(corner)
    image=ndi.shift(np.pad(alpha,2),[fraction[1],fraction[0]],order=1,prefilter=False)
    image,repair=connected_alpha(image)
    mask=image>1/255
    if clearance:mask=ndi.binary_dilation(mask,iterations=clearance)
    return dict(origin=origin,alpha=image,mask=mask,repair=repair)


def intersects(a,b,shift=(0,0)):
    p=a['origin']+shift;q=b['origin']
    start=np.maximum(p,q);end=np.minimum(p+np.array(a['mask'].shape[::-1]),q+np.array(b['mask'].shape[::-1]))
    if np.any(end<=start):return False
    aa=a['mask'][start[1]-p[1]:end[1]-p[1],start[0]-p[0]:end[0]-p[0]]
    bb=b['mask'][start[1]-q[1]:end[1]-q[1],start[0]-q[0]:end[0]-q[0]]
    return bool(np.any(aa&bb))


def frame(plan,t,state,size=(1280,720),offset=np.array([-800.,-450.])):
    """Offline collision projection with persistent offsets and checked topology."""
    nodes=active_nodes(plan,t);factor=plan['scale'];patches=[];centers=[];desired=[];repairs=0
    old_t=state.get('time',0);old_offsets=state.setdefault('offsets',{})
    decay=.90*max(0,1-clock(t))/max(1e-12,1-clock(old_t))
    for node in nodes:
        alpha,repair=plan.get('surface',patch_at)(node,t);repairs+=repair;patches.append(alpha)
        want=desired_center(node,t,factor)*factor+offset
        if 'tracks' in plan:want=want+plan['tracks'][node.id][round(t*(len(plan['tracks'][node.id])-1))]
        desired.append(want)
        previous=old_offsets.get(node.id,old_offsets.get(node.parent.id if node.parent else -1,np.zeros(2)))
        centers.append(want+previous*decay)
    centers=np.array(centers);desired=np.array(desired)
    clearance=0 if t in (0,1) else 1
    stamps=[stamp(a,c,clearance) for a,c in zip(patches,centers)]
    routes=state.setdefault('routes',{})
    for iteration in range(120):
        collisions=0
        for i in range(len(nodes)):
            for j in range(i):
                if not intersects(stamps[i],stamps[j]):continue
                collisions+=1;key=(nodes[i].id,nodes[j].id)
                root_i=nodes[i];root_j=nodes[j]
                while root_i.parent is not None:root_i=root_i.parent
                while root_j.parent is not None:root_j=root_j.parent
                lane_order=getattr(root_i,'lane',0.)-getattr(root_j,'lane',0.)
                choices=[]
                for direction in [(0,1),(0,-1),(1,0),(-1,0)]:
                    if lane_order and direction[1]*lane_order<0:continue
                    for distance in range(1,241):
                        shift=np.array(direction)*distance
                        if not intersects(stamps[i],stamps[j],shift):
                            penalty=1 if key not in routes or routes[key]==direction else 1.5
                            choices.append((distance*penalty,distance,direction));break
                if not choices:raise ValueError('No bounded separating displacement')
                _,distance,direction=min(choices);routes[key]=direction
                move=np.array(direction)*(distance+1)*.5
                centers[i]+=move;centers[j]-=move
                stamps[i]=stamp(patches[i],centers[i],clearance);stamps[j]=stamp(patches[j],centers[j],clearance)
        if not collisions:break
    else:raise ValueError('Collision projection did not converge')
    width,height=size;image=np.zeros((height,width));occupied=np.zeros((height,width),bool)
    for node,c,want,s in zip(nodes,centers,desired,stamps):
        old_offsets[node.id]=c-want;repairs+=s['repair']
        x,y=s['origin'];h,w=s['alpha'].shape
        if x<0 or y<0 or x+w>width or y+h>height:raise ValueError('Object left the output canvas')
        region=occupied[y:y+h,x:x+w]
        if np.any(region&(s['alpha']>1/255)):raise ValueError('Visible object overlap')
        region|=s['alpha']>1/255;image[y:y+h,x:x+w]+=s['alpha']
    count=ndi.label(image>.5)[1]
    if count!=len(nodes):raise ValueError(f'Visible count {count} differs from lineage count {len(nodes)}')
    state['time']=t
    return image,dict(ids=[n.id for n in nodes],count=count,repairs=repairs,max_offset=float(np.linalg.norm(centers-desired,axis=1).max()),centers=centers.tolist())


def motion_quality(metrics):
    previous={};velocity={};max_step=0.;max_acceleration=0.
    for row in metrics:
        current={i:np.array(c) for i,c in zip(row['ids'],row['centers'])};next_velocity={}
        for i,c in current.items():
            if i not in previous:continue
            v=c-previous[i];max_step=max(max_step,float(np.linalg.norm(v)))
            if i in velocity:max_acceleration=max(max_acceleration,float(np.linalg.norm(v-velocity[i])))
            next_velocity[i]=v
        previous=current;velocity=next_velocity
    return dict(max_step=max_step,max_acceleration=max_acceleration)


def smooth_tracks(plan,metrics,sigma=8):
    count=len(metrics);times=np.linspace(0,1,count);tracks={}
    recorded=[{i:np.array(c) for i,c in zip(r['ids'],r['centers'])} for r in metrics]
    fade=plan.get('track_fade',.08)
    envelope=np.array([clock(min(t/fade,1))*clock(min((1-t)/fade,1)) for t in times])
    for node in plan['nodes']:
        offsets=[];last=np.zeros(2)
        for k,t in enumerate(times):
            base=desired_center(node,t,plan['scale'])*plan['scale']+np.array([-800.,-450.])
            if node.id in recorded[k]:last=recorded[k][node.id]-base
            elif t<=node.birth and node.parent is not None:last=tracks[node.parent.id][k]
            offsets.append(last.copy())
        smooth=ndi.gaussian_filter1d(np.array(offsets),sigma,axis=0,mode='nearest')*envelope[:,None]
        if node.parent is not None:
            blend=np.array([clock(float(np.clip((t-node.birth)/.08,0,1))) for t in times])
            smooth=(1-blend[:,None])*tracks[node.parent.id]+blend[:,None]*smooth
        tracks[node.id]=smooth
    plan['tracks']=tracks


def presentation_alpha(alpha,t):
    """Stable visible topology through RGB/YUV quantization, including the hold.

    This display-only edge transfer preserves the half-coverage silhouette and
    fully transparent/opaque pixels. Its guard eases down rather than switching
    off on the last frame. Endpoint geometry is checked before this transfer.
    """
    margin=.05+.10*clock(min(t/.12,1))*clock(min((1-t)/.12,1))
    return np.where(alpha>.5,np.maximum(alpha,.5+margin),np.minimum(alpha,.5-margin))
