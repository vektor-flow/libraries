"""Test-only mouth model, independent line iterator; never a production parser.
No native execution. Category lookup happens inside next(), never line loading.
"""
from dataclasses import dataclass, replace
import copy

class Diagnostic(Exception):
 def __init__(self,code,start,stop):
  self.code,self.start,self.stop=code,start,stop
  super().__init__(f'{code} at [{start},{stop})')

def categories():
 c=[12]*128
 for i in range(65,91):c[i]=11
 for i in range(97,123):c[i]=11
 for i,v in {0:9,9:10,13:5,32:10,92:0,123:1,125:2,36:3,38:4,35:6,94:7,95:8,126:13,37:14,127:15}.items():c[i]=v
 return c

@dataclass(frozen=True)
class Token:
 kind:int; category:int; value:str; source:int; occurrence:int; start:int; stop:int; origin:int; provenance:int

class Mouth:
 def __init__(self,raw,source=0,occurrence=0,revision='sha256:fixture',origins=None):
  self.raw=raw; self.source=source; self.occurrence=occurrence; self.revision=revision
  self.cats=categories();self.generation=0;self.state=0;self.offset=0;self.units=[];self.index=0
  self.origins=copy.deepcopy(origins or [])
 def assign(self,code,cat):
  if code not in range(128) or code in (10,13):raise ValueError('TEX_MOUTH_UNSUPPORTED_CATEGORY_TARGET')
  if cat not in range(16) or cat==5:raise ValueError('TEX_MOUTH_UNSUPPORTED_CATEGORY_VALUE')
  self.cats[code]=cat;self.generation+=1
 def _line(self):
  if self.index<len(self.units):return True
  if self.offset>=len(self.raw):return False
  start=self.offset; end=start
  while end<len(self.raw) and self.raw[end] not in (10,13):end+=1
  after=end
  if after<len(self.raw):
   after+=1
   if self.raw[end]==13 and after<len(self.raw) and self.raw[after]==10:after+=1
  tail=end
  while tail>start and self.raw[tail-1]==32:tail-=1
  # UTF-8 decoding is structural only; no category assigned while loading.
  body=self.raw[start:tail].decode('utf8'); units=[];at=start
  for char in body:
   stop=at+len(char.encode());units.append((char,at,stop,False));at=stop
  units.append(('\r',tail,after,True))
  self.offset=after;self.units=units;self.index=0;self.state=0
  return True
 def _peek(self):
  c,a,b,line=self.units[self.index]
  if ord(c)>=128:raise Diagnostic(1,a,b)
  if self.cats[ord(c)]==7 and self.index+1<len(self.units) and self.units[self.index+1][0]==c:
   raise Diagnostic(2,a,b)
  return c,a,b,line
 def _emit(self,kind,cat,val,a,b,prov):
  origin=-1
  if b>a:
   origin=len(self.origins)
   self.origins.append(dict(source=self.source,occurrence=self.occurrence,start=a,stop=b,role='literal',definition=-1,invocation=-1))
  return Token(kind,cat,val,self.source,self.occurrence,a,b,origin,prov)
 def next(self):
  saved=copy.deepcopy(self.__dict__)
  try:return self._next()
  except Diagnostic:
   self.__dict__=saved
   raise
 def _next(self):
  while self._line():
   c,a,b,line=self._peek();cat=self.cats[ord(c)];self.index+=1
   if cat==15:raise Diagnostic(3,a,b)
   if cat==9:continue
   if cat==14:self.index=len(self.units);self.state=0;continue
   if cat==5:
    old=self.state;self.state=0
    if old==0:return self._emit(2,-1,'par',a,b,1)
    if old==1:return self._emit(1,10,' ',a,b,1)
    continue
   if cat==10:
    if self.state!=1:continue
    self.state=2;return self._emit(1,10,' ',a,b,0)
   if cat==0:
    c,_,b,line=self._peek();following=self.cats[ord(c)];name=c;self.index+=1
    self.state=2 if following in (10,11) else 1
    if following==11:
     while self.index<len(self.units):
      c,_,stop,_=self._peek()
      if self.cats[ord(c)]!=11:break
      name+=c;b=stop;self.index+=1
    return self._emit(2,-1,name,a,b,int(line))
   self.state=1;return self._emit(3 if cat==13 else 1,cat,c,a,b,0)
  return Token(0,-1,'',self.source,self.occurrence,self.offset,self.offset,-1,0)
 def checkpoint(self):return copy.deepcopy(self.__dict__)
 def reusable(self,checkpoint):return self.__dict__==checkpoint

def tokens(raw,assignments=()):
 m=Mouth(raw)
 for args in assignments:m.assign(*args)
 result=[]
 for _ in range(len(raw)*2+5):
  t=m.next()
  if t.kind==0:return result
  result.append(t)
 raise AssertionError('nonprogress')

def strict_token(token):
 if token.provenance not in (0,1):raise ValueError('TEX_PREVIEW_TOKEN_FORBIDDEN')
 return True
