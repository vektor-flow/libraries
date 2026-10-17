import assert from 'node:assert/strict';
import {fixture} from './columns-fixture.mjs';
import {beginProvenance} from '../latex_operation_binding.mjs';
import * as current from '../document_producer_adapter.mjs';
import * as baseline from '../baseline_adapter.mjs';
const checks=[];
const test=(name,fn)=>{fn();checks.push(name);};
const floats=['xs','ys','sxs','sys','widths','heights'],ints=['kinds','paints','payloads'];
function pair(f){const o=beginProvenance(f.owner);return [current.prepareProducerDocument(f.result,o,f.options),baseline.prepareProducerDocument(f.result,o,f.options)];}
test('Array and typed numeric columns preserve exact output',()=>{
 for(const typed of [false,true]){const f=fixture(1),a=f.result.document.arena;a.xs[0]=-0;a.xs[1]=1.25;
 if(typed){for(const k of floats)a[k]=Float64Array.from(a[k]);for(const k of ints)a[k]=Int32Array.from(a[k]);a.draws=Uint8Array.from(a.draws);for(const k of ['a260_operations','a260_starts','a260_stops','a260_parts'])a[k]=Float64Array.from(a[k]);}
 const [x,y]=pair(f);assert.deepEqual(x,y);assert.ok(Object.is(x.update.scene.arena.xs[0],-0));
 }
});
test('original invalid values reject without coercion with matching diagnostics',()=>{
 for(const [key,values] of [['xs',['1',NaN,Infinity,undefined,null,1n]],['kinds',['2',2.5,2147483648,-2147483649,4]],['paints',[2147483648]],['payloads',[-2147483649]],['draws',[false,0,2,'1',NaN]],['keys',[3]],['a260_operations',['0',-1,1.5,Number.MAX_SAFE_INTEGER+1]],['a260_texts',[4]]]){
 for(const value of values){const f=fixture(1);f.result.document.arena[key][0]=value;const o=beginProvenance(f.owner);let errors=[];for(const m of [baseline,current]){try{m.prepareProducerDocument(f.result,o,f.options);errors.push(null);}catch(e){errors.push(e.message);}}assert.ok(errors[0],key);assert.equal(errors[1],errors[0],key);}
 }
});
test('shared buffers DataView missing extents and sparse columns rejected',()=>{
 for(const change of [a=>a.xs=new Float64Array(new SharedArrayBuffer(24)),a=>a.xs=new DataView(new ArrayBuffer(24)),a=>a.xs=[1],a=>delete a.xs[1],a=>a.draws=new Uint8Array(new SharedArrayBuffer(3))]){const f=fixture(1);change(f.result.document.arena);assert.throws(()=>current.prepareProducerDocument(f.result,beginProvenance(f.owner),f.options));}
});
test('caller mutation and output mutation cannot alter retained snapshot',()=>{
 const f=fixture(10),[x,y]=pair(f);for(const k of [...floats,...ints,'draws','keys'])f.result.document.arena[k].fill(k==='keys'?'bad':999);
 for(let page=0;page<10;page++){const expected=baseline.selectProducerPage(y,page),out=current.selectProducerPage(x,page);assert.deepEqual(out,expected);for(const k of [...floats,...ints,'draws','keys'])out.update.scene.arena[k].fill(k==='keys'?'bad':99);assert.deepEqual(current.selectProducerPage(x,page),expected);}
});
test('genuine owner and previous binding remain mandatory',()=>{
 const f=fixture(1);assert.throws(()=>current.prepareProducerDocument(f.result,f.owner,f.options));const owner=beginProvenance(f.owner);const p=current.prepareProducerDocument(f.result,owner,f.options);assert.throws(()=>current.prepareProducerDocument(f.result,owner,{...f.options,previous:{...p.bound}}));
 f.result.document.arena.a260_operations[0]=999;assert.throws(()=>current.prepareProducerDocument(f.result,owner,f.options));
});
console.log(JSON.stringify({passed:true,checks}));
