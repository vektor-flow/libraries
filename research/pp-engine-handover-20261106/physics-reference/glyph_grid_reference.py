"""Conservative native-alpha→MAC cell averages; research, not glyph capture physics."""
import numpy as np

def cell_average(alpha,shape):
    value=np.asarray(alpha,dtype=float)
    if value.ndim!=2 or not np.all(np.isfinite(value)) or np.any(value<0) or np.any(value>1):raise ValueError('Finite native alpha occupancy0..1 required')
    nx,ny=shape
    if any(not isinstance(n,int) or n<1 or n>4096 for n in shape):raise ValueError('Bounded positive cell counts required')
    height,width=value.shape
    def weights(pixels,cells):
        pixel=np.arange(pixels);edge=np.arange(cells+1)*pixels/cells
        return np.maximum(0,np.minimum(edge[1:,None],pixel[None,:]+1)-np.maximum(edge[:-1,None],pixel[None,:]))
    # Alpha is a finite native raster footprint, piecewise constant within each pixel.
    integral=weights(height,ny)@value@weights(width,nx).T
    return (integral/((width/nx)*(height/ny))).T[:,::-1]

def extrude(alpha,shape,lengths):
    nx,ny,nz=shape
    if not isinstance(nz,int) or nz<1 or nz>4096 or len(lengths)!=3 or any(not np.isfinite(v) or v<=0 for v in lengths):raise ValueError('Bounded physical grid required')
    return np.repeat(cell_average(alpha,(nx,ny))[:,:,None],nz,axis=2)

def frozen_reaction(alpha,shape,lengths,flow_rate,duration):
    if not np.isfinite(flow_rate) or flow_rate<=0 or not np.isfinite(duration) or duration<0:raise ValueError('Finite positive collector rate and nonnegative duration required')
    fine=np.asarray(alpha,dtype=float);coarse=extrude(fine,shape,lengths);volume=np.prod(lengths)
    integral=float(fine.mean()*volume)
    if integral<=0:raise ValueError('Empty native receiver')
    fine_rate=flow_rate*fine/integral;coarse_rate=flow_rate*coarse/integral
    # Isolate the reaction operator: uniform concentration, no transport/mixing.
    # These exact exponentials test homogenization, not the full Navier-Stokes run.
    return {'fineCaptured':float(np.mean(-np.expm1(-fine_rate*duration))*volume),'coarseCaptured':float(np.mean(-np.expm1(-coarse_rate*duration))*volume),'fineMaximumRate':float(fine_rate.max()),'coarseMaximumRate':float(coarse_rate.max()),'fineMaterialRemaining':float(np.mean(np.exp(-fine_rate*duration))*volume)}
