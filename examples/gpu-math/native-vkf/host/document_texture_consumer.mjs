// Production consumer adapter; frozen document-demo.mjs remains a reference oracle.
// Takes ownership of an E300 snapshot lease on replace(), including failure.
// Metadata/typed columns must come from the source owner; no name-derived IDs.
export function createDocumentTextureConsumer({device,pipeline}) {
 let active=null,closed=false,lost=false,epoch=0,serial=Promise.resolve();
 const states=new Set(),draws=new Set(),pending=new Set();
 // Entries exist only while owned by live generation states. Draw references
 // retain their state until actual completion, including cancellation fences.
 const textures=new Map(),samplers=[],instances=new Set();
 // Private key cannot collide with any producer document/resource/version key.
 const neutralKey=Symbol("analytic-rule-neutral");
 function releaseInstance(e){if(e&&--e.refs===0){instances.delete(e);destroy(e.buffer);}}
 const sameDescriptor=(a,b)=>['format','width','height','bytesPerRow','alphaMode'].every(k=>a[k]===b[k]);
 const sameBytes=(a,b)=>a.byteLength===b.byteLength&&a.every((x,i)=>x===b[i]);
 function releaseTexture(e){if(--e.refs===0){textures.delete(e.key);destroy(e.texture);}}
 let lossResolve;const loss=new Promise(r=>lossResolve=r);
 const destroy=r=>{if(!lost)r?.destroy();};
 function free(s){if(s.freed)return;s.freed=true;states.delete(s);for(const e of s.entries)releaseTexture(e);releaseInstance(s.instance);s.lease.release();}
 function drop(s){if(--s.refs===0)free(s);}
 function failDevice(){if(lost)return;lost=true;closed=true;epoch++;lossResolve();active=null;for(const d of [...draws])d.release();for(const s of [...states])free(s);}
 device.lost.then(failDevice,failDevice);
 function track(p){pending.add(p);p.then(()=>pending.delete(p),()=>pending.delete(p));return p;}
 async function fence(){const ok=await Promise.race([device.queue.onSubmittedWorkDone().then(()=>true,()=>{failDevice();return false;}),loss.then(()=>false)]);if(!ok)throw Error('Device unavailable');}
 function clear(){epoch++;if(active){drop(active);active=null;}}
 async function upload(lease,ticket){
  const s={lease,refs:1,textures:new Map(),entries:[],buffer:null,instance:null,freed:false};states.add(s);
  let scoped=false,writeAttempted=false,error=null;
  try{
   if(closed||ticket!==epoch)throw Error('Cancelled replacement');
   let source=lease.bytes(),v=new DataView(source.buffer,source.byteOffset,source.byteLength);
   // E300 stores the canonical tagged f64 ABI, not packed vertex bytes.
   // Exact full canonical bytes identify immutable packed entries, owned only by live states.
   // Equality is linear and includes padding/tags; caller storage is never retained.
   if(source.byteLength!==16+lease.count*340||v.getUint32(0,true)!==4||v.getUint32(4,true)!==lease.count||v.getUint32(8,true)!==16)throw Error('Invalid instance extent');
   let instance=[...instances].find(e=>e.count===lease.count&&sameBytes(source,e.source));
   const bytes=instance?.bytes??new Float32Array(lease.count*16);
   if(!instance){
   source=new Uint8Array(source);v=new DataView(source.buffer);
   for(let i=0;i<lease.count;i++){
    const row=16+lease.count*4+i*336,values=row+16,numbers=values+64;
    if(v.getUint32(16+i*4,true)!==row||v.getUint32(row,true)!==4||v.getUint32(row+4,true)!==16||v.getUint32(row+8,true)!==values)throw Error('Invalid instance row');
    for(let j=0;j<16;j++){const n=numbers+j*16;if(v.getUint32(values+j*4,true)!==n||v.getUint32(n,true)!==2)throw Error('Invalid instance number');const x=v.getFloat64(n+8,true);if(!Number.isFinite(x)||!Number.isFinite(Math.fround(x)))throw Error('Invalid instance value');bytes[i*16+j]=x;}
   }
   }
   // Freeze every draw binding and validate every descriptor before any upload.
   // First matching record wins, as with Array.find; do not overwrite duplicates.
   const images=new Map(),glyphs=new Map();
   for(const image of lease.metadata.images)if(!images.has(image.leaf))images.set(image.leaf,image);
   for(const glyph of lease.metadata.glyphs??[])if(!glyphs.has(glyph.leaf))glyphs.set(glyph.leaf,glyph);
   s.bindings=Array.from({length:lease.count},(_,i)=>{
    const kind=bytes[i*16+12],image=images.get(i),glyph=glyphs.get(i),ids=lease.metadata.leafResources[i];
    const id=kind===0?(glyph?.resourceId??(ids.length===1?ids[0]:undefined)):kind===2?image?.resourceId:(ids.length===1?ids[0]:null);
    if((kind===0||kind===2)&&(!id||!ids.includes(id)))throw Error('Missing explicit draw resource');
    return {id,image:!!image,kind,neutral:kind===1&&ids.length===0};
   });
   const resourceIds=new Set();
   const decoded=lease.metadata.resources.map(({id,version})=>{
    if(resourceIds.has(id))throw Error('Duplicate resource ID');
    resourceIds.add(id);
    const d=lease.resourceDescriptor(id),raw=lease.resource(id);
    if(!d||d.format!=='rgba8unorm'||d.alphaMode!=='straight'||!Number.isSafeInteger(d.width)||d.width<=0||!Number.isSafeInteger(d.height)||d.height<=0||d.width*d.height>16777216||d.bytesPerRow!==d.width*4||raw.byteLength!==d.bytesPerRow*d.height)throw Error('Missing decoded RGBA resource');
    const key=JSON.stringify([lease.metadata.documentId,id,version]),entry=textures.get(key);
    if(entry&&(!sameDescriptor(d,entry.descriptor)||!sameBytes(raw,entry.bytes)))throw Error('Immutable resource version changed');
    return {id,d,raw,key,entry};
   });
   if(s.bindings.some(b=>b.id!==null&&(b.id!==b.id||!resourceIds.has(b.id))))throw Error('Unknown draw resource');
   device.pushErrorScope('validation');scoped=true;
   // draw.wgsl samples before the tag1 branch replaces coverage analytically.
   // Own this binding exactly like uploaded resources: generation/draw references
   // and attempted-write fences govern retirement, including failed replacement.
   if(s.bindings.some(b=>b.neutral)){
    let e=textures.get(neutralKey);
    if(e){e.refs++;s.entries.push(e);s.neutral=e.texture;}
    else {
     const t=device.createTexture({size:[1,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
     e={key:neutralKey,texture:t,refs:1};textures.set(neutralKey,e);s.entries.push(e);s.neutral=t;
     writeAttempted=true;
     device.queue.writeTexture({texture:t},new Uint8Array([255,255,255,255]),{bytesPerRow:4,rowsPerImage:1},[1,1]);
    }
   }
   for(const {id,d,raw,key,entry} of decoded){
    if(entry){entry.refs++;s.entries.push(entry);s.textures.set(id,entry.texture);continue;}
    if(!d||d.format!=='rgba8unorm'||d.alphaMode!=='straight'||d.bytesPerRow!==d.width*4||raw.byteLength!==d.bytesPerRow*d.height)throw Error('Missing decoded RGBA resource');
    const t=device.createTexture({size:[d.width,d.height],format:d.format,usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});s.textures.set(id,t);
    const e={key,texture:t,refs:1,descriptor:{...d},bytes:new Uint8Array(raw)};
    textures.set(key,e);s.entries.push(e);
    writeAttempted=true;
    device.queue.writeTexture({texture:t},raw,{bytesPerRow:d.bytesPerRow,rowsPerImage:d.height},[d.width,d.height]);
   }
   if(instance){instance.refs++;s.instance=instance;s.buffer=instance.buffer;}
   else {
    // Snapshot before handing any data to the queue; never rewrite a live buffer.
    const identity=source;
    s.buffer=device.createBuffer({size:Math.max(4,bytes.byteLength),usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
    instance={count:lease.count,source:identity,bytes,buffer:s.buffer,refs:1};
    s.instance=instance;instances.add(instance);
    if(bytes.byteLength){writeAttempted=true;device.queue.writeBuffer(s.buffer,0,bytes);}
   }
  }catch(e){error=e;}
  if(scoped){try{const e=await Promise.race([device.popErrorScope(),loss.then(()=>new Error('Device unavailable'))]);if(e)error??=e;}catch(e){error??=e;}}
  // Even rejected writes may have queued work. Never retire them before completion.
  // Unobservable attempted writes require terminal CPU-only retirement.
  // Before any write, ordinary cleanup is safe and needs no queue fence.
  try{if((writeAttempted||s.instance)&&!lost)await Promise.race([device.queue.onSubmittedWorkDone(),loss.then(()=>{throw Error('Device unavailable');})]);}catch(e){failDevice();error??=e;}
  if(error||closed||ticket!==epoch){free(s);throw error??Error('Cancelled replacement');}
  const old=active;active=s;if(old)drop(old);return lease.generation;
 }
 function replace(lease){const ticket=++epoch;const p=serial.then(()=>upload(lease,ticket));serial=p.catch(()=>{});return track(p);}
 function encodePage(draw,zoom=1,origin=[0,0]){
  if(closed||!active)throw Error('No active snapshot');
  const s=active,{canvas,context,scale}=draw;
  if(!Number.isFinite(scale)||scale<=0||!Number.isFinite(zoom)||zoom<=0||origin.length!==2||!origin.every(Number.isFinite))throw Error('Invalid view');
  s.refs++;let uniform,done=false,used=false,writeAttempted=false,retirement;
  const handle={cancel(){if(!used){used=true;retire();}},release(){if(done)return;done=true;draws.delete(handle);destroy(uniform);drop(s);}};draws.add(handle);
  function retire(){
   if(retirement)return retirement;
   if(!writeAttempted||lost){handle.release();return Promise.resolve();}
   // Includes attempted writes and possibly accepted throwing submits. A fence
   // acquisition failure is terminal, just like a rejected completion.
   retirement=track((async()=>{try{await fence();}catch(e){failDevice();throw e;}finally{handle.release();}})());
   return retirement;
  }
  try{
   uniform=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
   writeAttempted=true;
   device.queue.writeBuffer(uniform,0,new Float32Array([canvas.width/(scale*zoom),canvas.height/(scale*zoom),...origin]));
   const target=context.getCurrentTexture(),encoder=device.createCommandEncoder();
   const pass=encoder.beginRenderPass({colorAttachments:[{view:target.createView(),clearValue:[1,1,1,1],loadOp:'clear',storeOp:'store'}]});
   pass.setPipeline(pipeline);pass.setVertexBuffer(0,s.buffer);
   // Cache only within this draw: every bind group owns this exact uniform.
   const bindings=new Map();
   for(let i=0;i<s.lease.count;i++){
    const binding=s.bindings[i],image=binding.image;
    const id=binding.id??draw.defaultResourceId,texture=binding.neutral?s.neutral:s.textures.get(id);
    if(!texture)throw Error('Missing explicit draw resource');
    const policy=image?1:0;
    let byPolicy=bindings.get(texture);if(!byPolicy){byPolicy=[];bindings.set(texture,byPolicy);}
    let bind=byPolicy[policy];
    if(!bind){
     const sampler=samplers[policy]??(samplers[policy]=device.createSampler({minFilter:'linear',magFilter:image?'nearest':'linear'}));
     bind=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}},{binding:1,resource:texture.createView()},{binding:2,resource:sampler}]});
     byPolicy[policy]=bind;
    }
    pass.setBindGroup(0,bind);pass.draw(6,1,0,i);
   }
   pass.end();
   return Object.freeze({generation:s.lease.generation,target,encoder,
    submit(){if(used||done)throw Error('Draw already consumed');used=true;
     try{device.queue.submit([encoder.finish()]);}catch(e){retire();throw e;}
     return retire();},
    cancel(){handle.cancel();}
   });
  }catch(e){used=true;retire();throw e;}
 }
 return Object.freeze({replace,encodePage,clearDocumentProject:clear,
  get generation(){return active?.lease.generation??null;},
  dispose(){if(closed)return;closed=true;clear();for(const d of [...draws])d.cancel();},
  async drained(){while(pending.size)await Promise.allSettled([...pending]);}
 });
}
