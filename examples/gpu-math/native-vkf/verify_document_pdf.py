"""Python3.14 actual vector-pdf.mjs semantic and raster comparison; runtime writer is VKF."""
import argparse,hashlib,json,math,re,subprocess,sys,zlib
from pathlib import Path
assert sys.version_info[:2]==(3,14)
p=argparse.ArgumentParser(description=__doc__)
for name in ['compiler','wasm-compiler','wasm-runtime','fonts','operators','vectors','output']:p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'passed':False,'completeRendererPort':False,'performanceValidated':False,'sourceHashes':{p.name:sha(p) for p in root.glob('document_pdf*.vkf')},'referenceSha256':sha(root.parent/'vector-pdf.mjs'),'fontCatalogSha256':sha(a.fonts),'operatorsSha256':sha(a.operators),'vectorsSha256':sha(a.vectors),'excluded':['Explicit image asset-byte provider','Compressed byte identity (VKF emits ordinary uncompressed vector streams)']}
def run(command,input=None,timeout=300):
 q=subprocess.run(list(map(str,command)),text=True,input=input,capture_output=True,timeout=timeout)
 assert q.returncode==0,(command,q.stdout,q.stderr)
 return q.stdout
maximum=0
token_re=re.compile(rb'<[0-9A-Fa-f]*>|/[^\s\[\]<>]+|<<|>>|\[|\]|[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?|[^\s\[\]<>]+')
number_re=re.compile(rb'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?\Z')
def tokens(data):
 out=[]
 for token in token_re.findall(data):
  if number_re.fullmatch(token):out.append(float(token))
  elif token.startswith(b'<') and token not in [b'<<',b'>>']:out.append(bytes.fromhex(token[1:-1].decode()))
  else:out.append(token)
 return out
def objects(path):
 data=path.read_bytes();assert data.startswith(b'%PDF-1.7\n')
 xref=int(re.search(rb'startxref\n(\d+)\n',data)[1]);assert data[xref:xref+4]==b'xref'
 out=[]
 for m in re.finditer(rb'(\d+) 0 obj\n(.*?)\nendobj\n',data,re.S):
  identifier=int(m[1]);body=m[2];assert identifier==len(out)+1
  if b'\nstream\n' in body:
   dictionary,stream=body.split(b'\nstream\n',1);assert stream.endswith(b'\nendstream');stream=stream[:-10]
   length=int(re.search(rb'/Length (\d+)',dictionary)[1]);assert len(stream)==length,(path,identifier,len(stream),length)
   if b'/FlateDecode' in dictionary:stream=zlib.decompress(stream)
   dictionary=re.sub(rb'/Length \d+',b'',dictionary);dictionary=dictionary.replace(b'/Filter /FlateDecode',b'')
   out.append((tokens(dictionary),tokens(stream)))
  else:out.append((tokens(body),None))
 return out
def compare(e,v,path=''):
 global maximum
 assert len(e)==len(v),(path,len(e),len(v))
 for i,(x,y) in enumerate(zip(e,v)):
  name=path+'/'+str(i)
  if isinstance(x,(list,tuple)):compare(x,y,name)
  elif isinstance(x,float):
   assert isinstance(y,float) and math.isfinite(y),(name,x,y)
   error=abs(x-y);maximum=max(maximum,error);assert error<=1e-9,(name,x,y,error)
  else:assert x==y,(name,x,y)
try:
 glyph=lambda key,x,y,**kw:dict(kind='glyph',key=key,x=x,y=y,**kw)
 page=lambda items,**kw:dict(width=200,height=300,items=items,**kw)
 layouts=[
  dict(pages=[page([glyph('text/x',10,30),glyph('text/x',30,30),dict(kind='rule',x=10,y=40,width=80,height=.2,color=[1,0,0,.4])]),page([glyph('text/x',10,30)])]),
  dict(pages=[page([glyph('text/x',20.123456789012344,50.987654321012345,sx=2,sy=3,crop=[-3,1],cropX=[1,4]),glyph('text/x',40,80,sx=-1,sy=.5),glyph('text/x',60,100,sx=0),dict(kind='field',key='text/x',x=80,y=120)])]),
  dict(pages=[page([dict(kind='segment',x=10,y=20,delta=[50,-5],lineWidth=.5,dash='dashed'),dict(kind='bezier',x=10,y=50,delta=[50,0],controls=[dict(x=10,y=-20),dict(x=40,y=-20)],lineWidth=.7,color=[.2,.3,.4,.8]),dict(kind='circle',x=10,y=90,width=30,height=20,fill=True,fillColor=[1,0,0],strokeColor=[0,0,1,.4],lineWidth=1),dict(kind='circle',x=80,y=90,width=20,height=20,fill=True,fillColor=[.2,.4,.6,.5],lineWidth=0,dash='ignored-on-fill'),dict(kind='vectorrect',x=10,y=130,width=30,height=20,lineWidth=1,dash='dotted'),dict(kind='vectorrect',x=60,y=130,width=30,height=20,lineWidth=.4,dash='densely dotted'),dict(kind='vectorrect',x=110,y=130,width=30,height=20,lineWidth=2,dash='loosely dotted',sx=.5,sy=2)])]),
  dict(pages=[page([dict(kind='link',x=10,y=20,width=40,height=15,color=[1,0,0],target=dict(type='uri',value='https://example.test/å b?x=(y)')),dict(kind='link',x=10,y=60,width=40,height=15,borderWidth=0,target=dict(type='destination',value='named:next')),dict(kind='link',x=-100,y=-100,width=1,height=1,target=dict(type='uri',value='https://outside.test')),dict(kind='link',x=10,y=100,width=20,height=10,target=None)],links=[dict(x=10,y=130,width=40,height=15,target=dict(type='destination',value='named:next'))]),page([])],destinations={'named:next':dict(page=1,x=10.5,y=30.25)}),
  dict(pages=[page([],links=None)])]
 cases=[dict(layout=layout,defaultColor=[0,0,0,1]) for layout in layouts]
 cases.append(dict(layout=dict(pages=[page([glyph('text/x',10,30),dict(kind='rule',x=10,y=40,width=80,height=.2)])]),defaultColor=[.1,.2,.3,.5]))
 (a.output/'cases.json').write_text(json.dumps(cases,ensure_ascii=True,indent=2)+'\n')
 oracle=a.output/'reference.mjs';oracle.write_text("import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';import{gunzipSync}from'node:zlib';const{exportVectorPdf}=await import(pathToFileURL(process.argv[2]));const vectors=JSON.parse(gunzipSync(await readFile(process.argv[3]))),cases=JSON.parse(await readFile(process.argv[4]));for(let i=0;i<cases.length;i++){const c=cases[i];const pdf=await exportVectorPdf(c.layout,vectors,{defaultColor:c.defaultColor,compressionWorker:false});await writeFile(process.argv[5]+'/reference-'+i+'.pdf',pdf);}")
 run(['node',oracle,root.parent/'vector-pdf.mjs',a.vectors,a.output/'cases.json',a.output])
 build=run([a.compiler,'-b',root/'document_pdf_dump.vkf','-o',a.output/'dump','--diagnostics']);(a.output/'native-build.json').write_text(build)
 entries=[str(a.fonts),str(a.operators),str(len(cases))]
 for i,c in enumerate(cases):
  path=a.output/f'layout-{i}.json';path.write_text(json.dumps(c['layout'],ensure_ascii=True));entries.extend([str(path),json.dumps(c['defaultColor']),str(a.output/f'native-{i}.pdf')])
 run([a.output/'dump'],input='\n'.join(entries)+'\n')
 for i in range(len(cases)):compare(objects(a.output/f'reference-{i}.pdf'),objects(a.output/f'native-{i}.pdf'),f'native/{i}')
 report.update(nativePassed=True,nativeCases=len(cases),nativeMaximumNumericError=maximum);(a.output/'native-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 build=run([a.compiler,'-b',root/'document_pdf_kernel.vkf','-o',a.output/'kernel','--diagnostics']);(a.output/'kernel-build.json').write_text(build)
 manifest=a.output/'manifest.json';wasm=a.output/'kernel.wasm';run([a.wasm_compiler,'--typed-ir',json.loads(build)['typed_ir_path'],'--wasm',wasm,'--manifest',manifest,'--entry','pdf_encode','--prune-to-entry'])
 driver=a.output/'run-wasm.mjs';driver.write_text("import{readFile,writeFile}from'node:fs/promises';import{pathToFileURL}from'node:url';const{createSymbolicKernel}=await import(pathToFileURL(process.argv[2]));const manifest=JSON.parse(await readFile(process.argv[3])),{instance}=await WebAssembly.instantiate(await readFile(process.argv[4])),kernel=createSymbolicKernel({instance,manifest}),fonts=await readFile(process.argv[5],'utf8'),operators=await readFile(process.argv[6],'utf8'),cases=JSON.parse(await readFile(process.argv[7]));for(let i=0;i<cases.length;i++){const c=cases[i],pdf=kernel.invokeValue('pdf_encode',[fonts,operators,JSON.stringify(c.layout),JSON.stringify(c.defaultColor)]);await writeFile(process.argv[8]+'/wasm-'+i+'.pdf',pdf);await writeFile(process.argv[8]+'/progress.json',JSON.stringify({completed:i+1,total:cases.length}));}")
 run(['node',driver,a.wasm_runtime,manifest,wasm,a.fonts,a.operators,a.output/'cases.json',a.output],timeout=300)
 for i in range(len(cases)):
  compare(objects(a.output/f'reference-{i}.pdf'),objects(a.output/f'wasm-{i}.pdf'),f'wasm/{i}')
  assert (a.output/f'native-{i}.pdf').read_bytes()==(a.output/f'wasm-{i}.pdf').read_bytes(),('backend PDF byte mismatch',i)
 report.update(wasmPassed=True,wasmCases=len(cases),maximumNumericError=maximum,nativeWasmBytesEqual=True)
 from PIL import Image
 import numpy as np
 raster=[]
 for scale in [1,8]:
  for i,c in enumerate(cases):
   for backend in ['reference','native']:run(['mutool','draw','-q','-r',str(72*scale),'-o',a.output/f'{backend}-{i}-{scale}x-%d.png',a.output/f'{backend}-{i}.pdf'])
   for page_no in range(1,len(c['layout']['pages'])+1):
    x=np.array(Image.open(a.output/f'reference-{i}-{scale}x-{page_no}.png')).astype(np.int16);y=np.array(Image.open(a.output/f'native-{i}-{scale}x-{page_no}.png')).astype(np.int16);assert x.shape==y.shape
    delta=np.abs(x-y);changed=int(np.any(delta!=0,axis=2).sum());maxdelta=int(delta.max());raster.append(dict(case=i,page=page_no,zoom=scale,changedPixels=changed,maximumChannelDelta=maxdelta));assert changed==0,(i,page_no,scale,changed,maxdelta)
 report.update(passed=True,rasterComparisons=raster,rasterPixelsExact=True)
finally:(a.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','nativeCases','wasmCases','maximumNumericError','rasterPixelsExact']}))
