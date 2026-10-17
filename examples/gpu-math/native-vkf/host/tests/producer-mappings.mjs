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
 const d={samplers:[],binds:[],textures:[],buffers:[],commands:[],gates:[],auto:true,writes:0,lost:new Promise(()=>{}),pushErrorScope(){},async popErrorScope(){return null;},
 createTexture(){const t={destroyed:0,destroy(){this.destroyed++;},createView(){return {texture:this};}};d.textures.push(t);return t;},
 createBuffer(desc){const b={desc,destroyed:0,destroy(){this.destroyed++;}};d.buffers.push(b);return b;},
 createSampler(x){d.samplers.push(x);return x;},createBindGroup(x){d.binds.push(x);return x;},
 createCommandEncoder(){const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(i,b){c.buffer=b;},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){return c;}};d.commands.push(c);return c;},
 queue:{writeTexture({texture},raw){d.writes++;texture.bytes=raw.slice();},writeBuffer(b,o,raw){d.bufferWrites=(d.bufferWrites??0)+1;b.bytes=raw.slice();},submit(){},onSubmittedWorkDone(){return d.auto?Promise.resolve():new Promise(r=>d.gates.push(r));}},flush(){for(const r of d.gates.splice(0))r();}};return d;
}

globalThis.GPUTextureUsage={TEXTURE_BINDING:4,COPY_DST:2};globalThis.GPUBufferUsage={VERTEX:32,COPY_DST:8,UNIFORM:64};
for(const [kind,name,tag] of [[0,'glyph',0],[1,'field',0],[2,'rule',1],[3,'link',1]]){
 const f=fixture(),o=structuredClone(owner()),a=f.document.arena; a.kinds=[kind];
 let tiles=new Map(),resources=[];
 if(kind<2){a.keys=['tile'];o.resources=[{id:'font',version:0,binding:'owner'}];o.scopes[0].operations[0].leaves[0].resources=['font'];tiles.set('tile',{resourceId:'font',plane:new Float64Array([0,0,1,1]),uv:new Float64Array([0,0,1,1])});resources=[{id:'font',version:0,bytes:new Uint8Array([255,255,255,255]),image:{format:'rgba8unorm',alphaMode:'straight',width:1,height:1,bytesPerRow:4}}];}
 if(kind===3){o.scopes[0].operations[0].leaves[0].link='https://example.test';a.payloads=[0];a.payload_count=1;a.payload_table=[{target:'https://example.test',border_width:1}];}
 const {update:u}=prepareProducerDocument(f,beginProvenance(o),{tiles,resources});
 const p=sceneColumns(u.scene,u.metadata,u.tiles);assert.equal(p.columns[12][0],tag);
 const b=createRetainedSceneBridge(),lease=b.commitScene(u.scene,u.metadata,u.tiles,u.resources);
 const d=backend(),c=createDocumentTextureConsumer({device:d,pipeline:{getBindGroupLayout(){return {};}}});await c.replace(lease);
 const vertex=d.buffers.find(x=>x.desc.usage & 32);assert.equal(vertex.bytes[12],tag);
 const view={canvas:{width:100,height:100},context:{getCurrentTexture(){return {createView(){return {};}};}},scale:1,defaultResourceId:'font'};
 if(kind<2){await c.encodePage(view).submit();assert.equal(d.commands[0].draws.length,1);}else{assert.throws(()=>c.encodePage(view),/Missing explicit draw resource/);}
 assert.equal(d.textures.length,kind<2?1:0);
 c.dispose();await c.drained();b.dispose();await b.drained();checks.push(name+' maps to consumer tag '+tag+(kind<2?' with explicit ownership':' but resource-free encode is blocked'));
}
console.log(JSON.stringify({passed:true,checks,synthetic_only:true}));
