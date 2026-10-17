import assert from 'node:assert/strict';
import * as candidate from '../latex_operation_binding.mjs';
import * as baseline from './fixtures/certificate-baseline.mjs';
const checks=[],traces=[],test=(name,f)=>{f();checks.push(name);};
const empty=revision=>({revision,sources:[],scopes:[],groups:[]});
const fixture=()=>({documentId:'d',revision:0,resources:[],sources:[{id:'s',version:0,text:'ab'}],scopes:[{id:'p',sourceId:'s',text:'ab',baseByte:0,operations:[{operation:0,start:0,stop:1,groupId:'g',leaves:[{id:'l',part:0,resources:[]}]}]}],groups:[{id:'g',contentVersion:0,layoutVersion:0,contentKey:'g',layoutKey:'g',edges:[],spans:[{sourceId:'s',start:0,end:2}]}]});
function observe(m,make,auth=true){
 const p=m.reviseProvenance(m.beginProvenance(fixture()),empty(1)),trace=[];
 const d=make(trace,p),clone=globalThis.structuredClone;let clones=0,result;
 globalThis.structuredClone=(x,...rest)=>{clones++;return clone(x,...rest);};
 try{result={value:m.reviseProvenance(auth?p:{},d)};}catch(e){result={error:[e.constructor.name,e.message]};}finally{globalThis.structuredClone=clone;}
 const saved=clone(p),next=m.reviseProvenance(p,empty(2));assert.equal(next.revision,2);assert.deepEqual(p,saved);assert.equal(next.scopes[0],p.scopes[0]);
 return {result,trace,clones};
}
function compare(make,auth=true){const a=observe(candidate,make,auth),b=observe(baseline,make,auth);assert.deepEqual(a,b);traces.push(a);return a;}
const proxy=(trace,target,change=false)=>{let own=0;return new Proxy(target,{
 getPrototypeOf(t){trace.push('prototype');return Reflect.getPrototypeOf(t);},
 ownKeys(t){trace.push('keys');own++;return Reflect.ownKeys(t);},
 getOwnPropertyDescriptor(t,k){trace.push('descriptor:'+String(k));if(change&&own>1)throw Error('second observation');return Reflect.getOwnPropertyDescriptor(t,k);}
});};
test('certified previous observes Proxy delta once and preserves clone rejection',()=>{const r=compare(t=>proxy(t,empty(2),true));assert.equal(r.result.error[0],'DOMException');assert.equal(r.clones,1);assert.equal(r.trace.filter(x=>x==='keys').length,1);});
test('invalid accessor descriptor rejects without getter callbacks or clone retry',()=>{const r=compare(t=>{const d=empty(2);Object.defineProperty(d,'revision',{enumerable:true,get(){t.push('GETTER');return 2;}});return proxy(t,d,true);});assert.deepEqual(r.result.error,['Error','Unsupported snapshot property']);assert.equal(r.clones,0);assert.ok(!r.trace.includes('GETTER'));});
test('nested Proxy structuredClone rejection has identical trace and one clone',()=>{const r=compare(t=>({...empty(2),sources:proxy(t,[])}));assert.equal(r.result.error[0],'DOMException');assert.equal(r.clones,1);});
test('authentication rejects before observing caller delta',()=>{const r=compare(t=>proxy(t,empty(2)),false);assert.deepEqual(r.result.error,['Error','Entry owner session required']);assert.deepEqual(r.trace,[]);assert.equal(r.clones,0);});
test('semantic failure after detached snapshot falls back without recloning and preserves next revision',()=>{const r=compare((t,p)=>({...empty(2),groups:[{...p.groups[0],contentVersion:1,layoutVersion:1,spans:[{sourceId:'s',start:1,end:2}]}]}));assert.deepEqual(r.result.error,['Error','Leaf outside declared group origins']);assert.equal(r.clones,1);});
test('invalid delta and revision ordering preserve baseline errors without retry',()=>{for(const d of [{...empty(2),extra:1},empty(1),{revision:2,sources:[],scopes:[]}]){const r=compare(()=>d);assert.ok(r.result.error);assert.equal(r.clones,1);}});
console.log(JSON.stringify({passed:true,checks,traces}));
