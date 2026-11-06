"""Resolved native-pixel reaction along an accepted linear probe segment.
Research only: the air velocity still comes from its declared coarse fluid grid.
Optional finite-width affine moving front; no fine-grid air flow, nonlinear/
shape-changing receiver, thermal or glyph-formation claim.
"""
import numpy as np

def capture_segments(alpha,starts,ends,remaining,rate,dt,lengths,*,max_segments=4096,front=None):
    alpha=np.asarray(alpha,dtype=float);starts=np.asarray(starts,dtype=float);ends=np.asarray(ends,dtype=float);remaining=np.asarray(remaining,dtype=float);lengths=np.asarray(lengths,dtype=float)
    if alpha.ndim!=2 or 0 in alpha.shape or alpha.size>4194304 or not np.all(np.isfinite(alpha)) or np.any(alpha<0) or np.any(alpha>1):raise ValueError('Bounded native alpha mask required')
    if starts.ndim!=2 or starts.shape[1]!=3 or ends.shape!=starts.shape or remaining.shape!=(len(starts),) or len(starts)>131072:raise ValueError('Bounded three-dimensional probe segments required')
    if lengths.shape!=(3,) or np.any(lengths<=0) or not all(np.all(np.isfinite(a))for a in [starts,ends,remaining,lengths]) or np.any(remaining<0):raise ValueError('Finite physical probe data required')
    if not np.isfinite(rate) or rate<0 or not np.isfinite(dt) or dt<0 or not isinstance(max_segments,int) or max_segments<1 or max_segments>4096:raise ValueError('Finite bounded capture controls required')
    if front is not None:
        front=np.asarray(front,dtype=float)
        if front.shape!=(3,) or not np.all(np.isfinite(front)) or front[2]<=0:raise ValueError('Finite linear wave front and positive width required')
    height,width=alpha.shape;scale=np.array([width/lengths[0],height/lengths[1]])
    captured=np.zeros(len(starts),dtype=bool);positions=np.mod(ends,lengths);exposure=np.zeros(len(starts));pixels=np.full((len(starts),2),-1,dtype=int);fractions=np.full(len(starts),np.nan)
    if dt==0 or rate==0:return {'captured':captured,'positions':positions,'exposure':exposure,'pixels':pixels,'fractions':fractions}
    for i,(start,end,needed)in enumerate(zip(starts,ends,remaining)):
        p0=start[:2]*scale;delta=(end-start)[:2]*scale;events=[0.,1.]
        for axis in range(2):
            if delta[axis]==0:continue
            low,high=sorted([p0[axis],p0[axis]+delta[axis]])
            count=int(np.ceil(high)-np.floor(low)-1)
            if count>max_segments:raise RuntimeError('Fine receiver crossing budget exceeded')
            edges=np.arange(np.floor(low)+1,np.ceil(high));events.extend(((edges-p0[axis])/delta[axis]).tolist())
        events=np.unique(events)
        if len(events)-1>max_segments:raise RuntimeError('Fine receiver crossing budget exceeded')
        for a,b in zip(events[:-1],events[1:]):
            xy=np.floor(p0+delta*((a+b)/2)).astype(np.int64);x=int(xy[0]%width);y=int(height-1-xy[1]%height);hazard=rate*alpha[y,x]
            if front is not None:
                # Within this pixel interval the periodic image is fixed. The
                # probe and band edges are affine in physical time: clip exactly.
                relative=start[0]-(xy[0]//width)*lengths[0]-front[0]
                slope=end[0]-start[0]-(front[1]-front[0]);half=front[2]/2
                if slope==0:
                    if abs(relative)>half:continue
                else:
                    entry,exit=sorted([(-half-relative)/slope,(half-relative)/slope]);a=max(a,entry);b=min(b,exit)
                    if b<=a:continue
            amount=hazard*dt*(b-a)
            if hazard>0 and exposure[i]+amount>=needed:
                fraction=a+(needed-exposure[i])/(hazard*dt);positions[i]=np.mod(start+(end-start)*fraction,lengths);exposure[i]=needed;pixels[i]=[y,x];captured[i]=True;fractions[i]=fraction;break
            exposure[i]+=amount
    return {'captured':captured,'positions':positions,'exposure':exposure,'pixels':pixels,'fractions':fractions}
