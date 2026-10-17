import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {beginProvenance} from '../latex_operation_binding.mjs';
import * as current from '../document_producer_adapter.mjs';
import * as baseline from './fixtures/e317-adapter.mjs';
const schema=JSON.parse(readFileSync(new URL('./fixtures/schema314.json',import.meta.url)));
const checks=[],measurements=[];
function test(name,fn){fn();checks.push(name);}
function fixture(pages,allEmpty=false){
 const a=Object.fromEntries(schema.Arena.map(k=>[k,[]]));Object.assign(a,{count:0,paint_count:0,payload_count:1,paint_table:[],payload_table:[{target:'https://example.test',border_width:1}]});
 const d=Object.fromEntries(schema.PageDocument.map(k=>[k,[]]));Object.assign(d,{arena:a,page_count:pages,destination_count:0});
 const o={documentId:'index-test',revision:0,sources:[{id:'s',version:0,text:'x'}],scopes:[{id:'parse',sourceId:'s',text:'x',baseByte:0,operations:[]}],groups:[],resources:[]};
 const tiles=new Map(),resources=[];
 for(let p=0;p<pages;p++){
  const count=allEmpty||pages>1&&p%3===0?0:3;d.firsts.push(a.count);d.counts.push(count);d.widths.push(100+p);d.heights.push(200+p);
  if(!count)continue;
  const rid='resource-'+p,key='glyph-'+p;
  o.resources.push({id:rid,version:0,binding:'binding-'+p});resources.unshift({id:rid,version:0,bytes:new Uint8Array([p,0,0,255]),image:{format:'rgba8unorm',alphaMode:'straight',width:1,height:1,bytesPerRow:4}});
  tiles.set(key,{resourceId:rid,plane:new Float64Array([0,0,1,1]),uv:new Float64Array([0,0,1,1])});
  for(let k=0;k<count;k++){
   const i=a.count++,kind=[0,2,3][k],g='group-'+i;
   const values={keys:k===0?key:'',kinds:kind,xs:i,ys:p,sxs:1,sys:1,widths:3,heights:4,draws:true,paints:-1,payloads:k===2?0:-1,a260_scopes:'parse',a260_texts:'x',a260_operations:i,a260_starts:0,a260_stops:1,a260_parts:0};
   for(const [key,value] of Object.entries(values))a[key].push(value);
   const leaf={part:0,id:'leaf-'+i,resources:[rid]};if(k===2)leaf.link='https://example.test';
   o.scopes[0].operations.push({operation:i,start:0,stop:1,groupId:g,leaves:[leaf]});
   o.groups.push({id:g,contentVersion:0,layoutVersion:0,contentKey:g,layoutKey:g,edges:i?[{kind:'flow',target:'group-'+(i-1)}]:[],spans:[{sourceId:'s',start:0,end:1}]});
  }
 }
 for(const op of o.scopes[0].operations)if(op.operation%3===1)op.leaves[0].resources=o.resources.map(r=>r.id);
 return {result:{document:d,complete:true,diagnostics:'',unresolved_json:'[]'},owner:o,options:{page:0,tiles,resources}};
}
function pair(f){const owner=beginProvenance(f.owner);return [current.prepareProducerDocument(f.result,owner,f.options),baseline.prepareProducerDocument(f.result,owner,f.options)];}
for(const pages of [1,10,40])test(`indexed ${pages} pages preserve E317 outputs and remove repeated mapping`,()=>{
 const f=fixture(pages),[a,b]=pair(f),initial=current.producerPageWork(a);
 assert.deepEqual(a,b);
 for(let round=0;round<3;round++)for(let page=0;page<pages;page++){
  const x=current.selectProducerPage(a,page),y=baseline.selectProducerPage(b,page);assert.deepEqual(x,y);
  // Every mutable output category remains independent of both input and cache.
  x.update.scene.arena.xs.fill(999);x.update.scene.arena.payload_table[0].target='mutated';
  x.update.metadata.groups.forEach(g=>{g.edges.length=0;g.count=999;});x.update.metadata.leafResources.forEach(r=>r.push('bad'));
  x.update.metadata.links.forEach(l=>l.target='bad');x.update.metadata.resources.forEach(r=>r.version=999);
  x.update.resources.forEach(r=>r.bytes.fill(255));for(const t of x.update.tiles.values())t.uv.fill(0.5);
  assert.deepEqual(current.selectProducerPage(a,page),y);
 }
 const after=current.producerPageWork(a);
 for(const key of Object.keys(initial).filter(k=>!['selections','projectedGroupCopies'].includes(k)))assert.equal(after[key],initial[key],key);
 assert.equal(initial.indexPages,pages);assert.equal(initial.indexLeaves,f.result.document.arena.count);
 assert.equal(initial.groupRangeChecks,f.owner.groups.length);
 assert.equal(after.projectedGroupCopies-initial.projectedGroupCopies,6*pages*f.owner.groups.length);
 measurements.push({pages,initial,after,repeatSelections:6*pages,repeatMappingOperations:0,fullGroupCopies:after.projectedGroupCopies-initial.projectedGroupCopies});
 f.result.document.firsts.fill(999);f.result.document.arena.xs.fill(888);f.options.resources.forEach(r=>r.bytes.fill(77));
 assert.deepEqual(current.selectProducerPage(a,pages-1),baseline.selectProducerPage(b,pages-1));
});
test('all empty pages retain exact boundary and empty outputs',()=>{const [a,b]=pair(fixture(10,true));for(let p=0;p<10;p++)assert.deepEqual(current.selectProducerPage(a,p),baseline.selectProducerPage(b,p));});
test('malformed off-page and cross-page input reject identically to E317',()=>{
 const edits=[f=>f.result.document.firsts[2]++,f=>f.result.document.arena.xs.at(-1),f=>f.result.document.arena.xs[f.result.document.arena.count-1]=NaN,f=>f.result.document.arena.a260_operations[f.result.document.arena.count-1]=999,f=>f.options.resources.pop(),f=>f.options.tiles.clear(),f=>f.result.document.arena.payload_table[0].target='bad',f=>f.result.document.widths[9]=0,f=>{const ops=f.owner.scopes[0].operations;ops[3].groupId=ops[2].groupId;}];
 edits.splice(1,1);
 for(const edit of edits){const f=fixture(10);edit(f);const owner=beginProvenance(f.owner);let old,newer;try{baseline.prepareProducerDocument(f.result,owner,f.options);}catch(e){old=e.message;}try{current.prepareProducerDocument(f.result,owner,f.options);}catch(e){newer=e.message;}assert.ok(old);assert.equal(newer,old);}
});
if(process.env.VKF_INDEX_COUNTERS)writeFileSync(process.env.VKF_INDEX_COUNTERS,JSON.stringify(measurements,null,2)+'\n');
console.log(JSON.stringify({passed:true,checks,synthetic_only:true}));
