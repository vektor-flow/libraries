// Hand-constructed ABI transport inputs. These are NOT native lexer results.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createPackageSourceBundle} from '../../../examples/gpu-math/native-vkf/host/latex_package_sources.mjs';
import {mouthOriginTable,acceptMouthOrigin} from './candidate/examples/gpu-math/native-vkf/host/latex_mouth_origins.mjs';
let checks=0;
const eq=(a,b)=>{assert.deepEqual(a,b);checks++;};
const bad=(f,re)=>{assert.throws(f,re);checks++;};
function fixture(text) {
 const bytes=Buffer.from(text);
 const bundle=createPackageSourceBundle({files:[{id:'review',version:0,kind:'include',bytes,sha256:createHash('sha256').update(bytes).digest('hex')}],engineIdentity:'vkf.tex.mouth/ascii-1',initialStateIdentity:'review-only'});
 const context=bundle.context(),occurrence=context.enter('review');
 return {bundle,context,occurrence};
}
function tokenResult(before,kind,category,value,start,stop,provenance) {
 const source=0,occurrence=0,origin=stop>start?before.source.length:-1;
 const after=structuredClone(before);
 if(origin>=0) for(const [k,v] of Object.entries({source,occurrence,start,stop,role:'literal',definition:-1,invocation:-1}))after[k].push(v);
 return {state:{revision:before.revision,source,occurrence},origins:after,diagnostic:0,token:{kind,category,value,source,occurrence,start,stop,provenance,origin}};
}
for(const [raw,k,c,value,a,b] of [['a ',1,10,' ',1,2],[' ',2,-1,'par',0,1],['\\',2,-1,'\r',0,1],['\\ ',2,-1,'\r',0,2]]) {
 const {bundle,context,occurrence}=fixture(raw),before=mouthOriginTable(context);
 const result=tokenResult(before,k,c,value,a,b,1);
 const origin=acceptMouthOrigin(context,[occurrence],bundle.sourceTable,before,result);
 eq(context.textAt(origin),raw.slice(a,b));eq(result.token.provenance,1);
 eq(context.exportOrigins().origins.length,1);
 // Raw source anchor can differ from generated control spelling; preserve token.
 const current=mouthOriginTable(context),preview=tokenResult(current,k,c,value,a,b,2);
 bad(()=>acceptMouthOrigin(context,[occurrence],bundle.sourceTable,current,preview),/PREVIEW/);
 eq(mouthOriginTable(context),current);
}
const {bundle,context,occurrence}=fixture('a');
const before=mouthOriginTable(context),virtual=tokenResult(before,1,10,' ',1,1,1);
eq(acceptMouthOrigin(context,[occurrence],bundle.sourceTable,before,virtual),null);
eq(mouthOriginTable(context),before);
bad(()=>acceptMouthOrigin(context,[occurrence],bundle.sourceTable,before,{...virtual,token:{...virtual.token,provenance:0}}),/Zero-width/);
eq(mouthOriginTable(context),before);
console.log(JSON.stringify({assertions:checks,passed:true,native_executed:false,scope:'actual JS adapter; manually constructed token ABI'}));
