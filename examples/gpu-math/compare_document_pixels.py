"""Compare every PDF reference page against independent WebGPU framebuffer pixels."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt,binary_erosion

def compare(corpus,browser):
 report=json.loads((browser/'document-browser.json').read_text());results=[]
 for result in report['results']:
  name=result['name'];sizes=json.loads((browser/name/'pixel-sizes.json').read_text())if(browser/name/'pixel-sizes.json').exists()else[]
  for i,size in enumerate(sizes):
   raw=browser/name/f'native-{i+1:02}.rgba';Image.frombytes('RGBA',(size['width'],size['height']),raw.read_bytes()).convert('RGB').save(browser/name/f'native-{i+1:02}.png')
  references=sorted((corpus/name).glob('reference-*.png'),key=lambda p:int(p.stem.split('-')[-1]));actual=sorted((browser/name).glob('native-*.png'));pages=[]
  for i in range(max(len(references),len(actual))):
   if i>=len(references)or i>=len(actual):pages.append({'page':i+1,'missing':'reference'if i>=len(references)else'actual','passed':False});continue
   r=np.array(Image.open(references[i]).convert('RGB'));a=np.array(Image.open(actual[i]).convert('RGB'));same=r.shape==a.shape
   h,w=max(r.shape[0],a.shape[0]),max(r.shape[1],a.shape[1]);R=np.full((h,w,3),255,np.uint8);A=R.copy();R[:r.shape[0],:r.shape[1]]=r;A[:a.shape[0],:a.shape[1]]=a
   delta=abs(R.astype(float)-A.astype(float))/255;rm=R.mean(2)<178;am=A.mean(2)<178;union=rm|am;intersection=rm&am;iou=float(intersection.sum()/max(1,union.sum()));boundary_r=rm&~binary_erosion(rm);boundary_a=am&~binary_erosion(am)
   distances=np.r_[distance_transform_edt(~boundary_r)[boundary_a],distance_transform_edt(~boundary_a)[boundary_r]];max_edge=float(distances.max())if len(distances)else 0
   difference=np.zeros_like(R);difference[rm&~am]=[230,45,60];difference[am&~rm]=[30,100,240];difference[rm&am]=[180,180,180];difference[~union]=255
   Image.fromarray(difference).save(browser/name/f'difference-{i+1:02}.png')
   pages.append({'page':i+1,'sameDimensions':same,'referenceSize':[r.shape[1],r.shape[0]],'actualSize':[a.shape[1],a.shape[0]],'exactlyEqual':bool(same and np.array_equal(R,A)),'meanAbsoluteRGBError':float(delta.mean()),'meanAbsoluteRGBErrorOnInkUnion':float(delta[union].mean())if union.any()else 0,'pixelsDifferingOver8Codes':int((delta.max(2)>8/255).sum()),'inkIoU':iou,'maxBoundaryDistancePixels':max_edge,'passed':bool(same and iou>=.99 and max_edge<=1)})
  entry={'name':name,'referencePages':len(references),'nativePages':len(actual),'allPagesPassed':len(references)==len(actual)and all(p['passed']for p in pages),'diagnostics':result['diagnostics'],'pages':pages};results.append(entry)
 output={'documents':results,'accepted':all(r['allPagesPassed']for r in results),'policy':'Same page count/dimensions, ink IoU >= .99, max boundary displacement <= 1 pixel at 96dpi. Exact RGB equality and unregistered differences are recorded separately. No alignment, crop or page exclusions.','scope':'A failed document remains failed; successful formula-position checks do not establish full-document compatibility.'};(browser/'pixel-comparison.json').write_text(json.dumps(output,indent=2)+'\n');print(json.dumps({'accepted':output['accepted'],'documents':[{'name':r['name'],'pages':[r['referencePages'],r['nativePages']],'passed':r['allPagesPassed'],'meanInkIoU':float(np.mean([p['inkIoU']for p in r['pages']if'inkIoU'in p]))}for r in results]},indent=2))
 if not output['accepted']:raise SystemExit(1)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('corpus',type=Path);p.add_argument('browser',type=Path);a=p.parse_args();compare(a.corpus,a.browser)
