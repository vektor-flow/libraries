import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {beginProvenance,bindOperationFragment,bindOperationDocument} from '../latex_operation_binding.mjs';
import {createDocumentRenderSession} from '../document_render_session.mjs';
const schema=JSON.parse(readFileSync(new URL('./fixtures/schema.json',import.meta.url)));
// Structural witness from exact VKF declarations, NOT compiled producer output.
const arena=Object.fromEntries(schema.Arena.map(name=>[name,[]]));arena.count=0;
const document=Object.fromEntries(schema.PageDocument.map(name=>[name,[]]));
Object.assign(document,{arena,page_count:0,destination_count:0});
const owner=beginProvenance({documentId:'explicit-test-owner',revision:0,sources:[],scopes:[],groups:[],resources:[]});
const checks=[];
function rejects(name,fn,re){assert.throws(fn,re);checks.push({name,pass:true});}
rejects('B346 Arena lacks A operation provenance, even empty document',()=>bindOperationDocument({document,complete:true},owner),/Missing provenance column a260_scopes/);
rejects('Same sealed Arena cannot silently become an A Fragment',()=>bindOperationFragment({scene:{arena},complete:true},owner),/Missing provenance column a260_scopes/);
rejects('Incomplete producer stays rejected',()=>bindOperationDocument({document,complete:false},owner),/Incomplete layout/);
const device=new Proxy({lost:new Promise(()=>{})}, {get(target,key){if(key==='lost')return target.lost;throw Error('Unexpected device operation '+String(key));}});
const session=createDocumentRenderSession({device,pipeline:{}});
rejects('Native diagnostic strings are not host arrays',()=>session.update({document,complete:true,diagnostics:'',unresolved_json:'[]'}),/Incomplete producer result/);
rejects('Missing unresolved array cannot be assumed clean',()=>session.update({document,complete:true,diagnostics:[]}),/Incomplete producer result/);
await session.dispose();
console.log(JSON.stringify({passed:true,checks:checks.map(c=>c.name),synthetic_only:true}));
