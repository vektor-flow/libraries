import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';

const publications=new WeakMap(),staged=new WeakMap();
const format='latex-source-bundle-v1';
const check=(ok,message)=>{if(!ok)throw Error(message);};
const digest=bytes=>bytes===null?null:createHash('sha256').update(bytes).digest('hex');
const read=destination=>{try{return fs.readFileSync(destination);}catch(error){if(error.code==='ENOENT')return null;throw error;}};
const failure=(error,errors)=>errors.length?new AggregateError([error,...errors],error.message,{cause:error}):error;
const attempt=(errors,action)=>{try{action();}catch(error){errors.push(error);}};

function content(snapshot,replacement){
 const {sourceRevision,map,pdf}=replacement??{};
 check(sourceRevision===snapshot.revision,'Replacement source revision mismatch');
 check(map instanceof Uint8Array&&pdf instanceof Uint8Array,'Replacement requires map and PDF bytes');
 // Copy before I/O; no caller-owned bytes or getters enter the commit section.
 return {snapshot,mapBase64:Buffer.from(map).toString('base64'),pdfBase64:Buffer.from(pdf).toString('base64')};
}
function immutableReplacement(value){
 return Object.freeze({sourceRevision:value.snapshot.revision,
  get map(){return Buffer.from(value.mapBase64,'base64');},
  get pdf(){return Buffer.from(value.pdfBase64,'base64');}});
}

export function copySourcePublicationReplacement(snapshot,replacement){
 return immutableReplacement(content(snapshot,replacement));
}

/** Internal host prerequisite. Destination is ONE bundle, not a standalone PDF.
 * Existing content must match the supplied initial state. All writers must use
 * this protocol in a trusted local directory; see latex_source_publication.txt.
 */
export function openSourcePublication(destination,snapshot,replacement){
 check(typeof destination==='string'&&destination.length>0,'Invalid publication path');
 destination=path.resolve(destination);
 const bytes=read(destination);
 if(bytes!==null){
  const previous=JSON.parse(bytes.toString('utf8'));
  check(previous.format===format&&typeof previous.generation==='string'&&
   JSON.stringify(previous.content)===JSON.stringify(content(snapshot,replacement)),
   'Existing publication does not match initial state');
 }
 const publication=Object.freeze({});
 publications.set(publication,{destination,generation:digest(bytes)});
 return publication;
}

/** Write, flush and close an unreferenced same-directory temporary bundle.
 * Synchronous I/O deliberately bounds this implementation to small host work.
 */
export function stageSourcePublication(publication,snapshot,replacement){
 const owner=publications.get(publication);check(owner,'Invalid publication');
 const value=content(snapshot,replacement),canonical=immutableReplacement(value);
 const bytes=Buffer.from(JSON.stringify({format,generation:randomUUID(),content:value})+'\n');
 const temporary=path.join(path.dirname(owner.destination),'.latex-bundle-'+randomUUID()+'.tmp');
 const prepared=Object.freeze({}),entry={owner,temporary,replacement:canonical,generation:digest(bytes),consumed:false};
 let fd,created=false;
 try{
  fd=fs.openSync(temporary,'wx',0o600);created=true;
  fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);
  const closing=fd;fd=undefined;fs.closeSync(closing);
  staged.set(prepared,entry);return prepared;
 }catch(error){
  const errors=[];
  if(fd!==undefined)attempt(errors,()=>fs.closeSync(fd));
  if(created)attempt(errors,()=>fs.unlinkSync(temporary));
  throw failure(error,errors);
 }
}

export function preparedSourceReplacement(prepared){
 const entry=staged.get(prepared);check(entry&&!entry.consumed,'Invalid staged publication');
 return entry.replacement;
}

export function discardSourcePublication(prepared){
 const entry=staged.get(prepared);
 if(entry&&!entry.consumed){fs.unlinkSync(entry.temporary);entry.consumed=true;}
}

/** No await or caller callbacks. Successful rename is the irreversible commit.
 * Errors AFTER rename are returned as warnings, never a failed edit/rollback.
 */
export function commitSourcePublication(publication,prepared){
 const owner=publications.get(publication),entry=staged.get(prepared);
 check(owner&&entry&&entry.owner===owner&&!entry.consumed,'Invalid staged publication');
 const lock=owner.destination+'.lock';
 let fd,locked=false;
 const unlock=errors=>{
  if(fd!==undefined){const closing=fd;fd=undefined;attempt(errors,()=>fs.closeSync(closing));}
  if(locked){locked=false;attempt(errors,()=>fs.unlinkSync(lock));}
 };
 try{
  // Exclusive creation serializes cooperating processes too. Never steal locks.
  fd=fs.openSync(lock,'wx',0o600);locked=true;
  check(digest(read(owner.destination))===owner.generation,'Stale source publication');
  fs.renameSync(entry.temporary,owner.destination);
 }catch(error){
  const errors=[];unlock(errors);throw failure(error,errors);
 }
 entry.consumed=true;owner.generation=entry.generation;
 const warnings=[];unlock(warnings);
 let directory;
 try{directory=fs.openSync(path.dirname(owner.destination),'r');fs.fsyncSync(directory);}
 catch(error){warnings.push(error);}
 finally{if(directory!==undefined)attempt(warnings,()=>fs.closeSync(directory));}
 return Object.freeze({committed:true,durable:warnings.length===0,warnings:Object.freeze(warnings)});
}
