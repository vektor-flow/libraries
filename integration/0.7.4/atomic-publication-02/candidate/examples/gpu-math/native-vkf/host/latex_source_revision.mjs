import {createHash} from 'node:crypto';
import {copySourcePublicationReplacement,openSourcePublication,stageSourcePublication,preparedSourceReplacement,commitSourcePublication,discardSourcePublication} from './latex_source_publication.mjs';

const snapshots=new WeakSet();
const check=(ok,message)=>{if(!ok)throw Error(message);};
const integer=value=>Number.isSafeInteger(value)&&value>=0;
const boundary=(text,n)=>n===0||n===text.length||!(text.charCodeAt(n-1)>=0xd800&&text.charCodeAt(n-1)<=0xdbff&&text.charCodeAt(n)>=0xdc00&&text.charCodeAt(n)<=0xdfff);

/** Node host prerequisite, not a native rendering or PDF API.
 * Copy the source-binding schema: {id, version, text}, with explicit stable IDs.
 * Sort by UTF-16 ID order; input row order has no revision meaning. SHA-256 covers
 * a versioned JSON tuple of every exact ID, version and string. JSON escaping
 * preserves lone surrogates as well as CRLF and non-BMP text without normalization.
 * A revision is a source snapshot hash, not the numeric scene-owner revision.
 */
export function createSourceSnapshot(sources){
 check(Array.isArray(sources),'Invalid sources');
 const rows=sources.map(source=>{
  const {id,version,text}=source??{};
  check(typeof id==='string'&&id.length>0&&integer(version)&&typeof text==='string','Invalid source');
  return Object.freeze({id,version,text});
 }).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0);
 check(new Set(rows.map(row=>row.id)).size===rows.length,'Duplicate source');
 const encoded=JSON.stringify(['latex-source-revision-v1',rows.map(({id,version,text})=>[id,version,text])]);
 const revision='sha256:'+createHash('sha256').update(encoded,'utf8').digest('hex');
 const snapshot=Object.freeze({offsetUnit:'utf16',revision,sources:Object.freeze(rows)});
 snapshots.add(snapshot);return snapshot;
}

/** All edits use the original snapshot's UTF-16 offsets:
 * {sourceId, start, end, text}. Existing scalar pairs cannot be split.
 * Ranges may touch, but overlaps and duplicate starts (ambiguous insertions) fail.
 * Changed files advance version once; unchanged files retain their version.
 * No mutation, file creation, ID inference, or source normalization occurs.
 */
export function stageSourceEdits(snapshot,{expectedRevision,edits}={}){
 check(snapshots.has(snapshot),'Invalid source snapshot');
 check(expectedRevision===snapshot.revision,'Stale source revision');
 check(Array.isArray(edits),'Invalid edits');
 const byId=new Map(snapshot.sources.map(source=>[source.id,source])),byFile=new Map();
 for(const edit of edits){
  const {sourceId,start,end,text}=edit??{},source=byId.get(sourceId);
  check(source&&integer(start)&&integer(end)&&start<=end&&end<=source.text.length&&typeof text==='string','Invalid source edit');
  check(boundary(source.text,start)&&boundary(source.text,end),'Split Unicode scalar');
  let rows=byFile.get(sourceId);if(!rows)byFile.set(sourceId,rows=[]);
  rows.push({start,end,text});
 }
 const sources=snapshot.sources.map(source=>{
  const edits=byFile.get(source.id);if(!edits)return source;
  edits.sort((a,b)=>a.start-b.start||a.end-b.end);
  let cursor=0,previous=null,text='';
  for(const edit of edits){
   check(!previous||(edit.start>=previous.end&&edit.start!==previous.start),'Overlapping source edits');
   text+=source.text.slice(cursor,edit.start)+edit.text;cursor=edit.end;previous=edit;
  }
  text+=source.text.slice(cursor);
  if(text===source.text)return source;
  check(source.version<Number.MAX_SAFE_INTEGER,'Source version exhausted');
  return {id:source.id,version:source.version+1,text};
 });
 return createSourceSnapshot(sources);
}

/** Render is a preparation callback: render(candidate) ->
 * {complete:true, replacement, diagnostics?:[], unresolved?:[]}.
 * It must not publish external side effects. Without publicationPath the session
 * commits only its own snapshot/replacement pair. Failed or stale preparation
 * leaves that pair intact.
 * Optional {publicationPath} enables the small host bundle prerequisite, NOT a
 * native tex2pdf API. replacement must then contain {sourceRevision,map,pdf},
 * with Uint8Array map/PDF bytes supplied by the caller, never synthesized here.
 * A single bundle rename commits all three; publication warnings mean the rename
 * committed but crash durability/cleanup was not confirmed. See publication docs.
 * Among concurrent requests from one base, the first successful commit wins.
 * Snapshot identity also rejects stale no-op completions (the hash may be equal).
 */
export function createSourceEditSession(sources,initialReplacement=null,{publicationPath}={}){
 let state=Object.freeze({snapshot:createSourceSnapshot(sources),replacement:initialReplacement});
 if(publicationPath!==undefined&&initialReplacement!==null)state=Object.freeze({snapshot:state.snapshot,
  replacement:copySourcePublicationReplacement(state.snapshot,initialReplacement)});
 const publication=publicationPath===undefined?null:openSourcePublication(publicationPath,state.snapshot,state.replacement);
 function apply(request,render){
  check(typeof render==='function','Missing render callback');
  const base=state,candidate=stageSourceEdits(base.snapshot,request);
  return (async()=>{
   const result=await render(candidate);
   check(state===base,'Stale source completion');
   const {complete,replacement,diagnostics=[],unresolved=[]}=result??{};
   check(complete===true&&replacement!==undefined&&replacement!==null&&Array.isArray(diagnostics)&&diagnostics.length===0&&Array.isArray(unresolved)&&unresolved.length===0,'Incomplete source replacement');
   let prepared;
   try{
    prepared=publication?stageSourcePublication(publication,candidate,replacement):null;
    const committedReplacement=prepared?preparedSourceReplacement(prepared):replacement;
    // All caller-owned properties and bytes were read before this final guard.
    // Trusted synchronous commit performs CAS+rename without yielding to another
    // request. Its pre-rename errors preserve state; post-rename warnings commit.
    check(state===base,'Stale source completion');
    const receipt=prepared?commitSourcePublication(publication,prepared):null;
    state=Object.freeze({snapshot:candidate,replacement:committedReplacement,
     ...(receipt?{publication:receipt}:{})});return state;
   }catch(error){
    try{if(prepared)discardSourcePublication(prepared);}
    catch(cleanup){throw new AggregateError([error,cleanup],error.message,{cause:error});}
    throw error;
   }
  })();
 }
 return Object.freeze({apply,get current(){return state;}});
}
