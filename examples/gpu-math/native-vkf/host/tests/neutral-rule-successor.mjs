import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {beginProvenance} from '../latex_operation_binding.mjs';
import {prepareProducerDocument} from '../document_producer_adapter.mjs';
import {createDocumentRenderSession} from '../document_render_session.mjs';
import {createRetainedSceneBridge} from '../document_resource_bridge.mjs';
const schema=JSON.parse(readFileSync(new URL('./fixtures/schema314.json',import.meta.url)));
const checks=[];
function test(name,fn){fn();checks.push(name);}
const span={sourceId:'source',start:0,end:1};
function owner(revision=0){return beginProvenance({documentId:'document',revision,sources:[{id:'source',version:0,text:'x'}],scopes:[{id:'parse',sourceId:'source',text:'x',baseByte:0,operations:[{operation:0,start:0,stop:1,groupId:'group',leaves:[{part:0,id:'leaf',resources:[]}]}]}],groups:[{id:'group',contentVersion:0,layoutVersion:0,contentKey:'text-x',layoutKey:'rule-x',edges:[],spans:[span]}],resources:[]});}
function fixture(){
 const a=Object.fromEntries(schema.Arena.map(k=>[k,[]]));
 Object.assign(a,{count:1,keys:[''],kinds:[2],xs:[1],ys:[2],sxs:[1],sys:[1],widths:[3],heights:[4],draws:[true],paints:[-1],payloads:[-1],paint_table:[],payload_table:[],paint_count:0,payload_count:0,a260_scopes:['parse'],a260_texts:['x'],a260_operations:[0],a260_starts:[0],a260_stops:[1],a260_parts:[0]});
 const d=Object.fromEntries(schema.PageDocument.map(k=>[k,[]]));Object.assign(d,{arena:a,page_count:1,destination_count:0,firsts:[0],counts:[1],widths:[100],heights:[100]});
 return {document:d,complete:true,diagnostics:'',unresolved_json:'[]'};
}

import {sceneColumns} from '../document_scene_bridge.mjs';
import {createDocumentTextureConsumer} from '../document_texture_consumer.mjs';
function backend(){
 let lose;
 const d={samplers:[],binds:[],textures:[],buffers:[],commands:[],gates:[],auto:true,writes:0,lost:new Promise(r=>lose=r),lose(){lose();},pushErrorScope(){},async popErrorScope(){return null;},
 createTexture(desc){const t={desc,destroyed:0,destroy(){this.destroyed++;},createView(){return {texture:this};}};d.textures.push(t);return t;},
 createBuffer(desc){const b={desc,destroyed:0,destroy(){this.destroyed++;}};d.buffers.push(b);return b;},
 createSampler(x){d.samplers.push(x);return x;},createBindGroup(x){d.binds.push(x);return x;},
 createCommandEncoder(){const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(i,b){c.buffer=b;},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){return c;}};d.commands.push(c);return c;},
 queue:{writeTexture({texture},raw){d.writes++;texture.bytes=raw.slice();},writeBuffer(b,o,raw){d.bufferWrites=(d.bufferWrites??0)+1;b.bytes=raw.slice();},submit(){d.submits=(d.submits??0)+1;},onSubmittedWorkDone(){return d.auto?Promise.resolve():new Promise(r=>d.gates.push(r));}},flush(){for(const r of d.gates.splice(0))r();}};return d;
}

globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};

const view={canvas:{width:100,height:100},context:{getCurrentTexture(){return {createView(){return {};}};}},scale:1};
const tick=()=>new Promise(r=>setImmediate(r));
function prepared(kind=2,revision=0,mixed=false){
 const f=fixture(),o=structuredClone(owner(revision)),a=f.document.arena;
 a.kinds=[kind];let tiles=new Map(),resources=[];
 if(kind===3){o.scopes[0].operations[0].leaves[0].link='https://example.test';a.payloads=[0];a.payload_count=1;a.payload_table=[{target:'https://example.test',border_width:1}];}
 if(mixed){
  for(const k of schema.Arena)if(Array.isArray(a[k])&&a[k].length===1&&!['paint_table','payload_table'].includes(k))a[k].push(a[k][0]);
  a.count=2;a.kinds=[0,2];a.keys=['tile',''];a.a260_parts=[0,1];f.document.counts=[2];
  o.scopes[0].operations[0].leaves=[{part:0,id:'glyph',resources:['font']},{part:1,id:'rule',resources:[]}];
  o.resources=[{id:'font',version:0,binding:'owner'}];
  tiles.set('tile',{resourceId:'font',plane:new Float64Array([0,0,1,1]),uv:new Float64Array([0,0,1,1])});
  resources=[{id:'font',version:0,bytes:new Uint8Array([10,20,30,255]),image:{format:'rgba8unorm',alphaMode:'straight',width:1,height:1,bytesPerRow:4}}];
 }
 return prepareProducerDocument(f,beginProvenance(o),{tiles,resources}).update;
}
function setup(){const d=backend(),s=createDocumentRenderSession({device:d,pipeline:{getBindGroupLayout(){return {};}}});return {d,s};}
function cleaned(d){assert.ok(d.textures.every(t=>t.destroyed===1));assert.ok(d.buffers.every(b=>b.destroyed===1));}
for(const [kind,name] of [[2,'rule'],[3,'link']]){
 const {d,s}=setup(),u=prepared(kind);assert.equal(u.resources.length,0);assert.equal(u.metadata.resources.length,0);
 await s.update(u);const receipt=await s.render(view);await receipt.completion;
 assert.equal(d.submits,1);assert.equal(d.commands[0].draws.length,1);assert.equal(d.buffers[0].bytes[12],1);
 assert.deepEqual(d.textures[0].desc,{size:[1,1],format:'rgba8unorm',usage:6});assert.deepEqual([...d.textures[0].bytes],[255,255,255,255]);
 assert.equal(d.binds[0].entries[1].resource.texture,d.textures[0]);assert.equal(d.binds[0].entries[0].resource.buffer,d.buffers[1]);
 await s.dispose();cleaned(d);checks.push(name+' zero producer resources encodes submits completes and cleans once');
}
{
 const {d,s}=setup();await s.update(prepared(2,0,true));const r=await s.render(view);await r.completion;
 const calls=d.commands[0].draws;assert.deepEqual(calls.map(c=>c.args),[[6,1,0,0],[6,1,0,1]]);
 assert.deepEqual(calls.map(c=>[...c.bind.entries[1].resource.texture.bytes]),[[10,20,30,255],[255,255,255,255]]);
 assert.ok(d.samplers.every(x=>x.minFilter==='linear'&&x.magFilter==='linear'));
 assert.equal(calls[0].bind.entries[0].resource.buffer,calls[1].bind.entries[0].resource.buffer);
 await s.dispose();cleaned(d);checks.push('mixed glyph and rule keep order explicit pixels linear filters and per-draw uniform');
}
{
 const {d,s}=setup();await s.update(prepared());d.auto=false;const r=await s.render(view);await tick();
 const oldFence=d.gates.shift();d.auto=true;await s.update(prepared(2,1));assert.equal(d.textures.length,1);assert.equal(d.writes,1);
 const next=await s.render(view);await next.completion;const disposal=s.dispose();await tick();assert.equal(d.textures[0].destroyed,0);
 oldFence();await r.completion;await disposal;cleaned(d);checks.push('replacement shares neutral and pending old frame retains it through disposal');
}
for(const mode of ['cancel','dispose','write-error','loss','sync-fence','reject-fence']){
 const {d,s}=setup();d.auto=false;
 if(mode==='write-error'){d.queue.writeTexture=()=>{throw Error('neutral-write');};}
 if(mode==='sync-fence')d.queue.onSubmittedWorkDone=()=>{throw Error('neutral-fence');};
 if(mode==='reject-fence')d.queue.onSubmittedWorkDone=()=>Promise.reject(Error('neutral-fence'));
 const update=s.update(prepared());const rejected=assert.rejects(update);await tick();
 if(mode==='cancel')s.cancel();
 const terminal=['loss','sync-fence','reject-fence'].includes(mode);
 let disposal;if(mode==='dispose')disposal=s.dispose();
 if(mode==='loss')d.lose();
 if(!terminal){assert.equal(d.textures[0].destroyed,0);d.flush();}
 await rejected;await (disposal??s.dispose());
 if(terminal){assert.ok(d.textures.every(t=>t.destroyed===0));assert.ok(d.buffers.every(b=>b.destroyed===0));}else cleaned(d);
 assert.equal(s.metrics.liveSnapshots,0);checks.push('neutral upload '+mode+' observes fence and retires exactly once or terminal CPU-only');
}
console.log(JSON.stringify({passed:true,checks,synthetic_only:true}));
