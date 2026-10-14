"""Continuity-first local surfaces and shape-sized passing routes (CPU research)."""
import numpy as np
from scipy import ndimage as ndi
from lineage_transport import patch_at,distance_field
from weighted_transport import calibrate,rounded_connect
from pixel_transport import clock


def configure(plan,lane_scale=.35):
    plan['track_fade']=.16
    plan['continuous_tracks']=True
    plan['contact_grace']=True
    plan['clearance']=1
    plan['projection_slack']=.05
    for root in plan['roots']:root.lane*=lane_scale
    def surface(node,t):
        a=node.part.patch
        # The parent and its partition must meet at exactly the same surface.
        # Shape/mass growth starts smoothly after birth, never on the switch.
        if node.children:return a,0
        if node.parent is None and hasattr(node,'rigid_angle'):return patch_at(node,t)
        b=node.final.patch
        v=clock(float(np.clip((t-node.birth)/(1-node.birth),0,1)))
        if v==0:return a,0
        if v==1:return b,0
        if not hasattr(node,'continuous_fields'):
            pad=12
            shape=np.maximum(a.shape,b.shape)+2*pad
            y,x=np.mgrid[:shape[0],:shape[1]]
            grid=np.array([y-(shape[0]-1)/2,x-(shape[1]-1)/2])
            node.continuous_fields=([distance_field(np.pad(p,pad)) for p in [a,b]],grid,pad)
        return FieldPatch(node,v),0
    plan['surface']=surface


class FieldPatch:
    """Sample the moving contour once on the output grid, avoiding parity snaps."""
    def __init__(self,node,v):self.node=node;self.v=v
    def stamp(self,c,clearance):
        node=self.node;v=self.v;a=node.part.patch;b=node.final.patch
        fields,grid,pad=node.continuous_fields
        shape=np.array(grid.shape[1:])+4
        origin=np.floor(c-(shape[::-1]-1)/2).astype(int)
        y,x=np.mgrid[:shape[0],:shape[1]]
        grid=np.array([y+origin[1]-c[1],x+origin[0]-c[0]])
        extent=(1-v)*np.array(a.shape)+v*np.array(b.shape)
        sampled=[]
        for patch,field in zip([a,b],fields):
            ratio=(np.array(patch.shape)-1)/np.maximum(extent-1,1)
            coordinates=grid*ratio[:,None,None]+((np.array(patch.shape)-1)/2+pad)[:,None,None]
            sampled.append(ndi.map_coordinates(field,coordinates,order=1,mode='constant',cval=-100))
        field=(1-v)*sampled[0]+v*sampled[1]
        envelope=clock(min(v/.12,1))*clock(min((1-v)/.12,1))
        field=ndi.gaussian_filter(field,.55*envelope)
        desired=(1-v)*a.sum()+v*b.sum()
        alpha=calibrate(field,desired)
        # Match bilinear endpoint coverage continuously before entering the field
        # model, including fractional positions at a lineage birth.
        for patch,weight in [(a,1-clock(min(v/.04,1))),(b,1-clock(min((1-v)/.04,1)))]:
            if weight:
                coords=grid+((np.array(patch.shape)-1)/2+2)[:,None,None]
                endpoint=ndi.map_coordinates(np.pad(patch,2),coords,order=1,mode='constant',cval=0)
                alpha=(1-weight)*alpha+weight*endpoint
        alpha,repair=rounded_connect(alpha,.8)
        mask=alpha>1/255
        if clearance:mask=ndi.binary_dilation(mask,iterations=clearance)
        return dict(origin=origin,alpha=alpha,mask=mask,repair=repair)


def diagnostics(images):
    """Observe local thickening and changed coverage, not just total area."""
    areas=[];thickness=[];changes=[];previous=None;acceleration=[];previous_change=None
    for encoded in images:
        alpha=encoded/255
        areas.append(float(alpha.sum()))
        inside=ndi.distance_transform_edt(alpha>.5)
        thickness.append(float(np.sum(inside*alpha)/max(alpha.sum(),1)))
        if previous is not None:
            change=alpha-previous
            changes.append(float(np.abs(change).sum()/max(alpha.sum(),previous.sum(),1)))
            if previous_change is not None:acceleration.append(float(np.abs(change-previous_change).sum()/max(alpha.sum(),1)))
            previous_change=change
        previous=alpha
    baseline=np.linspace(thickness[0],thickness[-1],len(thickness))
    return dict(areas=areas,thickness=thickness,excess_thickness=float(np.mean(np.maximum(0,np.array(thickness)-baseline))),
        max_changed_coverage=max(changes,default=0),changed_coverage=changes,boundary_acceleration=acceleration)


def presentation_alpha(alpha):
    """Smooth monotone display contrast, with no jump at half coverage."""
    return alpha+.12*(np.tanh(300*(alpha-.5))-(2*alpha-1))
