import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fixture} from './columns-fixture.mjs';
import {beginProvenance} from '../latex_operation_binding.mjs';
import {prepareProducerFragment as candidate} from '../fragment_producer_adapter.mjs';
import {prepareProducerFragment as oracle} from '../fragment_validation_oracle.mjs';
const schema=JSON.parse(readFileSync(new URL('./fixtures/fragment-schema.json',import.meta.url)));
function fresh(){
 const f=fixture(1),arena=f.result.document.arena;
 arena.destination_firsts=[0,0,0];arena.destination_counts=[0,0,0];
 f.owner.groups[2].edges=[];
 const scene=Object.fromEntries(schema.Scene.map(k=>[k,[]]));
 Object.assign(scene,{arena,anchor_count:0,anchor_metadata:{kinds:[],ends:[],texts:[],numbers:[],count:0},width:100,height:80,depth:20,tag_width:0,inline_destinations:false});
 f.result={scene,complete:true,diagnostics:'',pending_count:0,a272_anchor_origins:{scope:'parse',text:'x',ids:[],operations:[],starts:[],stops:[]},a277_anchor_placements:{scenes:[],scene_count:3},a280_anchor_receipts:{leaves:[],slots:[]},a282_point_receipts:{points:[]},a283_final_anchors:{leaves:[],slots:[],points:[]}};
 delete f.options.page;return f;
}

const checks=[],test=(name,fn)=>{fn();checks.push(name);};
function outcome(fn,edit){const f=fresh(),trace=[];edit(f,trace);try{const v=fn(f.result,beginProvenance(f.owner),f.options);return {ok:true,extent:v.extent,update:v.update,metadata:v.bound.metadata,trace};}catch(e){return {ok:false,name:e.name,message:e.message,trace};}}
function same(edit,expected){const a=outcome(oracle,edit),b=outcome(candidate,edit);assert.deepEqual(b,a);if(expected)assert.match(b.message,expected);return b;}
test('finite numeric columns preserve signed extents errors and independent values',()=>{
 assert.equal(same(()=>{}).ok,true);
 for(const k of ['xs','ys','sxs','sys','widths','heights']){
  for(const v of [NaN,Infinity,-Infinity,'0',undefined,null])same(f=>f.result.scene.arena[k][0]=v,new RegExp('Invalid column type '+k));
  for(const v of [-1,-0,0,2.5]){const r=same(f=>f.result.scene.arena[k][0]=v);if((k==='widths'||k==='heights')&&v<0)assert.equal(r.message,'Invalid column type '+k);else if(r.ok)assert(Object.is(r.update.scene.arena[k][0],v));}
 }
});
test('numeric accessors keep double reads sparse arrays typed views and error precedence',()=>{
 for(const k of ['xs','widths'])same((f,t)=>{const a=f.result.scene.arena;let reads=0;Object.defineProperty(a[k],0,{enumerable:true,get(){t.push(k+':'+(++reads));return reads===1?1:2;}});});
 same(f=>{delete f.result.scene.arena.xs[1];},/Invalid column type xs/);
 same(f=>{const a=f.result.scene.arena;for(const k of ['xs','ys','sxs','sys','widths','heights'])a[k]=new Float64Array(a[k]);});
 same(f=>{f.result.scene.arena.xs[0]=NaN;f.result.scene.arena.widths[0]=-1;},/Invalid column type xs/);
});
test('destination fallback preserves custom iterator full consumption and exception precedence',()=>{
 for(const mode of ['zeros','nonzero','throw'])same((f,t)=>{const a=f.result.scene.arena;a.destination_firsts[Symbol.iterator]=function*(){t.push('first');yield mode==='nonzero'?1:0;t.push('second');if(mode==='throw')throw Error('iterator failure');yield 0;t.push('third');yield 0;};});
 same((f,t)=>{const a=f.result.scene.arena;a.destination_firsts[Symbol.iterator]=function*(){t.push('nonzero');yield 1;t.push('throw');throw Error('late iterator failure');};},/late iterator failure/);
 same((f,t)=>{const a=f.result.scene.arena;let reads=0;const value=a.destination_firsts;Object.defineProperty(a,'destination_firsts',{enumerable:true,get(){t.push('column'+(++reads));return value;}});});
});
test('destination sparse typed and invalid views retain exact independent rejection',()=>{
 same(f=>{delete f.result.scene.arena.destination_firsts[1];},/Unsupported fragment destinations/);
 same(f=>{const a=f.result.scene.arena;a.destination_firsts=new Uint32Array(3);a.destination_counts=new Float64Array(3);});
 same(f=>{f.result.scene.arena.destination_firsts=new DataView(new ArrayBuffer(12));},/Unsupported fragment destinations/);
 same(f=>{f.result.scene.arena.destination_firsts=[0,1,0];f.result.scene.arena.xs[0]=NaN;},/Unsupported fragment destinations/);
 same(f=>{f.result.scene.arena.destination_counts=new BigInt64Array(3);},/Unsupported fragment destinations/);
});
test('snapshot ownership stays independent of caller mutation',()=>{
 for(const fn of [oracle,candidate]){const f=fresh(),p=fn(f.result,beginProvenance(f.owner),f.options);f.result.scene.arena.xs[0]=42;assert.equal(p.update.scene.arena.xs[0],0);assert.equal(p.bound.scene.arena.xs[0],0);}
});
console.log(JSON.stringify({passed:true,checks,synthetic_only:true}));
