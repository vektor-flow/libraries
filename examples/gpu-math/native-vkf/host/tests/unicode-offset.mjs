import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createByteToUtf16Index} from './fixtures/unicode-probe.mjs';
import {byteToUtf16} from './fixtures/unicode-original-binding.mjs';
import * as candidate from '../latex_operation_binding.mjs';
import * as baseline from './fixtures/unicode-original-binding.mjs';
const checks=[];const test=(name,f)=>{f();checks.push(name);};
const outcome=f=>{try{return {value:f()};}catch(e){return {error:e.message};}};
const texts=['','ascii','é中','a😀z','𐀀💩é中','\ud800','\udc00','a\ud800b','😀\udc00','ab\ud800','\ud800\ud800','a\udfff😀'];
let comparisons=0;
const compare=(text,offsets,convert=createByteToUtf16Index())=>{for(const n of offsets){assert.deepEqual(outcome(()=>convert(text,n)),outcome(()=>byteToUtf16(text,n)),JSON.stringify([text,String(n)]));comparisons++;}};
test('exact valid invalid and reordered UTF8 boundaries including lone surrogates',()=>{for(const t of texts){const ns=Array.from({length:25},(_,i)=>i);compare(t,ns);compare(t,ns.reverse());compare(t,[0,7,2,1,9,0,3,3,4,2,0]);}});
test('negative fractional unsafe nonnumeric and enormous offsets allocate only actual source prefix',()=>{for(const t of texts)compare(t,[-1,-0,0.5,NaN,Infinity,Number.MAX_SAFE_INTEGER,Number.MAX_SAFE_INTEGER+1,1e9,'0',null,undefined,{},2n]);});
test('source changes isolation repeated offsets and exhaustive mixed scalar combinations',()=>{const convert=createByteToUtf16Index();const chars=['a','é','中','😀','\ud800','\udc00'];for(const a of chars)for(const b of chars)for(const c of chars)compare(a+b+c,[0,1,2,3,4,5,6,7,8,9,10,11,12,0,4,2],convert);compare('a😀z',[0,1,5,6],convert);compare('aézz',[0,1,3,4,5],convert);compare('a😀z',[6,5,1,0],createByteToUtf16Index());});
const schema=JSON.parse(readFileSync(new URL('./fixtures/schema314.json',import.meta.url)));
function fixture(explicit=false,text='é😀中x'){
 const a=Object.fromEntries(schema.Arena.map(k=>[k,[]]));Object.assign(a,{count:4,paint_count:0,payload_count:0,paint_table:[],payload_table:[]});
 const source='P'+text+'Q',bytes=new TextEncoder().encode(text).length;
 const o={documentId:'unicode',revision:0,sources:[{id:'s',version:0,text:source}],resources:[],groups:[{id:'g',contentVersion:0,layoutVersion:0,contentKey:'g',layoutKey:'g',edges:[],spans:[{sourceId:'s',start:0,end:source.length}]}],scopes:[{id:'scope',sourceId:'s',text,baseByte:1,operations:[9,2].map(operation=>({operation,start:0,stop:bytes,groupId:'g',leaves:[8,3].map(part=>({part,id:`${operation}-${part}`,resources:[]}))}))}]};
 if(explicit){const s=o.scopes[0];s.a262_originMode='explicit';for(const op of s.operations)op.a262_origins=[{sourceId:'s',startByte:1,stopByte:1+bytes},{sourceId:'s',startByte:0,stopByte:1}];}
 for(const operation of [2,9])for(const part of [3,8]){const row={keys:'',kinds:2,xs:0,ys:0,sxs:1,sys:1,widths:1,heights:1,draws:true,paints:-1,payloads:-1,a260_scopes:'scope',a260_texts:text,a260_operations:operation,a260_starts:0,a260_stops:bytes,a260_parts:part};for(const [k,v]of Object.entries(row))a[k].push(v);}
 const d=Object.fromEntries(schema.PageDocument.map(k=>[k,[]]));Object.assign(d,{arena:a,page_count:1,destination_count:0,firsts:[0],counts:[4],widths:[100],heights:[100]});return {o,r:{document:d,complete:true,diagnostics:'',unresolved_json:'[]'}};
}
const bind=(m,f,old=null)=>m.bindOperationDocument(f.r,m.beginProvenance(f.o),old);
test('full binding Unicode baseByte repeated offsets reordered leaves and explicit origins',()=>{for(const explicit of [false,true])for(const text of ['é😀中x','abcd','😀😀','中é']){const f=fixture(explicit,text);assert.deepEqual(bind(candidate,f),bind(baseline,f));}});
test('full binding authentication span boundaries and source isolation retain rejection',()=>{for(const m of [baseline,candidate]){const f=fixture(),s=m.beginProvenance(f.o);assert.throws(()=>m.bindOperationDocument(f.r,structuredClone(s)),/Entry owner/);f.o.sources[0].text='mutation';assert.deepEqual(m.bindOperationDocument(f.r,s),bind(m,fixture()));for(const mutate of [f=>f.o.scopes[0].baseByte=2,f=>f.o.scopes[0].operations[0].stop=3,f=>f.r.document.arena.a260_stops[0]=3]){const bad=fixture();mutate(bad);assert.throws(()=>bind(m,bad));}}});
test('full binding source revisions and previous ownership guards survive conversion cache',()=>{for(const m of [baseline,candidate]){const old=bind(m,fixture());assert.throws(()=>bind(m,fixture(),old),/Revision must advance/);const f=fixture(false,'中😀éx');f.o.revision=1;assert.throws(()=>bind(m,f,old),/Source changed without version/);f.o.sources[0].version=1;assert.throws(()=>bind(m,f,old),/Source edit requires/);f.o.groups[0].contentVersion=1;f.o.groups[0].layoutVersion=1;const next=bind(m,f,old);assert.equal(next.sourceBinding.sources[0].version,1);assert.deepEqual(bind(m,fixture()),old);}});
let work;
test('deterministic codepoint work falls for repeated and reordered requests',()=>{const text='é😀中x'.repeat(250),offset=new TextEncoder().encode(text).length,requests=Array.from({length:200},(_,i)=>i%2?offset:offset-1);const original=String.prototype.codePointAt;let calls=0;String.prototype.codePointAt=function(...a){calls++;return original.apply(this,a);};try{for(const n of requests)byteToUtf16(text,n);const baselineCalls=calls;calls=0;const convert=createByteToUtf16Index();for(const n of requests)convert(text,n);work={baselineCodepointCalls:baselineCalls,candidateCodepointCalls:calls,sourceScalars:1000,requests:requests.length};assert.equal(baselineCalls,200000);assert.equal(calls,1200);}finally{String.prototype.codePointAt=original;}});
console.log(JSON.stringify({passed:true,checks,comparisons,work,synthetic_only:true}));
