import assert from 'node:assert/strict';
import * as candidate from '../latex_operation_binding.mjs';
import * as unrepaired from './fixtures/owner-lookup-e358.mjs';
import * as baseline from './fixtures/owner-lookup-original.mjs';
import * as old from './fixtures/owner-lookup-counted-old.mjs';
import * as next from './fixtures/owner-lookup-counted-new.mjs';
import {fixture,bind} from './fixtures/owner-lookup-fixture.mjs';
const checks=[],test=(name,f)=>{f();checks.push(name);};
const outcome=f=>{try{return {value:f()};}catch(e){return {error:e.message,name:e.name};}};
let comparisons=0;const compare=f=>{const a=outcome(()=>bind(baseline,f)),b=outcome(()=>bind(candidate,f));assert.deepEqual(b,a);comparisons++;return b;};
test('dense sparse reversed and empty authentic Fragment and Document outputs match frozen binder',()=>{
 for(const document of [false,true])for(const [n,p] of [[0,0],[1,1],[1,80],[80,1],[32,32]])for(const reverse of [false,true]){
  const f=fixture(n,p,document);if(reverse){f.o.scopes[0].operations.reverse();for(const op of f.o.scopes[0].operations)op.leaves.reverse();for(const key of Object.keys(f.a))if(Array.isArray(f.a[key]))f.a[key].reverse();}
  assert.ok(compare(f).value);
 }
});
test('missing invalid duplicate signed zero and competing failures preserve exact error order',()=>{
 const mutations=[f=>f.a.a260_operations[0]=99999,f=>f.a.a260_parts[0]=99999,f=>f.a.a260_starts[0]=9,f=>f.a.a260_stops[0]=9,f=>f.r.complete=false,f=>f.a.a260_scopes[0]='missing',f=>f.a.a260_parts[1]=0,f=>f.o.scopes[0].operations.push(structuredClone(f.o.scopes[0].operations[0])),f=>f.o.scopes[0].operations[0].leaves.push(structuredClone(f.o.scopes[0].operations[0].leaves[0]))];
 for(const document of [false,true]){
  for(const mutation of mutations){const f=fixture(3,3,document);mutation(f);assert.ok(compare(f).error);f.a.a260_stops[0]=99;assert.ok(compare(f).error);}
  for(const value of [NaN,undefined,null,-1,0.5,Infinity,'0'])for(const key of ['a260_operations','a260_parts']){const f=fixture(3,3,document);f.a[key][0]=value;assert.ok(compare(f).error);}
  const f=fixture(3,3,document);f.o.scopes[0].operations[0].operation=-0;f.o.scopes[0].operations[0].leaves[0].part=-0;assert.ok(compare(f).value);
 }
});
test('authentic revised sessions preserve previous values and reject copied foreign owners',()=>{
 for(const document of [false,true]){
  const values=[];
  for(const m of [baseline,candidate]){
   const f=fixture(5,5,document),session=m.beginProvenance(f.o),previous=bind(m,f,null,session),snapshot=structuredClone(previous);
   const revised=m.reviseProvenance(session,{revision:1,sources:[],scopes:[],groups:[]});assert.equal(revised.scopes[0],session.scopes[0]);
   values.push(bind(m,f,previous,revised));assert.deepEqual(previous,snapshot);assert.deepEqual(bind(m,f,null,session),snapshot);
   assert.throws(()=>bind(m,f,null,structuredClone(session)),/Entry owner session required/);
   const foreign=baseline.beginProvenance(f.o);if(m===candidate)assert.throws(()=>bind(m,f,null,foreign),/Entry owner session required/);
  }
  assert.deepEqual(values[0],values[1]);
 }
});
const work=[];
test('actual dense binding scan counts change from quadratic to linear in owner records',()=>{
 for(const [n,p] of [[20,20],[80,80],[160,160]]){
  const f=fixture(n,p);for(const m of [old,next])for(const k of Object.keys(m.work))m.work[k]=0;
  assert.deepEqual(bind(next,f),bind(old,f));
  assert.equal(old.work.operation,p*n*(n+1)/2);assert.equal(old.work.part,n*p*(p+1)/2);
  assert.equal(next.work.operation,n);assert.equal(next.work.part,n*p);assert.equal(next.work.lookups,2*n*p);
  work.push({operations:n,parts:p,old:{...old.work},next:{...next.work}});
 }
});
test('progressive lookup preserves first strict match and avoids scanning unused suffixes',()=>{
 const rows=[{operation:NaN},{operation:-0},{operation:0},{operation:7},{operation:7}];
 const lookup=next.createOwnerLookup();assert.equal(lookup(rows,'operation',0),rows[1]);assert.equal(lookup(rows,'operation',7),rows[3]);assert.equal(lookup(rows,'operation',NaN),undefined);assert.equal(lookup(rows,'operation',999),undefined);assert.equal(lookup(rows,'operation',-0),rows[1]);
 const short=[{part:1},null];assert.equal(next.createOwnerLookup()(short,'part',1),short[0]);
});
test('shared operation and leaf arrays retain separate field lookup state through public entry and bind',()=>{
 for(const document of [false,true])for(const reversed of [false,true]){
  const f=fixture(2,1,document),scope=f.o.scopes[0],[first,second]=scope.operations;
  const shared=[first];Object.assign(first,{part:7,id:second.leaves[0].id,resources:[]});
  scope.operations=shared;second.leaves=shared;
  f.o.scopes.push({...scope,id:'second',operations:[second]});
  f.a.a260_scopes[1]='second';f.a.a260_parts[1]=7;
  if(reversed)for(const value of Object.values(f.a))if(Array.isArray(value))value.reverse();
  for(const m of [baseline,candidate,unrepaired]){
   const session=m.beginProvenance(f.o);
   assert.equal(session.scopes[0].operations,session.scopes[1].operations[0].leaves);
   assert.ok(Object.isFrozen(session.scopes[0].operations));
  }
  const expected=outcome(()=>bind(baseline,f));assert.ok(expected.value);
  assert.deepEqual(outcome(()=>bind(candidate,f)),expected);
  const broken=outcome(()=>bind(unrepaired,f));assert.ok(broken.error);assert.notDeepEqual(broken,expected);
  const revised=candidate.reviseProvenance(candidate.beginProvenance(f.o),{revision:1,sources:[],scopes:[],groups:[]});
  const revisedBase=baseline.reviseProvenance(baseline.beginProvenance(f.o),{revision:1,sources:[],scopes:[],groups:[]});
  assert.deepEqual(bind(candidate,f,null,revised),bind(baseline,f,null,revisedBase));
 }
});
console.log(JSON.stringify({passed:true,checks,comparisons,work}));
