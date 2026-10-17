import test from 'node:test';
import assert from 'node:assert/strict';
import {createSourceSnapshot,stageSourceEdits,createSourceEditSession} from '../native-vkf/host/latex_source_revision.mjs';

const row=(id,text,version=0)=>({id,version,text});
const edit=(sourceId,start,end,text)=>({sourceId,start,end,text});
const request=(snapshot,edits)=>({expectedRevision:snapshot.revision,edits});
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};

test('snapshots copy and freeze exact source-binding rows with stable order-independent hashes',()=>{
 const sources=[row('chapter.tex','é😀\r\n'),row('main.tex','\\input{chapter}\r\n')],snapshot=createSourceSnapshot(sources);
 assert.deepEqual(snapshot.sources,sources);
 assert.equal(snapshot.offsetUnit,'utf16');assert.match(snapshot.revision,/^sha256:[a-f0-9]{64}$/);
 assert.equal(createSourceSnapshot([...sources].reverse()).revision,snapshot.revision);
 assert.ok(Object.isFrozen(snapshot)&&Object.isFrozen(snapshot.sources)&&snapshot.sources.every(Object.isFrozen));
 sources[0].text='changed';sources.push(row('other.tex',''));
 assert.equal(snapshot.sources[0].text,'é😀\r\n');assert.equal(snapshot.sources.length,2);
 assert.throws(()=>{snapshot.sources[0].text='changed';},TypeError);
 assert.throws(()=>createSourceSnapshot([row('same','a'),row('same','b')]),/Duplicate/);
 assert.throws(()=>createSourceSnapshot([row('id','x',-1)]),/Invalid/);
});

test('hash framing distinguishes IDs, versions, boundaries, line endings and exact Unicode',()=>{
 const variants=[
  [row('a','bc')],[row('ab','c')],[row('a','bc',1)],
  [row('a','b'),row('c','')],[row('a','b\nc')],[row('a','b\r\nc')],
  [row('a','é')],[row('a','e\u0301')],[row('a','😀')],
  [row('a','\ud800')],[row('a','\ud801')],[row('a','\ufffd')]
 ];
 assert.equal(new Set(variants.map(createSourceSnapshot).map(s=>s.revision)).size,variants.length);
});

test('multifile edits use original offsets, preserve CRLF and advance only changed file versions',()=>{
 const original=createSourceSnapshot([row('main.tex','A😀B\r\nC',4),row('part.tex','abcd',7),row('untouched.tex','same',3)]);
 const staged=stageSourceEdits(original,request(original,[edit('part.tex',3,4,'!'),edit('main.tex',1,3,'Ω'),edit('part.tex',0,1,'Z')]));
 assert.deepEqual(staged.sources,[row('main.tex','AΩB\r\nC',5),row('part.tex','Zbc!',8),row('untouched.tex','same',3)]);
 assert.equal(original.sources[0].text,'A😀B\r\nC');assert.notEqual(staged.revision,original.revision);
 assert.equal(stageSourceEdits(original,request(original,[edit('main.tex',1,3,'😀')])).revision,original.revision);
 for(const [start,end]of [[2,2],[1,2],[2,3]])assert.throws(()=>stageSourceEdits(original,request(original,[edit('main.tex',start,end,'x')])),/Split Unicode scalar/);
});

test('staging rejects stale revisions, missing IDs, invalid ranges and ambiguous overlaps',()=>{
 const snapshot=createSourceSnapshot([row('a','abcd')]);
 assert.throws(()=>stageSourceEdits(snapshot,{expectedRevision:'stale',edits:[]}),/Stale/);
 for(const edits of [[edit('missing',0,0,'x')],[edit('a',-1,1,'x')],[edit('a',0,5,'x')],[edit('a',1.5,2,'x')],[edit('a',2,1,'x')]])assert.throws(()=>stageSourceEdits(snapshot,request(snapshot,edits)),/Invalid/);
 for(const edits of [[edit('a',0,2,'x'),edit('a',1,3,'y')],[edit('a',1,1,'x'),edit('a',1,1,'y')],[edit('a',1,1,'x'),edit('a',1,2,'y')]])assert.throws(()=>stageSourceEdits(snapshot,request(snapshot,edits)),/Overlapping/);
 assert.equal(stageSourceEdits(snapshot,request(snapshot,[edit('a',0,1,'X'),edit('a',1,2,'Y')])).sources[0].text,'XYcd');
 const full=createSourceSnapshot([row('a','x',Number.MAX_SAFE_INTEGER)]);
 assert.throws(()=>stageSourceEdits(full,request(full,[edit('a',0,1,'y')])),/exhausted/);
});

test('session commits source and complete replacement together and snapshots edits before await',async()=>{
 const oldReplacement={pages:['old']},session=createSourceEditSession([row('a','abc')],oldReplacement),before=session.current,ready=deferred();
 const edits=[edit('a',1,2,'X')],pending=session.apply(request(before.snapshot,edits),async candidate=>{assert.equal(candidate.sources[0].text,'aXc');await ready.promise;return {complete:true,replacement:{pages:['new']}};});
 edits[0].text='mutated';assert.equal(session.current,before);
 ready.resolve();const committed=await pending;
 assert.equal(committed,session.current);assert.equal(committed.snapshot.sources[0].text,'aXc');assert.deepEqual(committed.replacement,{pages:['new']});
 let called=false;assert.throws(()=>session.apply(request(before.snapshot,[]),()=>{called=true;}),/Stale/);assert.equal(called,false);
});

test('render throws, rejection, incomplete and unresolved replacements leave committed state unchanged',async()=>{
 const session=createSourceEditSession([row('a','abc')],{pages:['old']}),before=session.current;
 for(const render of [()=>{throw Error('render failed');},()=>Promise.reject(Error('render failed')),()=>({complete:false,replacement:{}}),()=>({complete:true}),()=>({complete:true,replacement:{},diagnostics:['bad']}),()=>({complete:true,replacement:{},unresolved:['missing']})]){
  await assert.rejects(session.apply(request(before.snapshot,[edit('a',0,1,'X')]),render));assert.equal(session.current,before);
 }
});

test('concurrent completion cannot overwrite a newer committed replacement',async()=>{
 const session=createSourceEditSession([row('a','abc')]),base=session.current.snapshot,slow=deferred();
 const first=session.apply(request(base,[edit('a',0,1,'X')]),()=>slow.promise);
 const second=await session.apply(request(base,[edit('a',0,1,'Y')]),()=>({complete:true,replacement:'second'}));
 slow.resolve({complete:true,replacement:'first'});
 await assert.rejects(first,/Stale source completion/);assert.equal(session.current,second);assert.equal(session.current.snapshot.sources[0].text,'Ybc');
});

test('failed concurrent requests do not revoke a valid preparation; no-op commits still reject old completions',async()=>{
 const session=createSourceEditSession([row('a','abc')]),base=session.current.snapshot,slow=deferred();
 const first=session.apply(request(base,[]),()=>slow.promise);
 await assert.rejects(session.apply(request(base,[]),()=>({complete:false,replacement:'bad'})),/Incomplete/);
 slow.resolve({complete:true,replacement:'valid'});await first;assert.equal(session.current.replacement,'valid');
 const stale=deferred(),pending=session.apply(request(base,[]),()=>stale.promise);
 await session.apply(request(base,[]),()=>({complete:true,replacement:'new no-op'}));
 stale.resolve({complete:true,replacement:'old no-op'});await assert.rejects(pending,/Stale source completion/);
 assert.equal(session.current.replacement,'new no-op');assert.equal(session.current.snapshot.revision,base.revision);
});
