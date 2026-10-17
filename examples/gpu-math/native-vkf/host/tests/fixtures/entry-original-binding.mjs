import {bindSourceFragment,bindSourceDocument} from '../../latex_source_binding.mjs';
const check=(ok,msg)=>{if(!ok)throw Error(msg);};
const num=x=>Number.isSafeInteger(x)&&x>=0;
const id=x=>typeof x==='string'&&x.length>0;
const sessions=new WeakSet();
const freeze=x=>{if(x&&typeof x==='object'){for(const v of Object.values(x))freeze(v);Object.freeze(x);}return x;};
// Called BEFORE layout. Owner issues stable IDs and explicitly maps THIS parse's
// local operation/emission selectors. A selector is never promoted to identity.
export function beginProvenance(owner){
 const o=structuredClone(owner);
 check(o&&Array.isArray(o.scopes)&&Array.isArray(o.sources)&&Array.isArray(o.groups),'Missing owner provenance');
 const sources=new Map(o.sources.map(s=>[s.id,s]));
 check(sources.size===o.sources.length&&o.sources.every(s=>id(s.id)&&num(s.version)&&typeof s.text==='string'),'Invalid owner source');
 const groups=new Map(o.groups.map(g=>[g.id,g]));check(groups.size===o.groups.length,'Duplicate group');
 const scopes=new Set(),leafIds=new Set();
 for(const scope of o.scopes){
  check(id(scope.id)&&!scopes.has(scope.id)&&sources.has(scope.sourceId)&&typeof scope.text==='string'&&num(scope.baseByte)&&Array.isArray(scope.operations),'Invalid parse scope');scopes.add(scope.id);
  check(scope.a262_originMode===undefined||scope.a262_originMode==='explicit','Invalid origin mode');
  // Expanded text is accepted only with explicit origins for EVERY operation.
  // It still must match the actual parser input at the native route/binder.
  if(scope.a262_originMode===undefined){
   const source=sources.get(scope.sourceId),base=byteToUtf16(source.text,scope.baseByte),end=byteToUtf16(source.text,scope.baseByte+new TextEncoder().encode(scope.text).length);
   check(source.text.slice(base,end)===scope.text,'Parse scope differs from source');
  }
  byteToUtf16(scope.text,new TextEncoder().encode(scope.text).length);
  const ops=new Set();
  for(const op of scope.operations){
   check(num(op.operation)&&!ops.has(op.operation)&&num(op.start)&&num(op.stop)&&op.start<=op.stop&&groups.has(op.groupId)&&Array.isArray(op.leaves),'Invalid operation mapping');ops.add(op.operation);
   byteToUtf16(scope.text,op.start);byteToUtf16(scope.text,op.stop);
   if(scope.a262_originMode==='explicit'){
    check(Array.isArray(op.a262_origins)&&op.a262_origins.length>0,'Missing explicit operation origins');
    for(const origin of op.a262_origins){
     const src=sources.get(origin?.sourceId);
     check(src&&num(origin.startByte)&&num(origin.stopByte)&&origin.startByte<origin.stopByte,'Invalid explicit origin');
     byteToUtf16(src.text,origin.startByte);byteToUtf16(src.text,origin.stopByte);
    }
   }else check(op.a262_origins===undefined,'Explicit origins require explicit scope mode');
   const parts=new Set();for(const leaf of op.leaves){check(num(leaf.part)&&!parts.has(leaf.part)&&id(leaf.id)&&Array.isArray(leaf.resources),'Invalid emission mapping');check(!leafIds.has(leaf.id),'Duplicate owner leaf ID');leafIds.add(leaf.id);parts.add(leaf.part);}
  }
 }
 freeze(o);sessions.add(o);return o;
}
// The native parser uses UTF-8 bytes; A258's public provenance uses UTF-16.
// Reject boundaries inside a scalar, including malformed surrogate source.
function byteToUtf16(text,wanted){
 check(num(wanted),'Invalid byte offset');let bytes=0,units=0;
 for(const scalar of text){
  const cp=scalar.codePointAt(0);check(cp<0xd800||cp>0xdfff,'Unpaired surrogate source');
  if(bytes===wanted)return units;
  bytes+=new TextEncoder().encode(scalar).length;units+=scalar.length;
  check(bytes<=wanted,'Byte offset splits scalar');
 }
 check(bytes===wanted,'Byte offset outside source');return units;
}
// Request-local, lazy Unicode boundary index. Storage is bounded by scanned
// source code points, never by the requested byte offset. No session is retained.
function createByteToUtf16Index(){
 const texts=new Map();
 return (text,wanted)=>{
  check(num(wanted),'Invalid byte offset');
  let state=texts.get(text);
  if(!state){state={bytes:[0],units:[0]};texts.set(text,state);}
  const {bytes,units}=state;
  while(bytes.at(-1)<wanted&&units.at(-1)<text.length){
   const unit=units.at(-1),cp=text.codePointAt(unit);
   check(cp<0xd800||cp>0xdfff,'Unpaired surrogate source');
   bytes.push(bytes.at(-1)+(cp<=0x7f?1:cp<=0x7ff?2:cp<=0xffff?3:4));
   units.push(unit+(cp>0xffff?2:1));
  }
  check(wanted<=bytes.at(-1),'Byte offset outside source');
  let lo=0,hi=bytes.length-1;
  while(lo<hi){const mid=lo+Math.floor((hi-lo)/2);if(bytes[mid]<wanted)lo=mid+1;else hi=mid;}
  check(bytes[lo]===wanted,'Byte offset splits scalar');
  // The original validates the next scalar BEFORE accepting its start boundary.
  // Preserve this even for offset zero and for a previously cached boundary.
  const cp=text.codePointAt(units[lo]);
  check(cp===undefined||cp<0xd800||cp>0xdfff,'Unpaired surrogate source');
  return units[lo];
 };
}
function bind(result,session,previous,document){
 const convertByte=createByteToUtf16Index();
 check(sessions.has(session),'Entry owner session required');
 check(result?.complete===true,'Incomplete layout cannot be reused');
 const arena=document?result.document?.arena:result.scene?.arena,n=arena?.count;
 check(num(n),'Missing typed arena');
 for(const column of ['a260_scopes','a260_texts','a260_operations','a260_starts','a260_stops','a260_parts'])check(arena[column]?.length===n,'Missing provenance column '+column);
 const scopes=new Map(session.scopes.map(s=>[s.id,s])),groupsById=new Map(session.groups.map(g=>[g.id,g]));
 const leafIds=[],leafResources=[],links=[],groups=[],origins=[],used=new Set();let group=null;
 for(let i=0;i<n;i++){
  const scope=scopes.get(arena.a260_scopes[i]),operation=arena.a260_operations[i],part=arena.a260_parts[i];
  check(scope&&scope.text===arena.a260_texts[i]&&num(operation)&&num(part),'Unbound/generated operation');
  const op=scope.operations.find(o=>o.operation===operation);
  check(op&&op.start===arena.a260_starts[i]&&op.stop===arena.a260_stops[i],'Parser span/owner mismatch');
  const leaf=op.leaves.find(l=>l.part===part);check(leaf&&!used.has(leaf.id),'Missing/duplicate owner leaf');used.add(leaf.id);
  if(group?.id!==op.groupId){check(!groups.some(g=>g.id===op.groupId),'Noncontiguous semantic group');group={...groupsById.get(op.groupId),first:i,count:0};groups.push(group);}group.count++;
  leafIds.push(leaf.id);leafResources.push(leaf.resources);
  const pi=arena.payloads?.[i],payload=pi>=0?arena.payload_table?.[pi]:null;
  if(arena.kinds?.[i]===3){check(id(leaf.link)&&payload?.target===leaf.link,'Link origin/target mismatch');links.push({leaf:i,target:leaf.link});}
  else check(leaf.link===undefined,'Link mapping on non-link leaf');
  const text=session.sources.find(s=>s.id===scope.sourceId).text;
  const spans=scope.a262_originMode==='explicit'?op.a262_origins.map(origin=>{
   const source=session.sources.find(s=>s.id===origin.sourceId);
   return {sourceId:origin.sourceId,start:convertByte(source.text,origin.startByte),end:convertByte(source.text,origin.stopByte)};
  }):[{sourceId:scope.sourceId,start:convertByte(text,scope.baseByte+op.start),end:convertByte(text,scope.baseByte+op.stop)}];
  origins.push({id:leaf.id,spans});
 }
 // Unconsumed mappings are rejected: deletion/changed multi-leaf emission must
 // be explicitly reconciled by the edit owner before reuse is possible.
 check(session.scopes.every(s=>s.operations.every(o=>o.leaves.every(l=>used.has(l.id)))),'Unconsumed owner leaf mapping');
 const owner={documentId:session.documentId,revision:session.revision,resources:session.resources,leafIds,leafResources,links,groups};
 const provenance={offsetUnit:'utf16',sources:session.sources,groups:groups.map(g=>({id:g.id,spans:g.spans})),leaves:origins};
 return (document?bindSourceDocument:bindSourceFragment)(result,owner,provenance,previous);
}
export function bindOperationFragment(fragment,session,previous=null){return bind(fragment,session,previous,false);}
export function bindOperationDocument(document,session,previous=null){return bind(document,session,previous,true);}

// Resolve explicit per-parse selectors before calling native document_owned.
// No text search, geometry matching, or index-to-identity conversion.
export function documentEntryRoutes(session,routes){
 check(sessions.has(session)&&Array.isArray(routes),'Entry owner session required');
 const blocks=[],scopes=[],texts=[],kinds=[],seen=new Set(),used=new Set();
 for(const route of routes){
  const kind=route?.kind??'body',selector=JSON.stringify([route?.block,kind]);
  check((kind==='body'||kind==='label'||(typeof kind==='string'&&/^outer:(0|[1-9][0-9]*)$/.test(kind)))&&route&&num(route.block)&&!seen.has(selector)&&id(route.scope)&&!used.has(route.scope),'Invalid/duplicate document route');
  const scope=session.scopes.find(s=>s.id===route.scope);
  check(scope,'Unknown document scope');seen.add(selector);used.add(scope.id);
  blocks.push(route.block);scopes.push(scope.id);texts.push(scope.text);kinds.push(kind);
 }
 check(used.size===session.scopes.length,'Missing document scope route');
 return freeze({blocks,scopes,texts,kinds});
}

// Separate producer namespaces, one immutable edit-owner session. Note selectors
// address current definition order; visible counters never become owner IDs.
export function documentAndNoteEntryRoutes(session,bodyRoutes,noteRoutes){
 check(sessions.has(session)&&Array.isArray(bodyRoutes)&&Array.isArray(noteRoutes),'Entry owner session required');
 const used=new Set();
 function routes(input,note){
  const blocks=[],scopes=[],texts=[],kinds=[],seen=new Set();
  for(const route of input){
   const kind=route?.kind??'body',block=route?.block,selector=JSON.stringify([block,kind]);
   const validKind=kind==='body'||kind==='label'||(!note&&typeof kind==='string'&&/^outer:(0|[1-9][0-9]*)$/.test(kind));
   check(validKind&&num(block)&&!seen.has(selector)&&id(route?.scope)&&!used.has(route.scope),'Invalid/duplicate document or note route');
   const scope=session.scopes.find(s=>s.id===route.scope);check(scope,'Unknown document or note scope');
   seen.add(selector);used.add(scope.id);blocks.push(block);scopes.push(scope.id);texts.push(scope.text);kinds.push(kind);
  }
  return {blocks,scopes,texts,kinds};
 }
 const body=routes(bodyRoutes,false),notes=routes(noteRoutes,true);
 check(used.size===session.scopes.length,'Missing document or note scope route');
 return freeze({body,notes});
}
