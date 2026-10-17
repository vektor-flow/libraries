"""Dev-only identification of external archive marks; never used by the renderer."""
import math,re

_ARXIV=re.compile(r'arXiv:(?:\d{4}\.\d{4,5}|[a-z.-]+/\d{7})v\d+\s+\[[^\]\n]+\]\s+\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}')

def arxiv_stamp_regions(page):
 """Identify only complete rotated arXiv marks isolated in the left margin.

 Callers opt in explicitly. Ambiguous marks overlapping other content fail closed.
 Original PDF and reference raster files are never modified.
 """
 traces=page.get_texttrace();regions=[]
 for span in traces:
  text=''.join(chr(c[0])for c in span['chars'])
  if not _ARXIV.fullmatch(text):continue
  direction=span['dir'];bbox=list(span['bbox'])
  if abs(direction[0])>1e-6 or direction[1]>-.999999 or not(0<=bbox[0]<bbox[2]<=page.rect.width*.1):continue
  padded=[bbox[0]-1,bbox[1]-1,bbox[2]+1,bbox[3]+1]
  def overlaps(b):return min(padded[2],b[2])>max(padded[0],b[0])and min(padded[3],b[3])>max(padded[1],b[1])
  if any(other is not span and overlaps(other['bbox'])for other in traces):raise ValueError('arXiv stamp overlaps other reference text')
  if any(overlaps(b['bbox'])for b in page.get_image_info())or any(overlaps(d['rect'])for d in page.get_drawings()):raise ValueError('arXiv stamp overlaps reference graphics')
  regions.append({'kind':'external-arxiv-stamp','text':text,'font':span['font'].split('+')[-1].lower(),'bbox':bbox,'glyphs':len(span['chars']),'reason':'Archive-added stamp is outside LaTeX source; excluded by explicit user request.'})
 return regions

def is_overlay_glyph(glyph,regions):
 return any(glyph['identity'][0]==r['font']and r['bbox'][0]<=glyph['x']<=r['bbox'][2]and r['bbox'][1]<=glyph['y']<=r['bbox'][3]for r in regions)

def mask_reference_overlays(reference,regions,scale=96/72):
 """Blank only verified isolated reference marks; unexpected GPU ink still fails."""
 result=reference.copy();height,width=result.shape[:2]
 for region in regions:
  x0,y0,x1,y1=region['bbox'];left=max(0,math.floor((x0-1)*scale));top=max(0,math.floor((y0-1)*scale));right=min(width,math.ceil((x1+1)*scale));bottom=min(height,math.ceil((y1+1)*scale));result[top:bottom,left:right]=255
 return result
