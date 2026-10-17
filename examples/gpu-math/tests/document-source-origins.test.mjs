import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {typesetDocument} from '../document-layout.mjs';
import {typeset} from '../typing-layout.mjs';

const data=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url)));
const prefix=String.raw`\documentclass{article}\usepackage{amsmath}\pagestyle{empty}`+'% é😀\n'+String.raw`\begin{document}`;
const suffix=String.raw`\end{document}`;
const bytes=text=>Buffer.byteLength(text,'utf8');
function assertOrigin(item,source,start,end){
 assert.ok(item.sourceOrigin);
 assert.deepEqual({...item.sourceOrigin,expansionOrder:undefined,clusterId:undefined}, {
  fileId:'document.tex',occurrenceId:1,start,end,byteStart:bytes(source.slice(0,start)),byteEnd:bytes(source.slice(0,end)),
  expansionOrder:undefined,clusterId:undefined,kind:'math'
 });
}
// Every non-provenance field, including metrics, tags and destinations, stays exact.
const provenance=new Set(['sourceOrigin','sourceRange','sourceScopes','sourceScope','sourceGranularity']);
const geometry=value=>Array.isArray(value)?value.map(geometry):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).filter(([key])=>!provenance.has(key)).map(([key,v])=>[key,geometry(v)])):value;

test('repeated bracket and dollar displays retain distinct authored UTF-16 and byte origins',async()=>{
 const expression=String.raw`x+\alpha`,first=String.raw`\[`+expression+String.raw`\]`,second='$$'+expression+'$$';
 const source=prefix+first+second+suffix,result=await typesetDocument(source,data);
 assert.equal(result.complete,true,JSON.stringify(result.diagnostics));
 const items=result.pages.flatMap(page=>page.items);
 assert.equal(items.length,6);
 for(let display=0;display<2;display++){
  const start=prefix.length+(display?first.length:0)+2;
  for(const [index,[a,b]]of [[0,1],[1,2],[2,8]].entries())assertOrigin(items[display*3+index],source,start+a,start+b);
 }
 assert.notEqual(items[0].sourceOrigin.clusterId,items[3].sourceOrigin.clusterId);
 assert.ok(items[0].sourceOrigin.byteStart>items[0].sourceOrigin.start);
});

test('equation variants map body spans while automatic equation tags stay unmapped',async()=>{
 for(const name of ['equation','equation*','displaymath']){
  // Whitespace in the authored begin command differs from the reconstructed wrapper.
  const opening='\\begin  {'+name+'}',source=prefix+opening+'x+x'+'\\end{'+name+'}'+suffix;
  const result=await typesetDocument(source,data);
  assert.equal(result.complete,true,JSON.stringify(result.diagnostics));
  const items=result.pages.flatMap(page=>page.items),body=items.filter(item=>!item.equationTag);
  assert.equal(body.length,3);
  for(let n=0;n<3;n++)assertOrigin(body[n],source,prefix.length+opening.length+n,prefix.length+opening.length+n+1);
  const tags=items.filter(item=>item.equationTag);
  assert.equal(tags.length,name==='equation'?3:0);
  assert.ok(tags.every(item=>!item.sourceOrigin));
 }
});

test('explicit tags and expanded display macros own their authored scopes',async()=>{
 const declaration=String.raw`\newcommand{\pair}{x+x}`,opening=String.raw`\begin{equation}`,body=String.raw`\pair\tag{A}`;
 const source=declaration+prefix+opening+body+String.raw`\end{equation}`+suffix,result=await typesetDocument(source,data);
 assert.equal(result.complete,true,JSON.stringify(result.diagnostics));
 const items=result.pages.flatMap(page=>page.items),start=declaration.length+prefix.length+opening.length;
 assert.equal(items.length,6);
 for(const item of items.slice(0,3))assertOrigin(item,source,start,start+5);
 for(const item of items.slice(3))assertOrigin(item,source,start+5,start+12);
});

test('display producer tracking preserves all layout values against track-off layout',()=>{
 for(const source of [String.raw`x+\frac{a}{b}=\sqrt{x}`,String.raw`\begin{equation}x+x\end{equation}`,String.raw`\begin{equation*}x\tag{A}\end{equation*}`]){
  const options={mode:'display',nativeSemantics:true,displayEnvironment:true,displayWidth:340,packages:['amsmath']};
  const original=typeset(source,data.maps,options),tracked=typeset(source,data.maps,{...options,trackSource:true});
  assert.equal(tracked.complete,true,JSON.stringify(tracked.diagnostics));
  assert.deepEqual(geometry(tracked),geometry(original));
 }
});

test('rewritten references and malformed displays fail closed',async()=>{
 for(const body of [String.raw`\begin{equation}x\label{a}\end{equation}\[x+\ref{a}\]`,String.raw`\[x+\unknowncommand\]`]){
  const result=await typesetDocument(prefix+body+suffix,data),items=result.pages.flatMap(page=>page.items);
  if(body.includes('label'))assert.ok(items.filter(item=>item.sourceOrigin).every(item=>item.sourceOrigin.start<prefix.length+String.raw`\begin{equation}x\label{a}\end{equation}`.length));
  else assert.ok(items.every(item=>!item.sourceOrigin));
 }
});
