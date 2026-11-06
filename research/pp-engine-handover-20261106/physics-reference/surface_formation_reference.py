"""Declared opaque areal-fill surface closure; research oracle only.

Captured lineages remain the authoritative stock. This pure display/geometry
closure neither changes them nor advances any clock or transports surface mass.
"""
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class SurfaceFormation:
    pma: np.ndarray
    coverage: np.ndarray
    covered_area: np.ndarray
    mass: np.ndarray
    layer_mass: np.ndarray
    excess_mass: np.ndarray
    thickness_factor: np.ndarray
    authored_opacity: np.ndarray
    clamped_ratios: int

def reconstruct(moments, target_alpha, pixel_area, areal_mass_density,
                *, ratio_tolerance=8*2**-24):
    raw=np.asarray(moments,dtype=np.float64)
    alpha=np.asarray(target_alpha,dtype=np.float64)
    if raw.ndim!=2 or raw.shape[1]!=5 or alpha.shape!=(raw.shape[0],) or raw.shape[0]>65536:
        raise ValueError('Bounded Kx5 raw moments and K genuine support alphas required')
    if not np.all(np.isfinite(raw)) or np.any(raw<0) or not np.all(np.isfinite(alpha)) or np.any(alpha<=0) or np.any(alpha>1):
        raise ValueError('Finite nonnegative moments and genuine positive alpha required')
    if not all(np.isfinite(x) and x>0 for x in [pixel_area,areal_mass_density]) or not np.isfinite(ratio_tolerance) or not 0<=ratio_tolerance<=1e-5:
        raise ValueError('Positive declared physical area/density and bounded tolerance required')
    full_pixel_layer_mass=pixel_area*areal_mass_density
    if not np.isfinite(full_pixel_layer_mass) or full_pixel_layer_mass<=0:
        raise ValueError('Finite positive one-layer pixel mass required')
    mass=raw[:,3].copy()
    empty=mass==0
    if np.any(raw[empty]!=0):
        raise ValueError('Zero material cannot have colour/opacity moments')
    rgb=np.zeros_like(raw[:,:3]);opacity=np.zeros_like(mass)
    positive=~empty
    rgb[positive]=raw[positive,:3]/mass[positive,None]
    opacity[positive]=raw[positive,4]/mass[positive]
    if np.any(rgb>1+ratio_tolerance) or np.any(opacity>1+ratio_tolerance):
        raise ValueError('Material display coefficient exceeds its finite reduction tolerance')
    clamps=int(np.count_nonzero(rgb>1)+np.count_nonzero(opacity>1))
    rgb=np.minimum(rgb,1);opacity=np.minimum(opacity,1)
    cap=full_pixel_layer_mass*alpha
    layer=np.minimum(mass,cap)
    coverage=np.minimum(alpha,layer/full_pixel_layer_mass)
    excess=mass-layer
    thickness=np.zeros_like(mass)
    thickness[positive]=mass[positive]/layer[positive]
    display_alpha=coverage*opacity
    return SurfaceFormation(np.column_stack((rgb*display_alpha[:,None],display_alpha)),
        coverage,coverage*pixel_area,mass,layer,excess,thickness,opacity,clamps)
