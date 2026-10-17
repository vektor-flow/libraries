import assert from 'node:assert/strict';
import * as candidate from '../latex_operation_binding.mjs';
import * as baseline from './fixtures/certificate-baseline.mjs';
import * as counted from './fixtures/certificate-counted.mjs';
const checks=[],test=(name,f)=>{f();checks.push(name);};
const empty=revision=>({revision,sources:[],scopes:[],groups:[]});
function fixture(){return {documentId:'certificate',revision:0,resources:[{id:'r',version:0,binding:'pixels'}],sources:[{id:'s',version:0,text:'éx'},{id:'t',version:0,text:'yz'}],scopes:[{id:'p',sourceId:'s',text:'éx',baseByte:0,operations:[{operation:0,start:0,stop:2,groupId:'g',leaves:[{id:'l',part:0,resources:['r']}]}]},{id:'q',sourceId:'t',text:'yz',baseByte:0,operations:[{operation:0,start:0,stop:1,groupId:'h',leaves:[{id:'m',part:0,resources:['r']}]}]}],groups:[{id:'g',contentVersion:0,layoutVersion:0,contentKey:'g',layoutKey:'g',edges:[],spans:[{sourceId:'s',start:0,end:2}]},{id:'h',contentVersion:0,layoutVersion:0,contentKey:'h',layoutKey:'h',edges:[],spans:[{sourceId:'t',start:0,end:2}]}]};}
function pair(data=fixture()){return [candidate,baseline].map(m=>m.reviseProvenance(m.beginProvenance(data),empty(1)));}
function outcome(m,p,d){try{return {value:m.reviseProvenance(p,d)};}catch(e){return {error:[e.constructor.name,e.message]};}}
function compare(ps,d){const a=outcome(candidate,ps[0],d),b=outcome(baseline,ps[1],d);assert.deepEqual(a,b);return a;}
test('legacy full qualification and unchanged certified scopes skip semantic work',()=>{
 const p=counted.beginProvenance(fixture());globalThis.__revisionWork={entryScopes:0,semanticOperations:0,reusedScopes:0};
 const q=counted.reviseProvenance(p,empty(1));assert.deepEqual(globalThis.__revisionWork,{entryScopes:2,semanticOperations:2,reusedScopes:0});
 globalThis.__revisionWork={entryScopes:0,semanticOperations:0,reusedScopes:0};
 const n=counted.reviseProvenance(q,empty(2));assert.deepEqual(globalThis.__revisionWork,{entryScopes:0,semanticOperations:0,reusedScopes:2});assert.equal(n.scopes[0],q.scopes[0]);
});
test('changed scope fully checked while retained scopes skipped; baseline and previous isolation',()=>{
 const ps=pair(),saved=structuredClone(ps[0]),d=empty(2);d.sources=[{...ps[0].sources[0],version:1,text:'öx'}];d.scopes=[structuredClone(ps[0].scopes[0])];d.scopes[0].text='öx';d.groups=[{...ps[0].groups[0],contentVersion:1,layoutVersion:1}];
 const a=compare(ps,d);assert.ok(a.value);d.scopes[0].text='bad';assert.equal(a.value.scopes[0].text,'öx');assert.deepEqual(ps[0],saved);
 const p=counted.reviseProvenance(counted.beginProvenance(fixture()),empty(1));d.scopes[0].text='öx';globalThis.__revisionWork={entryScopes:0,semanticOperations:0,reusedScopes:0};counted.reviseProvenance(p,d);assert.deepEqual(globalThis.__revisionWork,{entryScopes:1,semanticOperations:1,reusedScopes:1});
});
test('changed group span invalidates an otherwise identical scope',()=>{const ps=pair(),d=empty(2);d.groups=[{...ps[0].groups[0],contentVersion:1,layoutVersion:1,spans:[{sourceId:'s',start:1,end:2}]}];assert.deepEqual(compare(ps,d).error,['Error','Leaf outside declared group origins']);assert.ok(compare(ps,empty(2)).value);});
test('external origin source changes require scope replacement and retain Unicode checks',()=>{const o=fixture();o.scopes[0].a262_originMode='explicit';o.scopes[0].operations[0].a262_origins=[{sourceId:'t',startByte:0,stopByte:1}];o.groups[0].spans.push({sourceId:'t',start:0,end:2});const ps=pair(o),d=empty(2);d.sources=[{id:'t',version:1,text:'öz'}];assert.deepEqual(compare(ps,d).error,['Error','Missing dependent scope replacement']);d.scopes=structuredClone(ps[0].scopes);d.scopes[1].text='öz';d.groups=ps[0].groups.map(g=>({...g,contentVersion:1,layoutVersion:1}));assert.ok(compare(ps,d).error);});
test('competing invalid changed scope and earlier retained-scope containment preserve error precedence',()=>{const ps=pair(),d=empty(2);d.groups=ps[0].groups.map(g=>({...g,contentVersion:1,layoutVersion:1}));d.groups[0].spans=[{sourceId:'s',start:1,end:2}];d.scopes=[structuredClone(ps[0].scopes[1])];d.scopes[0].operations[0].stop=99;assert.deepEqual(compare(ps,d).error,['Error','Byte offset outside source']);});
test('legacy structural certification never substitutes for semantic resource qualification',()=>{const o=fixture();o.scopes[1].operations[0].leaves[0].resources=['absent'];const ps=[candidate,baseline].map(m=>m.beginProvenance(o));for(let i=0;i<2;i++)assert.deepEqual(compare(ps,empty(1)).error,['Error','Invalid leaf resources']);for(const p of [structuredClone(pair()[0]),Object.freeze({...pair()[0]})])assert.throws(()=>candidate.reviseProvenance(p,empty(2)),/owner session/);});
console.log(JSON.stringify({passed:true,checks}));
