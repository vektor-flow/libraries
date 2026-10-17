import assert from 'node:assert/strict';
import * as candidate from '../latex_operation_binding.mjs';
import * as baseline from './fixtures/entry-original-binding.mjs';
const checks=[];const test=(name,f)=>{f();checks.push(name);};
const outcome=f=>{try{return {value:f()};}catch(e){return {error:e.message,name:e.name};}};
let comparisons=0;
function fixture(text='é😀中x',explicit=false){
 const bytes=new TextEncoder().encode(text).length;
 const o={documentId:'entry',revision:0,resources:[],sources:[{id:'s',version:0,text}],groups:[{id:'g',spans:[]}],scopes:[{id:'scope',sourceId:'s',text,baseByte:0,operations:[9,2].map(operation=>({operation,start:0,stop:bytes,groupId:'g',leaves:[{part:3,id:'leaf-'+operation,resources:[]}]}))}]};
 if(explicit){o.scopes[0].a262_originMode='explicit';for(const op of o.scopes[0].operations)op.a262_origins=[{sourceId:'s',startByte:0,stopByte:bytes},{sourceId:'s',startByte:0,stopByte:bytes}];}
 return o;
}
function compare(o){const b=outcome(()=>baseline.beginProvenance(o)),c=outcome(()=>candidate.beginProvenance(o));assert.deepEqual(c,b);comparisons++;return c;}
test('entry accepts sparse reordered operations repeated origins and Unicode scopes',()=>{for(const text of ['','ascii','é中','a😀z','𐀀💩é中'])for(const explicit of [false,true])compare(fixture(text,explicit));const o=fixture();o.sources[0].text='😀'+o.sources[0].text+'Q';o.scopes[0].baseByte=4;assert.ok(compare(o).value);});
test('entry preserves exact errors for every offset and malformed surrogate source',()=>{
 for(const text of ['','ascii','é中','a😀z','\ud800','\udc00','a\ud800b','😀\udc00','ab\ud800','\ud800\ud800'])for(const explicit of [false,true])for(const n of [-1,-0,0.5,NaN,Infinity,Number.MAX_SAFE_INTEGER,1e9,'0',null,undefined,0,1,2,3,4,5,6,7,8,9,10])for(const field of ['base','start','stop','originStart','originStop']){
  const o=fixture(text,explicit),s=o.scopes[0],op=s.operations[0];
  if(field==='base')s.baseByte=n;else if(field==='start')op.start=n;else if(field==='stop')op.stop=n;else if(explicit)op.a262_origins[0][field==='originStart'?'startByte':'stopByte']=n;else continue;
  compare(o);
 }
});
test('entry preserves duplicate validation and competing error ordering',()=>{
 const mutations=[o=>o.sources.push({...o.sources[0]}),o=>o.groups.push({...o.groups[0]}),o=>o.scopes.push(structuredClone(o.scopes[0])),o=>o.scopes[0].operations.push(structuredClone(o.scopes[0].operations[0])),o=>o.scopes[0].operations[1].leaves[0].id='leaf-9',o=>o.scopes[0].operations[0].leaves.push({...o.scopes[0].operations[0].leaves[0]}),o=>o.scopes[0].a262_originMode='bad',o=>o.scopes[0].operations[0].groupId='missing',o=>o.scopes[0].operations[0].a262_origins=[],o=>o.sources[0].version=-1];
 for(const mutate of mutations)for(const malformed of [false,true]){const o=fixture();mutate(o);if(malformed)o.sources[0].text='\ud800';assert.ok(compare(o).error);}
});
test('entry clones freezes authenticates only successful sessions and isolates source revisions',()=>{
 const frozen=x=>{if(x&&typeof x==='object'){assert.ok(Object.isFrozen(x));for(const v of Object.values(x))frozen(v);}};
 for(const m of [baseline,candidate]){const o=fixture(),s=m.beginProvenance(o);frozen(s);assert.notEqual(s,o);o.sources[0].text='changed';o.sources[0].version=1;o.scopes[0].operations[0].leaves[0].resources.push('changed');assert.equal(s.sources[0].text,'é😀中x');assert.deepEqual(s.scopes[0].operations[0].leaves[0].resources,[]);
 const route=[{block:0,scope:'scope'}];assert.equal(m.documentEntryRoutes(s,route).scopes[0],'scope');for(const bad of [o,structuredClone(s)])assert.throws(()=>m.documentEntryRoutes(bad,route),/Entry owner session required/);
 const bad=fixture('a\ud800');assert.throws(()=>m.beginProvenance(bad));assert.throws(()=>m.documentEntryRoutes(bad,route),/Entry owner session required/);bad.sources[0].text='fresh';bad.sources[0].version=7;bad.scopes[0].text='fresh';for(const op of bad.scopes[0].operations)op.stop=5;const next=m.beginProvenance(bad);assert.equal(next.sources[0].version,7);assert.equal(s.sources[0].version,0);
 }
});
let work;
test('entry request local reuse reduces deterministic repeated source scan work',()=>{
 const o=fixture('é😀中x'.repeat(250));o.scopes[0].operations=Array.from({length:200},(_,i)=>({operation:i,start:0,stop:2500,groupId:'g',leaves:[]}));
 const original=String.prototype.codePointAt;const count=m=>{let calls=0;String.prototype.codePointAt=function(...args){calls++;return original.apply(this,args);};try{m.beginProvenance(o);}finally{String.prototype.codePointAt=original;}return calls;};
 work={baseline:count(baseline),candidate:count(candidate)};assert.equal(work.baseline,202201);assert.equal(work.candidate,1403);assert.equal(count(candidate),1403);
});
console.log(JSON.stringify({passed:true,checks,comparisons,work}));
