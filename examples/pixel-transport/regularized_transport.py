"""Experimental temporally regularized contour atlas; endpoint geometry only."""
import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import PchipInterpolator
from continuous_transport import configure as base_configure, FieldPatch
from lineage_transport import distance_field
from weighted_transport import calibrate, rounded_connect
from pixel_transport import clock


def configure(plan, lane_scale=.5):
    base_configure(plan,lane_scale)
    original=plan['surface']
    def surface(node,t):
        if not node.children and node.parent is None and hasattr(node,'rigid_angle') and 0<t<1:
            return RigidPatch(node,clock(t)),0
        patch,repair=original(node,t)
        if isinstance(patch,FieldPatch):return RegularizedPatch(node,patch.v),repair
        return patch,repair
    plan['surface']=surface


def area_target(node,v):
    """Bounded monotone mass schedule; power one retains the previous candidate."""
    a=float(node.part.patch.sum());b=float(node.final.patch.sum())
    power=getattr(node,'area_power',1.)
    progress=v**power if b>=a else 1-(1-v)**power
    return a+(b-a)*progress


class RegularizedPatch:
    """Smooth changes of repair geometry before sampling a sharp contour.

    Atlas samples are fields, not cross-faded rendered images. Endpoint coverage
    and inferred rigid transforms retain the preceding candidate's exact bypass.
    A final connectivity repair remains explicit; this is not a topology proof.
    """
    def __init__(self,node,v):self.node=node;self.v=v
    def stamp(self,c,clearance):
        node=self.node;v=self.v;a=node.part.patch;b=node.final.patch
        fields,grid,pad=node.continuous_fields
        if not hasattr(node,'contour_atlas'):
            atlas=[]
            # Restrict rounding to a small fraction of the endpoint stroke width.
            thickness=[]
            for patch in [a,b]:
                inside=ndi.distance_transform_edt(patch>.5)
                thickness.append(float((inside*patch).sum()/max(patch.sum(),1)))
            radius=float(np.clip(min(thickness)*.55,1.2,2.2))
            for w in np.linspace(0,1,129):
                extent=(1-w)*np.array(a.shape)+w*np.array(b.shape)
                sampled=[]
                for patch,field in zip([a,b],fields):
                    ratio=(np.array(patch.shape)-1)/np.maximum(extent-1,1)
                    coords=grid*ratio[:,None,None]+((np.array(patch.shape)-1)/2+pad)[:,None,None]
                    sampled.append(ndi.map_coordinates(field,coords,order=1,mode='constant',cval=-100))
                envelope=clock(min(w/.12,1))*clock(min((1-w)/.12,1))
                field=ndi.gaussian_filter((1-w)*sampled[0]+w*sampled[1],1.2*envelope)
                alpha=calibrate(field,area_target(node,w))
                repaired,_=rounded_connect(alpha,radius)
                # Preserve the subpixel field where no connection was added.
                correction=np.maximum(0,distance_field(repaired)-distance_field(alpha))
                atlas.append(field+correction)
            node.contour_atlas=ndi.gaussian_filter1d(np.array(atlas,dtype=np.float32),2.,axis=0,mode='nearest')
            node.contour_radius=radius
        index=v*128;lo=min(int(index),127);blend=index-lo
        atlas=node.contour_atlas
        left=atlas[lo];right=atlas[lo+1]
        dl=(right-atlas[max(0,lo-1)])/2
        dr=(atlas[min(128,lo+2)]-left)/2
        z=blend
        field=(2*z**3-3*z*z+1)*left+(z**3-2*z*z+z)*dl+(-2*z**3+3*z*z)*right+(z**3-z*z)*dr
        shape=np.array(field.shape)+4;origin=np.floor(c-(shape[::-1]-1)/2).astype(int)
        y,x=np.mgrid[:shape[0],:shape[1]]
        relative=np.array([y+origin[1]-c[1],x+origin[0]-c[0]])
        coords=relative+((np.array(field.shape)-1)/2)[:,None,None]
        field=ndi.map_coordinates(field,coords,order=1,mode='constant',cval=-100)
        alpha=calibrate(field,area_target(node,v))
        for patch,weight in [(a,1-clock(min(v/.04,1))),(b,1-clock(min((1-v)/.04,1)))]:
            if weight:
                coords=relative+((np.array(patch.shape)-1)/2+2)[:,None,None]
                endpoint=ndi.map_coordinates(np.pad(patch,2),coords,order=1,mode='constant',cval=0)
                alpha=(1-weight)*alpha+weight*endpoint
        alpha,repair=rounded_connect(alpha,node.contour_radius)
        mask=alpha>1/255
        if clearance:mask=ndi.binary_dilation(mask,iterations=clearance)
        return dict(origin=origin,alpha=alpha,mask=mask,repair=repair)


def activity_clock(images, strength=.65):
    """Monotone retiming from coverage redistribution, not centroid speed.

    Spatially blurred differences reduce sensitivity to single raster edges.
    This measures visual activity, not a recovered physical material velocity.
    A positive base rate avoids pauses; endpoint easing is retained separately.
    """
    activity=[];previous=None
    for image in images:
        low=ndi.gaussian_filter(image.astype(np.float32)/255,2.)[::3,::3]
        if previous is not None:activity.append(float(np.abs(low-previous).sum()))
        previous=low
    speed=ndi.gaussian_filter1d(np.array(activity),5.,mode='nearest')
    speed=speed/max(speed.mean(),1e-9)
    density=(1-strength)+strength*speed
    cumulative=np.r_[0,np.cumsum(density)];cumulative/=cumulative[-1]
    # Inverse visual arc length; strictly increasing even in static intervals.
    inverse=PchipInterpolator(cumulative,np.linspace(0,1,len(images)))
    t=np.linspace(0,1,len(images));u=inverse(t)
    # Preserve existing start/end ramps and exact endpoint timing.
    envelope=np.array([clock(min(x/.15,1))*clock(min((1-x)/.15,1)) for x in t])
    result=t+envelope*(u-t)
    if np.any(np.diff(result)<=0):raise ValueError('Retiming reversed time')
    return result


class RigidPatch:
    """Single output-grid rotation/translation, avoiding resized-canvas parity."""
    def __init__(self,node,v):self.node=node;self.v=v
    def stamp(self,c,clearance):
        a=self.node.part.patch;b=self.node.final.patch;v=self.v
        angle=self.node.rigid_angle
        radius=max(np.linalg.norm(a.shape),np.linalg.norm(b.shape))/2+4
        shape=np.full(2,int(np.ceil(2*radius))+1)
        origin=np.floor(c-(shape[::-1]-1)/2).astype(int)
        y,x=np.mgrid[:shape[0],:shape[1]];grid=np.array([y+origin[1]-c[1],x+origin[0]-c[0]])
        alpha=np.zeros(tuple(shape))
        for patch,theta,weight in [(a,-angle*v,1-v),(b,angle*(1-v),v)]:
            co=np.cos(theta);si=np.sin(theta)
            coords=np.array([co*grid[0]+si*grid[1],-si*grid[0]+co*grid[1]])
            coords+=((np.array(patch.shape)-1)/2+2)[:,None,None]
            alpha+=weight*ndi.map_coordinates(np.pad(patch,2),coords,order=1,mode='constant',cval=0)
        alpha,repair=rounded_connect(alpha,.8)
        mask=alpha>1/255
        if clearance:mask=ndi.binary_dilation(mask,iterations=clearance)
        return dict(origin=origin,alpha=alpha,mask=mask,repair=repair)
