"""Independent scalar-field sampling versus reconstructed contour endpoints."""
import argparse,json
from pathlib import Path
import contourpy
import numpy as np
from scipy import ndimage as ndi
from field_transport import Atlas,normalize,raster
p=argparse.ArgumentParser();p.add_argument('atlas',type=Path);p.add_argument('output',type=Path);a=p.parse_args();atlas=Atlas(a.atlas);results={}
for token in ['D','O','8','B','0']:
 f=atlas.field('display/'+token);points=np.concatenate(contourpy.contour_generator(z=f).lines(0));lo=points.min(0);hi=points.max(0);scale=280/(hi[1]-lo[1]);center=(lo+hi)/2
 y,x=np.mgrid[:512,:512];coords=np.array([(y+.5-256)/scale+center[1],(x+.5-256)/scale+center[0]])
 direct=ndi.map_coordinates(f,coords,order=1,mode='constant',cval=-atlas.data['range']/2)>0
 contour=raster(normalize(atlas.loops('display/'+token)))>127
 iou=float((direct&contour).sum()/(direct|contour).sum());assert iou>.99,(token,iou);results[token]=iou
 print(token,iou)
a.output.write_text(json.dumps(dict(method='Direct bilinear sampling of native scalar atlas at output pixel centers versus contour raster; not an exact analytic-font comparison',iou=results,provenance=atlas.provenance),indent=2)+'\n')
