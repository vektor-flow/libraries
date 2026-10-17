import assert from 'node:assert/strict';
import * as candidate from '../latex_source_binding.mjs';
import * as oracle from './origin-lookup-oracle/latex_source_binding.mjs';
const checks=[];
const span=(start,end,sourceId='s')=>({sourceId,start,end});
function fixture(spans=[span(0,8)],leaves=[span(0,1)]){return {owner:{documentId:'d',revision:0,leafIds:['a'],groups:[{id:'g',first:0,count:1,contentVersion:0,layoutVersion:0,contentKey:'k',layoutKey:'k',edges:[]}],resources:[],leafResources:[[]],links:[]},provenance:{offsetUnit:'utf16',sources:[{id:'s',version:0,text:'abcdefgh'},{id:'t',version:0,text:'abcdefgh'}],groups:[{id:'g',spans}],leaves:[{id:'a',spans:leaves}]}};}
const padded=spans=>[...spans,...Array.from({length:20},()=>span(8,8,'t'))];
const fragment={complete:true,scene:{arena:{count:1}}},document={complete:true,document:{arena:{count:1},page_count:2,firsts:[0,0],counts:[0,1]}};
for(const [name,result] of [['Fragment',fragment],['Document',document]]){
 const fn='bindSource'+name;
 function pair(f,expected,previous=null){
  const invoke=m=>{try{return {value:m[fn](result,structuredClone(f.owner),structuredClone(f.provenance),previous)};}catch(e){return {error:e.message};}};
  const a=invoke(candidate),b=invoke(oracle);assert.deepEqual(a,b);if(expected)assert.equal(a.error,expected);return a.value;
 }
 for(const n of [1,16,17,40]){
  const f=fixture(Array.from({length:n},(_,i)=>span(i%8,i%8+1)),[span(0,1),span(1,1)]);
  pair(f);pair(fixture(f.provenance.groups[0].spans,[span(0,2)]),'Leaf outside declared group origins');
 }
 pair(fixture(padded([span(4,8),span(0,5),span(0,5),span(3,7)]),[span(2,5),span(4,8),span(8,8)]));
 pair(fixture(padded([span(0,4),span(4,8)]),[span(3,5)]),'Leaf outside declared group origins');
 pair(fixture(padded([span(0,4),span(2,8)]),[span(1,7)]),'Leaf outside declared group origins');
 pair(fixture(padded([span(0,4),span(2,8)]),[span(2,7)]));
 pair(fixture(padded([span(0,4)]),[span(4,5,'t')]),'Leaf outside declared group origins');
 pair(fixture(padded([span(0,4),span(4,5,'t')]),[span(4,5,'t')]));
 checks.push(name+' exact oracle containment for small/indexed unsorted duplicate overlapping adjacent zero-length and multiple-source spans');
 const invalid=fixture(padded([span(0,4)]),[span(5,6),span(-1,0)]);pair(invalid,'Invalid source span');
 const u=fixture(padded([span(0,4)]),[span(1,3)]);u.provenance.sources[0].text='a😀bcdef';pair(u);
 u.provenance.leaves[0].spans=[span(2,3)];pair(u,'Split Unicode scalar');
 u.provenance.groups[0].spans[0]=span(2,3);u.provenance.leaves[0].spans=[span(-1,0)];pair(u,'Split Unicode scalar');
 const bad=fixture(padded([span(0,4)]));bad.provenance.sources.push({...bad.provenance.sources[0]});pair(bad,'Duplicate source');
 const missing=fixture();missing.provenance.leaves=[];pair(missing,'Missing origin coverage');
 checks.push(name+' original invalid input and Unicode validation precede containment with exact error preservation');
 let seed=330;const rand=n=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;};
 for(let test=0;test<250;test++){
  const spans=Array.from({length:17+rand(60)},()=>{const a=rand(9),b=rand(9);return span(Math.min(a,b),Math.max(a,b),rand(2)?'s':'t');});
  const leaves=Array.from({length:1+rand(8)},()=>{const a=rand(9),b=rand(9);return span(Math.min(a,b),Math.max(a,b),rand(2)?'s':'t');});pair(fixture(spans,leaves));
 }
 checks.push(name+' 250 deterministic interval matrices equal independent frozen existential oracle');
 const f=fixture(padded([span(0,8)]));const before=pair(f);f.owner.revision=1;f.provenance.sources[0].text='zbcdefgh';f.provenance.sources[0].version=1;
 pair(f,'Source edit requires content/layout versions',before);f.owner.groups[0].contentVersion=1;f.owner.groups[0].layoutVersion=1;const after=pair(f,null,before);
 assert.equal(before.sourceBinding.sources[0].text,'abcdefgh');assert.equal(after.sourceBinding.sources[0].text,'zbcdefgh');assert(Object.isFrozen(after.sourceBinding.groups[0].spans));
 checks.push(name+' real edit version guards and retained frozen previous values unchanged');
}
console.log(JSON.stringify({passed:true,checks}));
