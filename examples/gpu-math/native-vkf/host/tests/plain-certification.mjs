import assert from 'node:assert/strict';
import {beginProvenance,reviseProvenance} from '../latex_operation_binding.mjs';
const checks=[],test=(name,f)=>{f();checks.push(name);};
function fixture(){return {documentId:'revision',revision:0,resources:[{id:'r',version:0,binding:'pixels'}],sources:[{id:'s',version:0,text:'Pé😀Q'},{id:'other',version:0,text:'z'}],scopes:[{id:'p',sourceId:'s',text:'é😀',baseByte:1,operations:[{operation:2,start:0,stop:6,groupId:'g',leaves:[{part:3,id:'leaf',resources:['r']}]}]}],groups:[{id:'g',contentVersion:0,layoutVersion:0,contentKey:'old',layoutKey:'old',edges:[],spans:[{sourceId:'s',start:1,end:4}]}]};}
function delta(o){const d=structuredClone({revision:1,sources:[o.sources[0]],scopes:o.scopes,groups:o.groups});d.sources[0].text='P中😀Q';d.sources[0].version=1;d.scopes[0].text='中😀';d.scopes[0].operations[0].stop=7;d.groups[0].contentVersion=1;d.groups[0].layoutVersion=1;d.groups[0].contentKey='new';d.groups[0].layoutKey='new';return d;}

const empty=revision=>({revision,sources:[],scopes:[],groups:[]});
function observe(target,f){const own=Reflect.ownKeys;let visits=0;Reflect.ownKeys=x=>{if(x===target)visits++;return own(x);};try{return {value:f(),visits};}finally{Reflect.ownKeys=own;}}
test('first legacy walk then certified output and independent branches skip only previous traversal',()=>{
 const p=beginProvenance(fixture()),saved=structuredClone(p);
 const first=observe(p,()=>reviseProvenance(p,delta(p)));assert.equal(first.visits,1);
 const n=first.value;assert.equal(observe(n,()=>reviseProvenance(n,empty(2))).visits,0);
 assert.equal(observe(p,()=>reviseProvenance(p,empty(4))).visits,0);
 assert.equal(observe(n,()=>reviseProvenance(n,empty(3))).visits,0);
 assert.deepEqual(p,saved);assert.equal(n.revision,1);
});
test('certification does not authenticate clones fakes or caller mutations',()=>{
 const p=beginProvenance(fixture()),d=delta(p),n=reviseProvenance(p,d),saved=structuredClone(n);
 d.scopes[0].text='bad';d.groups[0].spans[0].end=999;assert.deepEqual(n,saved);
 for(const fake of [structuredClone(n),Object.freeze({...n}),Object.freeze(structuredClone(n))])assert.throws(()=>reviseProvenance(fake,empty(2)),/owner session/);
 assert.throws(()=>n.sources[0].text='bad');assert.deepEqual(n,saved);
});
test('legacy frozen exotic wrappers never certify after rejection',()=>{
 for(const extra of [new Map(),new Date(),new Uint8Array(0),{inner:new Map()},{inner:new Date()},{inner:new Uint8Array(0)}]){
  const p=beginProvenance({...fixture(),extra});assert.ok(Object.isFrozen(p));
  for(let i=0;i<2;i++)assert.equal(observe(p,()=>assert.throws(()=>reviseProvenance(p,empty(1)),/Unsupported snapshot container/)).visits,1);
 }
});
test('certified parents still reject delta cycles depth accessors symbols and exotics without issuing output',()=>{
 const p=reviseProvenance(beginProvenance(fixture()),delta(fixture()));
 for(const mode of ['cycle','depth','accessor','symbol','map','date','typed','hidden']){
  const d=empty(2);if(mode==='cycle')d.extra=d;
  if(mode==='depth'){let x=d;for(let i=0;i<260;i++)x=x.extra={};}
  if(mode==='accessor')Object.defineProperty(d,'extra',{enumerable:true,get(){throw Error('getter must not run');}});
  if(mode==='symbol')d[Symbol('x')]=1;
  if(mode==='hidden')Object.defineProperty(d,'extra',{value:1});
  if(mode==='map')d.extra=new Map();if(mode==='date')d.extra=new Date();if(mode==='typed')d.extra=new Uint8Array(0);
  let output;assert.throws(()=>{output=reviseProvenance(p,d);},/Unsupported snapshot/);assert.equal(output,undefined);
  assert.throws(()=>reviseProvenance(d,empty(3)),/owner session/);
 }
 assert.equal(reviseProvenance(p,empty(2)).revision,2);
});
test('certified sessions retain semantic validation on every failed branch',()=>{
 const p=reviseProvenance(beginProvenance(fixture()),delta(fixture()));
 for(const d of [empty(1),{...empty(2),sources:[{...p.sources[0],version:2}]},{...empty(2),groups:[{...p.groups[0],contentVersion:2,layoutVersion:2,spans:[{sourceId:'s',start:0,end:999}]}]}])assert.throws(()=>reviseProvenance(p,d));
 const bad=fixture();bad.resources.push(bad.resources[0]);const legacy=beginProvenance(bad);
 for(let i=0;i<2;i++)assert.throws(()=>reviseProvenance(legacy,empty(1)),/Invalid immutable resource/);
 assert.equal(reviseProvenance(p,empty(2)).revision,2);
});
console.log(JSON.stringify({passed:true,checks}));
