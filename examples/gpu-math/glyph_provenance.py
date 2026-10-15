"""Read development DVI glyph placement; output contains font primitives, no pages."""
import subprocess,os
from pathlib import Path
from fontTools.tfmLib import TFM
class DVI:
 _font_cache={}
 def __init__(self,path,extras=None):
  self.raw=path.read_bytes();self.at=0;self.fonts={};self.metrics={};self.items=[];self.origin=None;self.env=os.environ.copy()
  if extras:self.env['TFMFONTS']=str(extras.resolve())+'//:'
 def number(self,n,signed=False):
  v=int.from_bytes(self.raw[self.at:self.at+n],byteorder='big',signed=signed);self.at+=n;return v
 def read(self):
  h=v=w=x=y=z=0;stack=[];selected=None;factor=72/(65536*72.27)
  while self.at<len(self.raw):
   op=self.number(1)
   if op<=131 or 133<=op<=136:
    code=op if op<=127 else self.number(op-127 if op<=131 else op-132);f=self.fonts[selected];name=f['name'];tfm=self.metrics[name];self.items.append({'fontName':name,'fontCode':code,'fontSize':f['scale']*factor,'x':h*factor,'y':v*factor,'advance':round(tfm.chars[code]['width']*f['scale'])*factor})
    if op<=131:h+=round(tfm.chars[code]['width']*f['scale'])
   elif op in [132,137]:
    height=self.number(4,True);width=self.number(4,True)
    if op==132:h+=width
   elif op==138:pass
   elif op==139:
    self.at+=44;h=v=w=x=y=z=0;stack=[]
   elif op==140:pass
   elif op==141:stack.append((h,v,w,x,y,z))
   elif op==142:h,v,w,x,y,z=stack.pop()
   elif 143<=op<=146:h+=self.number(op-142,True)
   elif op==147:h+=w
   elif 148<=op<=151:w=self.number(op-147,True);h+=w
   elif op==152:h+=x
   elif 153<=op<=156:x=self.number(op-152,True);h+=x
   elif 157<=op<=160:v+=self.number(op-156,True)
   elif op==161:v+=y
   elif 162<=op<=165:y=self.number(op-161,True);v+=y
   elif op==166:v+=z
   elif 167<=op<=170:z=self.number(op-166,True);v+=z
   elif 171<=op<=234:selected=op-171
   elif 235<=op<=238:selected=self.number(op-234)
   elif 239<=op<=242:
    count=self.number(op-238);special=self.raw[self.at:self.at+count];self.at+=count
    if b'box-origin'in special:self.origin=(h*factor,v*factor)
   elif 243<=op<=246:
    k=self.number(op-242);checksum=self.number(4);scale=self.number(4);design=self.number(4);a=self.number(1);l=self.number(1);name=self.raw[self.at:self.at+a+l].decode();self.at+=a+l;self.fonts[k]={'name':name,'scale':scale}
    if name not in self.metrics:
     key=(name,self.env.get('TFMFONTS'));cached=DVI._font_cache.get(key)
     if cached is None:cached=TFM(subprocess.check_output(['kpsewhich',name+'.tfm'],text=True,env=self.env).strip());DVI._font_cache[key]=cached
     self.metrics[name]=cached
   elif op==247:
    version=self.number(1);numerator=self.number(4);denominator=self.number(4);mag=self.number(4);factor=numerator/denominator*mag/1000*72/254000;length=self.number(1);self.at+=length
   elif op in [248,249]:break
   else:raise ValueError('Unsupported DVI opcode '+str(op))
  if self.origin is None:raise ValueError('Missing glyph mapping origin')
  ox,oy=self.origin
  return[{**p,'x':p['x']-ox,'y':p['y']-oy}for p in self.items]
