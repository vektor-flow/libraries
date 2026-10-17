import assert from 'node:assert/strict';
import * as candidate from '../latex_source_binding.mjs';
import * as oracle from './source-slices-oracle/latex_source_binding.mjs';
const checks=[];
const span=(start,end,sourceId='s')=>({sourceId,start,end});
function fixture(){return {owner:{documentId:'d',revision:0,leafIds:['a','b'],groups:[{id:'g',first:0,count:2,contentVersion:0,layoutVersion:0,contentKey:'k',layoutKey:'k',edges:[]},{id:'empty',first:2,count:0,contentVersion:0,layoutVersion:0,contentKey:'e',layoutKey:'e',edges:[]}],resources:[],leafResources:[[],[]],links:[]},provenance:{offsetUnit:'utf16',sources:[{id:'s',version:0,text:'α😀z'},{id:'macro',version:0,text:'μ'}],groups:[{id:'g',spans:[span(0,4),span(0,1,'macro')]},{id:'empty',spans:[span(4,4)]}],leaves:[{id:'a',spans:[span(0,3),span(0,1,'macro')]},{id:'b',spans:[span(1,4)]}]}};}
const fragment={complete:true,scene:{arena:{count:2}}},document={complete:true,document:{arena:{count:2},page_count:3,firsts:[0,1,1],counts:[1,0,1]}};
for(const [name,result] of [['Fragment',fragment],['Document',document]]){
 const fn='bindSource'+name;
 function pair(make,expected,prev=null){const f=make(),g=make();let a,b;
  if(expected){assert.throws(()=>candidate[fn](result,f.owner,f.provenance,prev?.[0]),e=>e.message===expected);assert.throws(()=>oracle[fn](result,g.owner,g.provenance,prev?.[1]),e=>e.message===expected);return;}
  a=candidate[fn](result,f.owner,f.provenance,prev?.[0]);b=oracle[fn](result,g.owner,g.provenance,prev?.[1]);assert.deepEqual(a,b);assert.equal(name==='Fragment'?a.scene:a.document,name==='Fragment'?result.scene:result.document);return [a,b];
 }
 const old=pair(fixture);assert.deepEqual(old[0].sourceBinding,fixture().provenance);assert(Object.isFrozen(old[0].metadata.leafIds));
 checks.push(name+' exact frozen oracle: Unicode multiple overlapping origins and empty group/page');
 pair(()=>{const f=fixture();f.owner.groups[1].first=1;f.owner.groups[1].count=1;return f;},'Overlapping groups');
 pair(()=>{const f=fixture();f.provenance.leaves[0].spans=[span(2,3)];return f;},'Split Unicode scalar');
 pair(()=>{const f=fixture();f.provenance.groups[0].spans=[span(0,1)];return f;},'Leaf outside declared group origins');
 checks.push(name+' exact overlap Unicode containment rejection precedence');
 const edited=()=>{const f=fixture();f.owner.revision=1;f.provenance.sources[0].version=1;f.provenance.sources[0].text='β😀z';f.owner.groups[0].contentVersion=1;f.owner.groups[0].layoutVersion=1;return f;};
 const next=pair(edited,null,old);assert.deepEqual(next[0].invalidated,['g']);assert.equal(old[0].sourceBinding.sources[0].text,'α😀z');
 pair(()=>{const f=edited();f.provenance.sources[0].version=0;return f;},'Source changed without version',old);
 pair(()=>{const f=edited();f.owner.groups[0].contentVersion=0;f.owner.groups[0].layoutVersion=0;return f;},'Source edit requires content/layout versions',old);
 pair(()=>{const f=fixture();f.owner.revision=1;f.provenance.leaves[0].spans=[span(1,3),span(0,1,'macro')];return f;},'Leaf origin edit requires content/layout versions',old);
 checks.push(name+' source and leaf version rejection with successful real text revision');
 const branch=pair(()=>{const f=edited();f.provenance.sources[0].text='γ😀z';return f;},null,old);assert.equal(next[0].sourceBinding.sources[0].text,'β😀z');assert.equal(branch[0].sourceBinding.sources[0].text,'γ😀z');assert.equal(old[0].sourceBinding.sources[0].text,'α😀z');
 checks.push(name+' failed revisions and sibling branches preserve old source binding');
 const unusual=pair(()=>{const f=fixture();let reads=0;Object.defineProperty(f.owner.groups[0],'first',{get(){return ++reads<8?0:-1;}});return f;});assert.equal(unusual[0].metadata.groups[0].first,-1);
 checks.push(name+' unusual getter stored range retains original slice clamping');
}
console.log(JSON.stringify({passed:true,checks}));
