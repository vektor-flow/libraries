import assert from 'node:assert/strict';
import * as candidate from '../latex_operation_binding.mjs';
import * as baseline from './fixtures/contiguity-original-binding.mjs';
import * as countedOld from './fixtures/contiguity-counted-old.mjs';
import * as countedNew from './fixtures/contiguity-counted-new.mjs';
const checks=[];const test=(name,f)=>{f();checks.push(name);};
const outcome=f=>{try{return {value:f()};}catch(e){return {error:e.message,name:e.name};}};
function fixture(ids,document=true){
 const text='x',spans=[{sourceId:'s',start:0,end:1}];
 const o={documentId:'groups',revision:0,resources:[],sources:[{id:'s',version:0,text}],groups:[...new Set(ids)].map(id=>({id,contentVersion:0,layoutVersion:0,contentKey:'c',layoutKey:'l',edges:[],spans})),scopes:[{id:'scope',sourceId:'s',text,baseByte:0,operations:ids.map((groupId,i)=>({operation:i*3+2,start:0,stop:1,groupId,leaves:[{part:7,id:'leaf'+i,resources:[]}]}))}]};
 const arena={count:ids.length,kinds:ids.map(()=>2),a260_scopes:ids.map(()=>'scope'),a260_texts:ids.map(()=>text),a260_operations:ids.map((_,i)=>i*3+2),a260_starts:ids.map(()=>0),a260_stops:ids.map(()=>1),a260_parts:ids.map(()=>7)};
 const r={complete:true,diagnostics:'',unresolved_json:'[]',...(document?{document:{arena,page_count:1,firsts:[0],counts:[ids.length],widths:[100],heights:[100]}}:{scene:{arena,width:100,height:100}})};
 return {o,r,document};
}
const bind=(m,f,previous=null)=>m[f.document?'bindOperationDocument':'bindOperationFragment'](f.r,m.beginProvenance(f.o),previous);
let comparisons=0;
function compare(f){const a=outcome(()=>bind(baseline,f)),b=outcome(()=>bind(candidate,f));assert.deepEqual(b,a);comparisons++;return b;}
test('one many adjacent sparse reordered and empty groups preserve complete fragment and document outputs',()=>{
 for(const document of [false,true])for(const ids of [[],['g'],['g','g','g'],['g900','g2','g70'],['a','a','b','b','c'],Array.from({length:200},(_,i)=>'g'+i)]){
  const f=fixture(ids,document),result=compare(f);assert.ok(result.value);assert.deepEqual(result.value.metadata.groups.map(g=>[g.id,g.first,g.count]),ids.reduce((a,id,i)=>{if(a.at(-1)?.[0]===id)a.at(-1)[2]++;else a.push([id,i,1]);return a;},[]));
 }
 const f=fixture([]);f.o.groups=[{id:'unused'}];assert.ok(compare(f).value);
});
test('noncontiguous reappearance rejects with exact error and ownership checks retain precedence',()=>{
 for(const document of [false,true]){
  const f=fixture(['a','b','a'],document);assert.equal(compare(f).error,'Noncontiguous semantic group');
  for(const mutate of [f=>f.r.complete=false,f=>(f.document?f.r.document:f.r.scene).arena.a260_operations[2]=999,f=>(f.document?f.r.document:f.r.scene).arena.a260_stops[2]=0,f=>(f.document?f.r.document:f.r.scene).arena.a260_parts[2]=99]){const f=fixture(['a','b','a'],document);mutate(f);const result=compare(f);assert.ok(result.error);assert.notEqual(result.error,'Noncontiguous semantic group');}
  for(const m of [baseline,candidate]){const f=fixture(['a'],document);assert.throws(()=>m[document?'bindOperationDocument':'bindOperationFragment'](f.r,structuredClone(m.beginProvenance(f.o))),/Entry owner session required/);}
 }
});
test('legacy nonstring IDs including NaN retain downstream rejection and competing-error order',()=>{
 for(const id of [NaN,0,-0,1,null,undefined,false,{},1n,''])for(const document of [false,true]){
  for(const ids of [[id,id],[id,'g',id]]){const f=fixture(ids,document);const result=compare(f);assert.ok(result.error);}
 }
 // NaN is admitted by legacy entry; strict equality must never detect a repeat.
 const f=fixture([NaN,NaN]);for(const m of [baseline,candidate])assert.ok(m.beginProvenance(f.o));assert.notEqual(compare(f).error,'Noncontiguous semantic group');
});
test('previous revision source versions group versions and snapshot isolation remain exact',()=>{
 for(const document of [false,true]){
  const f=fixture(['a','a','b'],document),old=bind(baseline,f);assert.deepEqual(bind(candidate,f),old);
  for(const m of [baseline,candidate]){assert.throws(()=>bind(m,f,old),/Revision must advance/);const next=structuredClone(f);next.o.revision=1;assert.deepEqual(bind(m,next,old),bind(baseline,next,old));assert.deepEqual(bind(m,f),old);next.o.documentId='other';assert.deepEqual(outcome(()=>bind(m,next,old)),outcome(()=>bind(baseline,next,old)));}
 }
});
let work=[];
test('actual binding membership work is quadratic before and one Set lookup per transition after',()=>{
 for(const n of [20,200,800]){
  const f=fixture(Array.from({length:n},(_,i)=>'g'+i));countedOld.work.count=0;countedNew.work.count=0;
  const old=bind(countedOld,f),next=bind(countedNew,f);assert.deepEqual(next,old);
  work.push({groups:n,oldComparisons:countedOld.work.count,newLookups:countedNew.work.count});assert.equal(countedOld.work.count,n*(n-1)/2);assert.equal(countedNew.work.count,n);
 }
 const f=fixture(Array(800).fill('one'));countedNew.work.count=0;bind(countedNew,f);assert.equal(countedNew.work.count,1);
});
console.log(JSON.stringify({passed:true,checks,comparisons,work,scope:'Actual private binding; synthetic CPU only'}));
