"""Forward contact and shared-body reformation, inferred from endpoint pixels."""
from types import SimpleNamespace
import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import CubicSpline
from lineage_transport import make_plan as lineage_plan, Node, center, distance_field
from regularized_transport import RigidPatch
from weighted_transport import calibrate
from pixel_transport import clock


def make_plan(start,end,scale=3,lane_scale=.5,neck_width=.8,phase_guard=False):
    old=lineage_plan(start,end,scale)
    if old['source_count']==old['target_count']:
        old=lineage_plan(end,start,scale)
    elif not old['reverse']:
        raise ValueError('Render the decreasing-count direction and reverse for splits')
    roots=[]
    def leaves(node):return sum([leaves(c) for c in node.children],[]) if node.children else [node]
    for original in old['roots']:
        parts=[n.final for n in leaves(original)]
        lo=np.min([p.origin for p in parts],axis=0);hi=np.max([p.origin+np.array(p.patch.shape[::-1]) for p in parts],axis=0)
        alpha=np.zeros(tuple((hi-lo)[::-1]))
        for part in parts:
            x,y=part.origin-lo;h,w=part.patch.shape;alpha[y:y+h,x:x+w]+=part.patch
        part=SimpleNamespace(patch=alpha,origin=lo)
        node=Node(len(roots),part,[],goal=center(original.part,scale),final=original.part)
        node.lane=original.lane*lane_scale
        if len(parts)==1 and hasattr(original,'rigid_angle'):node.rigid_angle=-original.rigid_angle
        node.initial_parts=parts
        node.initial_offsets=[center(p,scale)*scale-center(part,scale)*scale for p in parts]
        node.canvas=np.maximum(alpha.shape,node.final.patch.shape)+28
        node.field_pad=int(max(node.canvas))+8
        node.source_fields=[distance_field(np.pad(p.patch,node.field_pad)) for p in parts]
        node.target_field=distance_field(np.pad(node.final.patch,node.field_pad))
        node.neck_width=neck_width
        node.phase_guard=phase_guard
        node.collapse_time=.58
        node.contact_time=0.
        if len(parts)>1:
            # No symbol is pre-shaped into a target partition. They translate
            # into contact, then one shared field reforms toward the target.
            node.contact_time=node.collapse_time
            for t in np.linspace(0,node.collapse_time,97):
                f=CoalescingPatch(node,float(t)).field_on_grid(canonical=True,morph=False)
                if ndi.label(f>0)[1]==1:
                    node.contact_time=float(t);break
        joined=CoalescingPatch(node,node.contact_time).field_on_grid(morph=False)>0
        y,x=np.nonzero(joined)
        node.join_extent=np.array([y.max()-y.min()+1,x.max()-x.min()+1])
        node.join_center=np.array([(y.max()+y.min())/2,(x.max()+x.min())/2])-(node.canvas-1)/2
        roots.append(node)
    def surface(node,t):
        if t==0:return ExactPatch(node.part.patch),0
        if t==1:return node.final.patch,0
        if hasattr(node,'rigid_angle'):return RigidPatch(node,clock(t)),0
        return CoalescingPatch(node,t),0
    return dict(roots=roots,nodes=roots,scale=scale,reverse=False,source_count=old['source_count'],target_count=old['target_count'],
        surface=surface,coalescing=True,continuous_tracks=True,track_fade=.12,clearance=1,projection_slack=.05,events=[])


class CoalescingPatch:
    def __init__(self,node,t):self.node=node;self.t=t
    def field_on_grid(self,canonical=False,morph=True,relative=None,regularize=True):
        n=self.node;t=self.t
        if relative is None:
            y,x=np.mgrid[:n.canvas[0],:n.canvas[1]]
            relative=np.array([y-(n.canvas[0]-1)/2,x-(n.canvas[1]-1)/2])
        effective=t
        if morph and t>n.contact_time:
            u=min((t-n.contact_time)/.08,1)
            effective=n.contact_time+.08*(u-u**3+.5*u**4)
        contraction=1-clock(min(effective/n.collapse_time,1)) if len(n.initial_parts)>1 else 1.
        finish=min(.9,n.contact_time+.28)
        v=clock(float(np.clip((t-n.contact_time)/(finish-n.contact_time),0,1))) if morph else 0.
        source_relative=relative
        if v>0:
            ratio=(1-v)+v*np.array(n.final.patch.shape)/n.join_extent
            source_relative=relative/ratio[:,None,None]+v*n.join_center[:,None,None]
        values=[]
        for part,offset,field in zip(n.initial_parts,n.initial_offsets,n.source_fields):
            coords=source_relative-(offset*contraction)[::-1,None,None]+((np.array(part.patch.shape)-1)/2+n.field_pad)[:,None,None]
            values.append(ndi.map_coordinates(field,coords,order=1,mode='constant',cval=-1000))
        union=np.maximum.reduce(values)
        if not morph or t<=n.contact_time:return union
        finish=min(.9,n.contact_time+.28)
        v=clock(float(np.clip((t-n.contact_time)/(finish-n.contact_time),0,1)))
        coords=relative+((np.array(n.final.patch.shape)-1)/2+n.field_pad)[:,None,None]
        target=ndi.map_coordinates(n.target_field,coords,order=1,mode='constant',cval=-1000)
        if t>=finish:return target
        envelope=clock(min(v/.1,1))*clock(min((1-v)/.1,1))
        field=ndi.gaussian_filter((1-v)*union+v*target,.8*envelope)
        area=np.clip(field+.5,0,1).sum();lower=min(n.part.patch.sum(),n.final.patch.sum());upper=max(n.part.patch.sum(),n.final.patch.sum())
        if area<lower or area>upper:
            alpha=calibrate(field,float(np.clip(area,lower,upper)))
            field=field+float((alpha-field-.5)[(alpha>0)&(alpha<1)].mean()) if np.any((alpha>0)&(alpha<1)) else field
        if regularize:
            if not hasattr(n,'neck_curve'):
                times=np.linspace(n.contact_time,finish,161);amounts=[]
                for time in times:
                    raw=CoalescingPatch(n,float(time)).field_on_grid(regularize=False)
                    env=clock(min((time-n.contact_time)/.08,1))*clock(min((finish-time)/.08,1))
                    neck=n.neck_width*env
                    def feasible(shift):
                        levels=[0,neck] if not n.phase_guard else [-neck,0,neck/2,neck]
                        return ndi.label(raw+shift>0)[1]==1 and all(ndi.label(raw+shift>level)[1]<=1 for level in levels)
                    shift=0.
                    if not feasible(0):
                        for shift in np.arange(.25,12.01,.25):
                            if feasible(shift):break
                        else:raise ValueError('Shared surface needs excessive thickening')
                        lo=shift-.25;hi=shift
                        for _ in range(8):
                            mid=(lo+hi)/2
                            if feasible(mid):hi=mid
                            else:lo=mid
                        shift=hi
                    amounts.append(shift/max(env,1e-8))
                amounts=ndi.gaussian_filter1d(ndi.maximum_filter1d(amounts,9,mode='nearest'),1.,mode='nearest')
                envelopes=np.array([clock(min((x-n.contact_time)/.08,1))*clock(min((finish-x)/.08,1)) for x in times])
                n.neck_curve=CubicSpline(times,amounts*envelopes,bc_type=((1,0.),(1,0.)))
                n.maximum_neck_offset=float(max(amounts*envelopes))
            field=field+max(0.,float(n.neck_curve(t)))
        return field
    def stamp(self,c,clearance):
        n=self.node;shape=n.canvas+4;origin=np.floor(c-(shape[::-1]-1)/2).astype(int)
        y,x=np.mgrid[:shape[0],:shape[1]];relative=np.array([y+origin[1]-c[1],x+origin[0]-c[0]])
        alpha=np.clip(self.field_on_grid(relative=relative)+.5,0,1)
        yy,xx=np.nonzero(alpha)
        if not len(xx):raise ValueError('Shared body vanished')
        lo=np.array([xx.min(),yy.min()]);hi=np.array([xx.max()+1,yy.max()+1])
        alpha=np.pad(alpha[lo[1]:hi[1],lo[0]:hi[0]],2);origin=origin+lo-2
        mask=alpha>1/255
        if clearance:mask=ndi.binary_dilation(mask,iterations=clearance)
        return dict(origin=origin,alpha=alpha,mask=mask,repair=0)



class ExactPatch:
    def __init__(self,alpha):self.alpha=alpha
    def stamp(self,c,clearance):
        corner=c-(np.array(self.alpha.shape[::-1])-1)/2
        origin=np.floor(corner).astype(int)-2;fraction=corner-np.floor(corner)
        alpha=ndi.shift(np.pad(self.alpha,2),fraction[::-1],order=1,prefilter=False)
        mask=alpha>1/255
        if clearance:mask=ndi.binary_dilation(mask,iterations=clearance)
        return dict(origin=origin,alpha=alpha,mask=mask,repair=0)
