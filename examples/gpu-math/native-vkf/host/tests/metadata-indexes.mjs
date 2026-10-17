import assert from 'node:assert/strict';
import * as candidate from '../latex_metadata.mjs';
import * as oracle from './metadata-oracle/latex_metadata.mjs';
const checks=[],test=(name,fn)=>{fn();checks.push(name);};
function owner(revision=0){return {documentId:'d',revision,leafIds:['a','b','c'],groups:[{id:'g',first:0,count:3,contentVersion:0,layoutVersion:0,contentKey:'c',layoutKey:'l',edges:[]},{id:'empty',first:3,count:0,contentVersion:0,layoutVersion:0,contentKey:'e',layoutKey:'e',edges:[]}],resources:[{id:'x',version:0,binding:'bx'},{id:'y',version:0,binding:'by'}],leafResources:[['y','x'],[],['x']],links:[{leaf:2,target:'z'},{leaf:0,target:'a'},{leaf:0,target:'a'},{leaf:0,target:'b'}]};}
function compare(change=()=>{},trusted=true){const values=[],traces=[];for(const api of [oracle,candidate]){let p=api.bindMetadata(3,owner()).metadata;if(!trusted)p=structuredClone(p);const o=owner(1),trace=[];change(o,p,trace);try{values.push({value:api.bindMetadata(3,o,p)});}catch(e){values.push({error:[e.name,e.message]});}traces.push(trace);}assert.deepEqual(values[1],values[0]);assert.deepEqual(traces[1],traces[0]);return values[1];}
test('trusted metadata eager signatures preserve links order duplicates resources and empty groups',()=>{
 assert.deepEqual(compare().value.invalidated,[]);
 for(const change of [o=>o.links.reverse(),o=>o.links.splice(2,1),o=>o.leafResources[0].reverse(),o=>{o.resources[1].version++;o.resources[1].binding='new';}]){assert.ok(compare(change).error);assert.deepEqual(compare(o=>{change(o);o.groups[0].layoutVersion++;}).value.invalidated,['g']);}
 compare(o=>o.links.push({leaf:1,target:'extra'}));
});
test('untrusted previous preserves first resource match sparse malformed and missing resource errors',()=>{
 for(const mutate of [p=>p.resources.push({...p.resources[0],binding:'duplicate'}),p=>p.resources.reverse(),p=>p.resources.splice(0,1),p=>delete p.resources[0],p=>p.resources[0]=null,p=>delete p.links[0],p=>p.links[0]=null,p=>delete p.leafResources[0],p=>p.leafResources[0]=null,p=>p.groups[0]=null,p=>p.groups[0].count=0])compare((o,p)=>mutate(p),false);
});
test('getter traces and signature short circuit retain exact legacy observations',()=>{
 for(const key of ['resources','links','leafResources','leafIds'])compare((o,p,t)=>{const v=p[key];Object.defineProperty(p,key,{get(){t.push(key);return v;}});},false);
 compare((o,p,t)=>{Object.defineProperty(p.links[0],'leaf',{get(){t.push('leaf');return 2;}});Object.defineProperty(p.resources[0],'id',{get(){t.push('id');return 'x';}});},false);
 compare((o,p,t)=>{o.groups[0].contentVersion++;o.groups[0].layoutVersion++;Object.defineProperty(p,'links',{get(){t.push('unexpected links');throw Error('links');}});},false);
 compare((o,p,t)=>{p.links=[{get leaf(){t.push('badleaf');throw Error('badleaf');}}];p.leafResources[0]=['missing'];},false);
});
test('binding graph revision and group failure precedence matches frozen metadata oracle',()=>{
 for(const change of [o=>{o.resources[0].binding='rebound';o.groups[0].contentVersion=-1;},o=>{o.resources[0].binding='rebound';o.groups[0].layoutVersion=1;},o=>{o.groups[0].edges=[{kind:'flow',target:'missing'}];o.revision=0;},o=>{o.revision=0;o.links[0].leaf=99;},o=>{o.groups[0].contentKey='changed';o.links.reverse();},o=>{o.groups[0].edges=[{kind:'flow',target:'empty'}];}])compare(change);
});
test('issued sparse links and unusual normalized owner keys keep oracle behavior',()=>{
 for(const api of [oracle,candidate]){const o=owner();delete o.links[1];const p=api.bindMetadata(3,o).metadata;o.revision++;assert.deepEqual(api.bindMetadata(3,o,p).invalidated,[]);}
 const outcomes=[];for(const api of [oracle,candidate]){const o=owner();let n=0;Object.defineProperty(o.links[0],'leaf',{get(){return ++n<=2?2:NaN;}});const p=api.bindMetadata(3,o).metadata;try{outcomes.push(api.bindMetadata(3,owner(1),p));}catch(e){outcomes.push([e.name,e.message]);}}assert.deepEqual(outcomes[1],outcomes[0]);
});
console.log(JSON.stringify({passed:true,checks}));
