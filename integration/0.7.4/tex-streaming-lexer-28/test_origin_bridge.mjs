import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {createPackageSourceBundle} from '../../../examples/gpu-math/native-vkf/host/latex_package_sources.mjs';
import {mouthOriginTable,acceptMouthOrigin} from './candidate/examples/gpu-math/native-vkf/host/latex_mouth_origins.mjs';
let checks = 0;
const ok = (value) => {assert.ok(value); checks++;};
const eq = (a,b) => {assert.deepEqual(a,b); checks++;};
const bad = (f,pattern) => {assert.throws(f,pattern); checks++;};
const file = (id,text) => {const bytes=Buffer.from(text);return {id,bytes,kind:'include',version:0,sha256:createHash('sha256').update(bytes).digest('hex')};};
const bundle=createPackageSourceBundle({files:[file('main','\\input{p} a'),file('p','x\r\nα')],engineIdentity:'mouth/ascii-1',initialStateIdentity:'test'});
const context=bundle.context();const main=context.enter('main');const include=context.origin(main,0,9,'include');
const one=context.enter('p',include);const two=context.enter('p',include);const occurrences=[main,one,two];
const definition=context.origin(one,0,1,'definition');const call=context.origin(main,10,11,'invocation',{definition});
const initial=mouthOriginTable(context);
eq(initial.occurrence_sources,[0,1,1]);eq(initial.occurrence_via,[-1,0,0]);eq(initial.role,['include','definition','invocation']);
eq(initial.definition,[-1,-1,1]);ok(Object.isFrozen(initial.start));
function result(before,occurrence,start,stop,provenance=0) {
 const source=occurrences[occurrence].source;const after=structuredClone(before);const origin=stop>start?before.source.length:-1;
 if (origin>=0) for (const [key,value] of Object.entries({source,occurrence,start,stop,role:'literal',definition:-1,invocation:-1}))after[key].push(value);
 return {state:{revision:before.revision,source,occurrence},token:{kind:1,category:11,value:'x',source,occurrence,start,stop,origin,provenance},diagnostic:0,origins:after};
}
const first=result(initial,1,0,1);const issued=acceptMouthOrigin(context,occurrences,bundle.sourceTable,initial,first);
eq(issued.occurrence,1);eq(context.exportOrigins().origins[3],issued);eq(mouthOriginTable(context),first.origins);
bad(()=>acceptMouthOrigin(context,occurrences,bundle.sourceTable,initial,first),/Stale/);
let before=mouthOriginTable(context);const repeat=result(before,2,0,1);acceptMouthOrigin(context,occurrences,bundle.sourceTable,before,repeat);
eq(context.exportOrigins().origins[4].occurrence,2);
before=mouthOriginTable(context);
for (const [field,value,pattern] of [['origin',99,/ID/],['provenance',2,/PREVIEW/],['source',0,/occurrence/],['stop',-1,/span/]]) {
 const malformed=result(before,1,0,1);malformed.token[field]=value;
 bad(()=>acceptMouthOrigin(context,occurrences,bundle.sourceTable,before,malformed),pattern);eq(mouthOriginTable(context),before);
}
const forged=result(before,1,0,1);forged.origins.role[0]='literal';bad(()=>acceptMouthOrigin(context,occurrences,bundle.sourceTable,before,forged),/suffix/);
bad(()=>acceptMouthOrigin(context,[...occurrences.map(x=>({...x}))],bundle.sourceTable,before,result(before,1,0,1)),/Foreign/);
const split=result(before,1,3,4);bad(()=>acceptMouthOrigin(context,occurrences,bundle.sourceTable,before,split),/split UTF-8/);eq(mouthOriginTable(context),before);
const virtual=result(before,1,5,5,1);eq(acceptMouthOrigin(context,occurrences,bundle.sourceTable,before,virtual),null);eq(mouthOriginTable(context),before);
const beyond=result(before,1,6,6,1);bad(()=>acceptMouthOrigin(context,occurrences,bundle.sourceTable,before,beyond),/source span/);
const zero=result(before,1,1,1,0);bad(()=>acceptMouthOrigin(context,occurrences,bundle.sourceTable,before,zero),/Zero-width/);
const diagnostic={...virtual,diagnostic:2,token:{...virtual.token,kind:0,provenance:0}};
eq(acceptMouthOrigin(context,occurrences,bundle.sourceTable,before,diagnostic),null);
const manifest=JSON.parse(readFileSync(new URL('./installed-sources.json',import.meta.url)));
for(const row of manifest.files){const bytes=readFileSync(row.path);eq(createHash('sha256').update(bytes).digest('hex'),row.sha256);
 const b=createPackageSourceBundle({files:[{id:row.id,bytes,sha256:row.sha256,kind:'package',version:0}],engineIdentity:'mouth/ascii-1',initialStateIdentity:'first-boundary'});
 const c=b.context();const o=c.enter(row.id);const origin=c.origin(o,row.first_boundary.startByte,row.first_boundary.stopByte);
 eq(c.textAt(origin),row.first_boundary.text);eq(mouthOriginTable(c).source,[0]);eq(mouthOriginTable(c).start,[row.first_boundary.startByte]);}
console.log(JSON.stringify({assertions:checks,passed:true,native_executed:false,parser:'none; transport adapter only'}));
// Actual-source native preparation uses byte-identical full inputs in memory;
// it does not write source packages or execute the native entry.
const {prepareInstalledNative}=await import('./prepare_installed_native.mjs');
const prepared=prepareInstalledNative();
for(const call of prepared.calls){const [table,trace,occurrence,name,start,stop]=call.args;
 eq(table.revision,trace.revision);eq(table.ids[trace.occurrence_sources[occurrence]],call.sourceId);
 eq(Buffer.from(table.texts[trace.occurrence_sources[occurrence]]).subarray(start,stop).toString(),'\\'+name);
 eq(call.executed,false);}
console.log(JSON.stringify({total_assertions:checks,passed:true,native_prepared_calls:prepared.calls.length,native_executed:false}));
