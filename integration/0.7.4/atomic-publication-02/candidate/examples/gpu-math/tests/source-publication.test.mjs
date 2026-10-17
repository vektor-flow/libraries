import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {createSourceEditSession} from '../native-vkf/host/latex_source_revision.mjs';

// Opaque synthetic bytes exercise publication only, never a native map/PDF claim.
const sources=[{id:'主 源😀.tex',version:0,text:'A😀\r\né\ud800'}];
const replacement=(snapshot,label)=>({sourceRevision:snapshot.revision,map:Buffer.from('map fixture '+label),pdf:Buffer.from('PDF fixture '+label)});
const render=label=>snapshot=>({complete:true,replacement:replacement(snapshot,label)});
const request=(session,text)=>({expectedRevision:session.current.snapshot.revision,
 edits:text===undefined?[]:[{sourceId:sources[0].id,start:0,end:1,text}]});
const deferred=()=>{let resolve;const promise=new Promise(r=>{resolve=r;});return {promise,resolve};};
function fixture(t){
 const directory=fs.mkdtempSync(path.join(process.env.VKF_PUBLICATION_TEST_TMPDIR||os.tmpdir(),'publication Ω 😀 '));
 t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 const destination=path.join(directory,'résultat 源 😀.bundle');
 const session=createSourceEditSession(sources,null,{publicationPath:destination});
 return {directory,destination,session};
}
const bundle=destination=>JSON.parse(fs.readFileSync(destination,'utf8'));
function coherent(destination,state){
 const stored=bundle(destination).content;
 assert.deepEqual(stored.snapshot,state.snapshot);
 assert.equal(stored.snapshot.revision,state.replacement.sourceRevision);
 assert.deepEqual(Buffer.from(stored.mapBase64,'base64'),state.replacement.map);
 assert.deepEqual(Buffer.from(stored.pdfBase64,'base64'),state.replacement.pdf);
}
const clean=({directory,destination})=>assert.deepEqual(fs.readdirSync(directory),[path.basename(destination)]);

// Each top-level test runs sequentially; fs mocks are scoped and restored by t.
test('Unicode destination publishes one complete bundle, preserving exact source and immutable byte copies',async t=>{
 const f=fixture(t),{session,destination}=f;
 const pending=deferred();
 const task=session.apply(request(session,'Ω'),async snapshot=>{await pending.promise;return render('new')(snapshot);});
 assert.equal(fs.existsSync(destination),false);
 pending.resolve();const state=await task;
 coherent(destination,state);clean(f);
 assert.equal(state.snapshot.sources[0].text,'Ω😀\r\né\ud800');
 assert.equal(state.publication.committed,true);assert.equal(state.publication.durable,true);
 const saved=fs.readFileSync(destination);state.replacement.pdf.fill(0);state.replacement.map.fill(0);
 assert.deepEqual(fs.readFileSync(destination),saved);coherent(destination,state);
});

test('stale completion, stale request and invalid preparation never replace the previous bundle',async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const before=session.current,old=fs.readFileSync(destination),slow=deferred();
 const pending=session.apply(request(session,'X'),()=>slow.promise);
 for(const callback of [()=>{throw Error('render failed');},()=>({complete:false,replacement:{}}),
  snapshot=>({...render('bad')(snapshot),diagnostics:['bad']}),
  snapshot=>({...render('bad')(snapshot),unresolved:['missing']}),
  snapshot=>({complete:true,replacement:{...replacement(snapshot,'bad'),sourceRevision:'wrong'}}),
  snapshot=>({complete:true,replacement:{...replacement(snapshot,'bad'),map:'not bytes'}})]){
  await assert.rejects(session.apply(request(session,'!'),callback));
  assert.equal(session.current,before);assert.deepEqual(fs.readFileSync(destination),old);clean(f);
 }
 const winner=await session.apply(request(session,'Y'),render('winner'));
 const saved=fs.readFileSync(destination);
 slow.resolve(render('loser')(before.snapshot));
 await assert.rejects(pending,/Stale source completion/);
 assert.equal(session.current,winner);assert.deepEqual(fs.readFileSync(destination),saved);
 assert.throws(()=>session.apply({expectedRevision:before.snapshot.revision,edits:[]},()=>{throw Error('must not run');}),/Stale/);
 coherent(destination,winner);clean(f);
});

for(const operation of ['write','flush','close','rename'])test(`${operation} failure preserves old source/map/PDF and cleans temporary files`,async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const before=session.current,old=fs.readFileSync(destination);
 const fail=()=>{throw Object.assign(Error('injected '+operation),{code:'EIO'});};
 if(operation==='write'){
  const original=fs.writeFileSync;
  t.mock.method(fs,'writeFileSync',(fd,bytes)=>{original(fd,bytes.subarray(0,11));fail();});
 }else if(operation==='flush')t.mock.method(fs,'fsyncSync',fail);
 else if(operation==='close'){
  const original=fs.closeSync;let first=true;
  t.mock.method(fs,'closeSync',fd=>{original(fd);if(first){first=false;fail();}});
 }else t.mock.method(fs,'renameSync',fail);
 await assert.rejects(session.apply(request(session,'N'),render('new')),/injected/);
 t.mock.restoreAll();
 assert.equal(session.current,before);assert.deepEqual(fs.readFileSync(destination),old);clean(f);
 // A failed preparation does not poison subsequent valid publication.
 await session.apply(request(session,'V'),render('valid'));coherent(destination,session.current);clean(f);
});

test('real filesystem rename error preserves the prior bundle and removes its staged file',async t=>{
 const f=fixture(t),{destination,session}=f;
 await session.apply(request(session),render('old'));
 const before=session.current,old=fs.readFileSync(destination),rename=fs.renameSync;
 // Route only the attempted rename to an invalid child of the existing file.
 // Generation validation and temp I/O remain real; the kernel returns ENOTDIR.
 t.mock.method(fs,'renameSync',(source,target)=>{
  assert.equal(target,destination);return rename(source,path.join(target,'invalid-child'));
 });
 await assert.rejects(session.apply(request(session,'N'),render('new')),{code:'ENOTDIR'});
 t.mock.restoreAll();assert.equal(session.current,before);
 assert.deepEqual(fs.readFileSync(destination),old);coherent(destination,before);clean(f);
});

test('missing parent fails real temp creation without changing session state',async t=>{
 const f=fixture(t),destination=path.join(f.directory,'missing','file.bundle');
 const session=createSourceEditSession(sources,null,{publicationPath:destination}),before=session.current;
 await assert.rejects(session.apply(request(session,'N'),render('new')),{code:'ENOENT'});
 assert.equal(session.current,before);assert.deepEqual(fs.readdirSync(f.directory),[]);
});

test('post-rename directory flush failure commits state and returns durability warning',async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const original=fs.fsyncSync;
 t.mock.method(fs,'fsyncSync',fd=>{
  if(fs.fstatSync(fd).isDirectory())throw Object.assign(Error('directory flush failed'),{code:'EIO'});
  return original(fd);
 });
 const state=await session.apply(request(session,'N'),render('new'));
 assert.equal(state.publication.committed,true);assert.equal(state.publication.durable,false);
 assert.match(state.publication.warnings[0].message,/directory flush/);
 coherent(destination,state);clean(f);
});

test('lock contention fails closed without deleting another writer lock',async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const before=session.current,old=fs.readFileSync(destination),lock=destination+'.lock';
 fs.writeFileSync(lock,'other writer');
 await assert.rejects(session.apply(request(session,'N'),render('new')),{code:'EEXIST'});
 assert.equal(fs.readFileSync(lock,'utf8'),'other writer');assert.equal(session.current,before);
 assert.deepEqual(fs.readFileSync(destination),old);
 assert.equal(fs.readdirSync(f.directory).length,2);fs.unlinkSync(lock);clean(f);
});

test('two sessions opened on the same generation cannot overwrite a newer no-op bundle',async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const old=session.current;
 const other=createSourceEditSession(old.snapshot.sources,old.replacement,{publicationPath:destination});
 const before=other.current;
 assert.throws(()=>createSourceEditSession(sources,null,{publicationPath:destination}),/revision mismatch/);
 await session.apply(request(session),render('new no-op'));
 const saved=fs.readFileSync(destination);
 assert.equal(session.current.snapshot.revision,old.snapshot.revision);
 await assert.rejects(other.apply(request(other,'N'),render('stale')),/Stale source publication/);
 assert.equal(other.current,before);assert.deepEqual(fs.readFileSync(destination),saved);clean(f);
});

test('same-session no-op commit rejects pending older output even with equal hashes',async t=>{
 const f=fixture(t),{session,destination}=f,slow=deferred();
 const pending=session.apply(request(session),()=>slow.promise);
 const state=await session.apply(request(session),render('winner'));
 slow.resolve(render('stale')(state.snapshot));
 await assert.rejects(pending,/Stale source completion/);coherent(destination,state);clean(f);
});

test('real competing processes publish at most one generation and every read is coherent',{timeout:10000},async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const initial=session.current;
 const moduleURL=new URL('../native-vkf/host/latex_source_revision.mjs',import.meta.url).href;
 const script=`import {createSourceEditSession} from ${JSON.stringify(moduleURL)};
 const initial=JSON.parse(process.env.PUBLICATION_INITIAL);
 const r={sourceRevision:initial.snapshot.revision,map:Buffer.from(initial.map,'base64'),pdf:Buffer.from(initial.pdf,'base64')};
 const session=createSourceEditSession(initial.snapshot.sources,r,{publicationPath:process.env.PUBLICATION_DEST});
 process.send({ready:true});
 process.on('message',async()=>{
  try {const state=await session.apply({expectedRevision:session.current.snapshot.revision,edits:[]},s=>({complete:true,replacement:{sourceRevision:s.revision,map:Buffer.from(process.env.PUBLICATION_LABEL),pdf:Buffer.from(process.env.PUBLICATION_LABEL)}}));process.send({ok:true,revision:state.snapshot.revision});}
  catch(error){process.send({ok:false,error:error.message,code:error.code});}
  process.disconnect();
 });`;
 const children=['one','two'].map(label=>{
  const child=spawn(process.execPath,['--input-type=module','-e',script],{stdio:['ignore','ignore','pipe','ipc'],env:{...process.env,
   PUBLICATION_DEST:destination,PUBLICATION_LABEL:label,PUBLICATION_INITIAL:JSON.stringify({snapshot:initial.snapshot,map:initial.replacement.map.toString('base64'),pdf:initial.replacement.pdf.toString('base64')})}});
  let stderr='';child.stderr.on('data',value=>{stderr+=value;});
  const exited=once(child,'exit');
  t.after(async()=>{if(child.exitCode===null&&child.signalCode===null)child.kill();await exited;});
  return {child,ready:once(child,'message'),exited,stderr:()=>stderr};
 });
 await Promise.all(children.map(c=>c.ready));
 const results=children.map(c=>once(c.child,'message'));
 children.forEach(c=>c.child.send('go'));
 const observations=[];
 const reader=setInterval(()=>observations.push(bundle(destination)),1);
 const outcomes=await Promise.all(results);
 clearInterval(reader);observations.push(bundle(destination));
 const exits=await Promise.all(children.map(c=>c.exited));
 for(let i=0;i<exits.length;i++){assert.deepEqual(exits[i],[0,null]);assert.equal(children[i].stderr(),'');}
 assert.equal(outcomes.filter(([r])=>r.ok).length,1);
 const loser=outcomes.find(([r])=>!r.ok)[0];
 assert.ok(loser.code==='EEXIST'||/Stale source publication/.test(loser.error));
 for(const entry of observations){
  const {snapshot,mapBase64,pdfBase64}=entry.content;
  assert.deepEqual(snapshot,initial.snapshot);
  const map=Buffer.from(mapBase64,'base64').toString(),pdf=Buffer.from(pdfBase64,'base64').toString();
  assert.ok((map==='map fixture old'&&pdf==='PDF fixture old')||(map===pdf&&['one','two'].includes(map)));
 }
 clean(f);
});

test('post-rename lock removal failure is committed, reported and fails subsequent writers closed',async t=>{
 const f=fixture(t),{session,destination}=f;
 const unlink=fs.unlinkSync;
 t.mock.method(fs,'unlinkSync',name=>{
  if(name===destination+'.lock')throw Object.assign(Error('lock cleanup failed'),{code:'EACCES'});
  return unlink(name);
 });
 const committed=await session.apply(request(session,'N'),render('new'));
 assert.equal(committed.publication.committed,true);assert.equal(committed.publication.durable,false);
 assert.match(committed.publication.warnings[0].message,/lock cleanup/);coherent(destination,committed);
 t.mock.restoreAll();
 await assert.rejects(session.apply(request(session,'X'),render('blocked')),{code:'EEXIST'});
 assert.equal(session.current,committed);coherent(destination,committed);
 fs.unlinkSync(destination+'.lock');clean(f);
});

test('cleanup failure is explicit and does not hide the pre-publication error or replace prior bytes',async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const before=session.current,old=fs.readFileSync(destination),unlink=fs.unlinkSync;
 t.mock.method(fs,'renameSync',()=>{throw Error('rename failed');});
 t.mock.method(fs,'unlinkSync',name=>{
  if(name.endsWith('.tmp'))throw Error('temporary cleanup failed');
  return unlink(name);
 });
 await assert.rejects(session.apply(request(session,'N'),render('new')),error=>{
  assert.ok(error instanceof AggregateError);
  assert.deepEqual(error.errors.map(e=>e.message),['rename failed','temporary cleanup failed']);return true;
 });
 t.mock.restoreAll();
 assert.equal(session.current,before);assert.deepEqual(fs.readFileSync(destination),old);
 const leftovers=fs.readdirSync(f.directory).filter(name=>name.endsWith('.tmp'));
 assert.equal(leftovers.length,1);fs.unlinkSync(path.join(f.directory,leftovers[0]));clean(f);
});

test('existing bundle mismatch refuses attachment; copied initial bytes remain stable on failed edits',async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const state=session.current,wrong={...state.replacement,pdf:Buffer.from('wrong')};
 assert.throws(()=>createSourceEditSession(state.snapshot.sources,wrong,{publicationPath:destination}),/does not match/);
 const original={...state.replacement};
 const reopened=createSourceEditSession(state.snapshot.sources,original,{publicationPath:destination});
 original.pdf.fill(0);original.map.fill(0);
 await assert.rejects(reopened.apply(request(reopened,'X'),()=>{throw Error('failed');}));
 coherent(destination,reopened.current);clean(f);
 await reopened.apply(request(reopened,'R'),render('restored'));coherent(destination,reopened.current);clean(f);
});

test('file bytes are copied before publication and caller getters cannot publish a stale nested completion',async t=>{
 const f=fixture(t),{session,destination}=f;
 let nested;const old=session.current.snapshot;
 const state=await session.apply(request(session,'N'),snapshot=>({complete:true,replacement:{
  sourceRevision:snapshot.revision,
  get map(){
   nested=session.apply({expectedRevision:old.revision,edits:[]},render('nested stale'));
   return Buffer.from('outer map');
  },pdf:Buffer.from('outer PDF')
 }}));
 await assert.rejects(nested,/Stale source completion/);
 coherent(destination,state);assert.equal(state.replacement.map.toString(),'outer map');clean(f);
});

test('initial replacement getters are copied once before validating disk attachment',async t=>{
 const f=fixture(t),{session,destination}=f;
 await session.apply(request(session),render('old'));
 const old=session.current;let reads=0;
 const reopened=createSourceEditSession(old.snapshot.sources,{
  sourceRevision:old.snapshot.revision,pdf:old.replacement.pdf,
  get map(){reads++;return reads===1?old.replacement.map:Buffer.from('changed getter');}
 },{publicationPath:destination});
 assert.equal(reads,1);coherent(destination,reopened.current);clean(f);
});
