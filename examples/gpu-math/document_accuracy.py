"""Spatial error estimates. White page background never inflates the ink score."""
import numpy as np
from scipy.ndimage import binary_dilation,label,find_objects,distance_transform_cdt

def spatial_accuracy(reference,actual):
 r=reference.mean(2)<178;a=actual.mean(2)<178
 # Chebyshev one pixel is the full 3x3 neighbouring pixel square. Keep the old
 # Euclidean boundary measurement separately; this is an explicit extra metric.
 near_r=binary_dilation(r,structure=np.ones((3,3),bool));near_a=binary_dilation(a,structure=np.ones((3,3),bool));missing=r&~near_a;extra=a&~near_r
 def components(mask,other_near,kind):
  ids,count=label(mask);regions=[];worst=1.;evaluated=0
  for index,box in enumerate(find_objects(ids),1):
   pixels=ids[box]==index;n=int(pixels.sum())
   if n<2:continue
   evaluated+=1;unmatched=int((pixels&~other_near[box]).sum());recall=1-unmatched/n;worst=min(worst,recall)
   if unmatched>=2:regions.append({'kind':kind,'bbox':[box[1].start,box[0].start,box[1].stop,box[0].stop],'inkPixels':n,'unmatchedBeyond1px':unmatched,'coveredWithin1px':recall})
  return evaluated,worst,regions
 nr,wr,rr=components(r,near_a,'reference component');na,wa,ra=components(a,near_r,'GPU component')
 # Every error region is retained; the UI lists the worst rather than discarding
 # low-area glyphs. Geometry checks independently detect even tiny missing glyphs.
 regions=sorted(rr+ra,key=lambda p:(-p['unmatchedBeyond1px'],p['coveredWithin1px']))
 return {'tolerance':'one pixel in x and y (Chebyshev), 96dpi; no registration','referenceInkPixels':int(r.sum()),'gpuInkPixels':int(a.sum()),'referenceInkBeyond1px':int(missing.sum()),'gpuInkBeyond1px':int(extra.sum()),'referenceCoverageWithin1px':1-int(missing.sum())/max(1,int(r.sum())),'gpuCoverageWithin1px':1-int(extra.sum())/max(1,int(a.sum())),'worstReferenceComponentCoverage':wr,'worstGpuComponentCoverage':wa,'referenceComponentsChecked':nr,'gpuComponentsChecked':na,'regions':regions,'edgeTolerantInkAccuracy':min(1-int(missing.sum())/max(1,int(r.sum())),1-int(extra.sum())/max(1,int(a.sum()))),'concentratedErrorRegions':[region for region in regions if region['coveredWithin1px']<.95],'localPixelsPassed':all(region['coveredWithin1px']>=.95 for region in regions)}

def heatmap(reference,actual):
 r=reference.mean(2)<178;a=actual.mean(2)<178;near_r=binary_dilation(r,structure=np.ones((3,3),bool));near_a=binary_dilation(a,structure=np.ones((3,3),bool));out=np.full_like(reference,255);out[r|a]=[220,220,220];out[(r^a)&(near_r&near_a)]=[240,170,50];out[r&~near_a]=[230,45,60];out[a&~near_r]=[30,100,240];return out
