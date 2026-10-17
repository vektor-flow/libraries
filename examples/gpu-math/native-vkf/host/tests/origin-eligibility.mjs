import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import * as repaired from '../latex_source_binding.mjs';
import * as oracle from './origin-lookup-oracle/latex_source_binding.mjs';
const oldPath=process.argv[2]?.startsWith('/')?process.argv[2]:null;
const candidate=oldPath?await import(pathToFileURL(oldPath)):repaired;
const traceRows=[],checks=[];
const span=(start=0,end=8,sourceId='s')=>({sourceId,start,end});
function fixture(trace,field,kind,target,mode){
 const object={valueOf(){trace.push('coerce');return 8;}};
 const values={nan:NaN,undefined:undefined,string:'8',object,symbol:Symbol('endpoint'),reverse:field==='start'?8:0};
 const special=span(0,8);let reads=0;const finalRead={sourceId:2,start:4,end:5}[field];
 Object.defineProperty(special,field,{get(){trace.push(field+':'+(++reads));return reads>=finalRead?values[kind]:field==='sourceId'?'s':field==='start'?0:8;}});
 let groups=[special,...Array.from({length:17},()=>span())],leaves=[span(1,2)];
 if(target==='leaf'){groups=Array.from({length:18},()=>span());leaves=[special];}
 if(mode==='sparse-group'){groups=Array(18);groups[17]=span();}
 if(mode==='sparse-leaf'){leaves=Array(2);leaves[1]=span();}
 if(mode==='first-fail'){leaves=[span(0,1,'t'),span()];}
 if(mode==='invalid-start'){leaves=[span(-1,2)];}
 if(mode==='invalid-end'){leaves=[span(3,2)];}
 const owner={documentId:'d',revision:0,leafIds:['a'],groups:[{id:'g',first:0,count:mode==='empty'?0:1,contentVersion:0,layoutVersion:0,contentKey:'k',layoutKey:'k',edges:[]}],resources:[],leafResources:[[]],links:[]};
 if(mode==='empty')owner.groups.push({...owner.groups[0],id:'cover',count:1});
 return {owner,provenance:{offsetUnit:'utf16',sources:[{id:'s',version:0,text:'abcdefgh'},{id:'t',version:0,text:'abcdefgh'}],groups:[{id:'g',spans:groups},...(mode==='empty'?[{id:'cover',spans:[span()]}]:[])],leaves:[{id:'a',spans:leaves}]}};
}
const results={Fragment:{complete:true,scene:{arena:{count:1}}},Document:{complete:true,document:{arena:{count:1},page_count:2,firsts:[0,0],counts:[0,1]}}};
let mismatches=0;
for(const [name,result] of Object.entries(results)){
 for(const target of ['group','leaf'])for(const field of ['start','end','sourceId'])for(const kind of ['nan','undefined','string','object','symbol','reverse']){
  const modes=target==='group'?['normal','empty','first-fail','invalid-start','invalid-end']:['normal'];
  for(const mode of modes)compare(name,result,target,field,kind,mode);
 }
 for(const mode of ['sparse-group','sparse-leaf'])compare(name,result,'group','end','nan',mode);
 checks.push(name+' public getter endpoints and source IDs preserve exact oracle getter coercion and error traces');
 checks.push(name+' lazy empty first-failure invalid-order and sparse coverage preserve oracle behavior');
}
function compare(name,result,target,field,kind,mode){
 const invoke=m=>{const trace=[],f=fixture(trace,field,kind,target,mode);let outcome;
  try{m['bindSource'+name](result,f.owner,f.provenance);outcome={accepted:true};}catch(e){outcome={error:e.name+': '+e.message};}
  return {...outcome,trace};
 };
 const a=invoke(candidate),b=invoke(oracle);const equal=JSON.stringify(a)===JSON.stringify(b);
 traceRows.push({name,target,field,kind,mode,candidate:a,oracle:b,equal});
 if(!equal)mismatches++;
 if(!oldPath)assert.deepEqual(a,b,JSON.stringify({name,target,field,kind,mode}));
 if(target==='group'&&field==='end'&&kind==='nan'&&mode==='normal')assert.equal(b.accepted,true);
}
if(process.env.A331_TRACE_PATH){const fs=await import('node:fs');fs.writeFileSync(process.env.A331_TRACE_PATH,JSON.stringify({mismatches,cases:traceRows},null,2)+'\n');}
if(oldPath)assert(mismatches>0,'Old candidate must reproduce oracle difference');
console.log(JSON.stringify({passed:true,checks,cases:traceRows.length,mismatches}));
