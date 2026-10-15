"""Dev-only native PDF tile oracle. Never used by the independent renderer."""
import sys,json,base64,math
from pathlib import Path
import pymupdf as fitz
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import binary_dilation
from document_accuracy import spatial_accuracy,heatmap
corpus=Path(sys.argv[1]);out=Path(sys.argv[2]);docs={};displays={};worst={};sheets={}
def document(name):
 if name not in docs:docs[name]=fitz.open(corpus/name/'source.pdf')
 return docs[name]
def respond(job):
 name=job['name'];doc=document(name)
 if job['op']=='describe':return {'pages':[[p.rect.width,p.rect.height]for p in doc],'rasterizer':'PyMuPDF '+fitz.VersionBind}
 page=job['page'];zoom=job['zoom'];scale=96/72*zoom;x=job['x'];y=job['y'];w=job['width'];h=job['height'];halo=1;W=w+2;H=h+2
 A=np.frombuffer(base64.b64decode(job['rgba']),dtype=np.uint8).reshape(H,W,4)[:,:,:3].copy();R=np.full((H,W,3),255,np.uint8)
 if page<len(doc):
  key=(name,page)
  if key not in displays:displays[key]=doc[page].get_displaylist()
  pix=displays[key].get_pixmap(matrix=fitz.Matrix(scale,scale),clip=fitz.Rect((x-halo)/scale,(y-halo)/scale,(x+w+halo)/scale,(y+h+halo)/scale),alpha=False)
  if pix.width and pix.height:
   raw=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3);dx=pix.x-(x-halo);dy=pix.y-(y-halo);x0=max(0,dx);y0=max(0,dy);x1=min(W,dx+pix.width);y1=min(H,dy+pix.height)
   if x1>x0 and y1>y0:R[y0:y1,x0:x1]=raw[y0-dy:y1-dy,x0-dx:x1-dx]
 rm=R.mean(2)<178;am=A.mean(2)<178;nr=binary_dilation(rm,structure=np.ones((3,3),bool));na=binary_dilation(am,structure=np.ones((3,3),bool));r=rm[1:-1,1:-1];a=am[1:-1,1:-1];ref=int(r.sum());gpu=int(a.sum());missing=int((r&~na[1:-1,1:-1]).sum());extra=int((a&~nr[1:-1,1:-1]).sum());union=int((r|a).sum());intersection=int((r&a).sum());coverage=min(1-missing/max(1,ref),1-extra/max(1,gpu));spatial=spatial_accuracy(R,A)if missing or extra else None
 bad=spatial['concentratedErrorRegions']if spatial else[]
 result={'column':job['column'],'row':job['row'],'x':x,'y':y,'width':w,'height':h,'referenceInk':ref,'gpuInk':gpu,'missingBeyond1px':missing,'extraBeyond1px':extra,'inkUnion':union,'inkIntersection':intersection,'inkIoU':intersection/union if union else 1,'coverageWithin1px':coverage,'badComponents':len(bad),'worstRegions':bad[:4],'passed':coverage>=.995 and not bad and page<len(doc)}
 key=(name,page,zoom);folder=out/name/f'page-{page+1:02}'/f'zoom-{zoom}';folder.mkdir(parents=True,exist_ok=True)
 # Full-resolution evidence is retained for every failed or nonblank tile.
 if ref or gpu:
  stem=f"tile-{job['row']:03}-{job['column']:03}";result['evidence']=stem
  for kind,img in [('reference',R[1:-1,1:-1]),('gpu',A[1:-1,1:-1]),('error',heatmap(R,A)[1:-1,1:-1])]:Image.fromarray(img).save(folder/f'{stem}-{kind}.png')
 if key not in sheets:sheets[key]=Image.new('RGB',(job['columns']*100,job['rows']*110),'white')
 thumb=Image.fromarray(A[1:-1,1:-1]).resize((96,96));sheet=sheets[key];xx=job['column']*100;yy=job['row']*110;sheet.paste(thumb,(xx+2,yy+12));draw=ImageDraw.Draw(sheet);draw.rectangle((xx,yy,xx+99,yy+109),outline='#4c9c72'if result['passed']else'#c42e38',width=2);draw.text((xx+3,yy),f"{job['row']+1},{job['column']+1}",fill='black');sheet.save(folder/'grid.png')
 score=missing+extra
 if key not in worst or score>worst[key][0]:worst[key]=(score,result)
 return result
for line in sys.stdin:
 try:print(json.dumps({'ok':True,'result':respond(json.loads(line))},separators=(',',':')),flush=True)
 except Exception as exc:print(json.dumps({'ok':False,'error':str(exc)}),flush=True)
