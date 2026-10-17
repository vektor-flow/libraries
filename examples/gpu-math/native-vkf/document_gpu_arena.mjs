// VKF-to-WebGPU transport. This adapter does no LaTeX/layout work and never
// decodes per-instance objects. Compute and draw share one resident GPUBuffer.
const encoder=new TextEncoder(),decoder=new TextDecoder('utf-8',{fatal:true});
export async function createDocumentGpuArena({device,instance,manifest,shader}){
 const e=instance.exports,slot=e.vkf_vm_value_slot_size();
 if(![16,24].includes(slot)||!(e.memory instanceof WebAssembly.Memory)||manifest.schema!=='vektor-flow.symbolic-kernel')throw Error('Unsupported VKF kernel ABI');
 const module=device.createShaderModule({code:shader});
 const info=await module.getCompilationInfo();
 if(info.messages.some(x=>x.type==='error'))throw Error(info.messages.map(x=>x.message).join('\n'));
 const pipeline=await device.createComputePipelineAsync({layout:'auto',compute:{module,entryPoint:'pack'}});
 const uniform=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
 const errors=device.createBuffer({size:4,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|GPUBufferUsage.COPY_SRC});
 let raw,output,mapping,rawCapacity=0,outputCapacity=0,mappingCapacity=0,binding,destroyed=false,generation=0;
 const metrics={allocations:2,commits:0,uploadedBytes:0,instanceBytes:0,scannedNumericSlots:0,decodedInstanceObjects:0,jsonParses:0};
 const view=()=>new DataView(e.memory.buffer);
 const range=(p,n)=>{if(!Number.isSafeInteger(p)||p<0||!Number.isSafeInteger(n)||n<0||p+n>e.memory.buffer.byteLength)throw Error('Invalid VKF memory range');};
 const field=(root,name)=>{
  range(root,slot);const v=view();if(v.getUint32(root,true)!==5)throw Error('GPU packet must be a record');
  const count=v.getUint32(root+4,true),entries=v.getUint32(root+8,true);range(entries,count*8);
  for(let i=0;i<count;i++){
   const key=v.getUint32(entries+i*8,true);range(key,slot);if(v.getUint32(key,true)!==3)throw Error('Invalid VKF record key');
   const p=v.getUint32(key+8,true),n=v.getUint32(key+4,true);range(p,n);
   if(decoder.decode(new Uint8Array(e.memory.buffer,p,n))===name)return v.getUint32(entries+i*8+4,true);
  }throw Error('Missing GPU packet field: '+name);
 };
 const number=p=>{range(p,slot);if(view().getUint32(p,true)!==2)throw Error('GPU packet header must be numeric');return view().getFloat64(p+8,true);};
 const writeArgument=(p,value)=>{
  range(p,slot);new Uint8Array(e.memory.buffer,p,slot).fill(0);
  if(typeof value==='number'&&Number.isFinite(value)){view().setUint32(p,2,true);view().setFloat64(p+8,value,true);return;}
  if(typeof value==='string'){
   const bytes=encoder.encode(value),at=e.vkf_vm_alloc(bytes.length);range(at,bytes.length);new Uint8Array(e.memory.buffer,at,bytes.length).set(bytes);
   const v=view();v.setUint32(p,3,true);v.setUint32(p+4,bytes.length,true);v.setUint32(p+8,at,true);return;
  }throw Error('GPU entry accepts numeric or UTF-8 boundary arguments');
 };
 function commit(entry,args=[]){
  if(destroyed)throw Error('GPU arena was disposed');
  const signature=manifest.functions[entry];if(!signature||signature.parameters!==args.length||args.length>e.vkf_vm_arguments_capacity())throw Error('Invalid VKF GPU entry signature');
  const checkpoint=e.vkf_vm_heap_ptr();
  try{
   args.forEach((x,i)=>writeArgument(e.vkf_vm_arguments_ptr()+i*slot,x));
   const status=e.vkf_vm_invoke(signature.index,args.length);if(status!==0)throw Error('VKF GPU invocation failed: '+status);
   const root=e.vkf_vm_results_ptr(),rows=field(root,'rows'),count=number(field(root,'count')),stride=number(field(root,'stride')),revision=number(field(root,'revision'));
   if(!Number.isSafeInteger(count)||count<0||stride!==64||!Number.isSafeInteger(revision))throw Error('Invalid GPU packet header');
   range(rows,slot);const v=view();if(v.getUint32(rows,true)!==4||v.getUint32(rows+4,true)!==count)throw Error('Invalid GPU row array');
   const entries=v.getUint32(rows+8,true);range(entries,count*4);
   // Follow only pointer metadata, never materializing numeric values or
   // per-instance objects. Upload reachable memory pages directly from WASM.
   const needed=Math.max(4,count*stride);
   if(needed>device.limits.maxStorageBufferBindingSize)throw Error('GPU instances exceed storage binding limits');
   const pageSize=4096,marked=new Uint8Array(Math.ceil(e.memory.buffer.byteLength/pageSize));
   let firstPage=marked.length,lastPage=0;
   const mark=(p,n)=>{range(p,n);if(n===0)return;const first=Math.floor(p/pageSize),last=Math.floor((p+n-1)/pageSize);for(let i=first;i<=last;i++)marked[i]=1;firstPage=Math.min(firstPage,first);lastPage=Math.max(lastPage,last);};
   mark(rows,slot);mark(entries,count*4);
   for(let i=0;i<count;i++){
    const row=v.getUint32(entries+i*4,true);mark(row,slot);
    if(v.getUint32(row,true)!==4||v.getUint32(row+4,true)!==16)throw Error('Invalid numeric GPU row');
    const values=v.getUint32(row+8,true);mark(values,16*4);
    for(let j=0;j<16;j++)mark(v.getUint32(values+j*4,true),slot);
   }
   const chunks=[];let bytes=0;
   for(let i=firstPage;i<=lastPage;){
    if(!marked[i]){i++;continue;}
    const start=i*pageSize;while(i<=lastPage&&marked[i])i++;
    const end=Math.min(i*pageSize,e.memory.buffer.byteLength);
    chunks.push({start,end,offset:bytes});bytes+=end-start;
   }
   if(bytes>device.limits.maxStorageBufferBindingSize)throw Error('Reachable GPU data exceeds storage binding limits');
   const table=new Uint32Array(chunks.length*4);
   chunks.forEach((chunk,i)=>table.set([chunk.start,chunk.end,chunk.offset/4,0],i*4));
   let changed=false;
   if(!raw||bytes>rawCapacity){raw?.destroy();rawCapacity=Math.max(4,2**Math.ceil(Math.log2(Math.max(4,bytes))));raw=device.createBuffer({size:rawCapacity,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST});metrics.allocations++;changed=true;}
   if(!output||needed>outputCapacity){output?.destroy();outputCapacity=2**Math.ceil(Math.log2(needed));output=device.createBuffer({size:outputCapacity,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_SRC});metrics.allocations++;changed=true;}
   if(!mapping||table.byteLength>mappingCapacity){mapping?.destroy();mappingCapacity=Math.max(16,2**Math.ceil(Math.log2(table.byteLength)));mapping=device.createBuffer({size:mappingCapacity,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST});metrics.allocations++;changed=true;}
   if(changed||!binding)binding=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:raw}},{binding:1,resource:{buffer:output}},{binding:2,resource:{buffer:uniform}},{binding:3,resource:{buffer:errors}},{binding:4,resource:{buffer:mapping}}]});
   for(const chunk of chunks)device.queue.writeBuffer(raw,chunk.offset,new Uint8Array(e.memory.buffer,chunk.start,chunk.end-chunk.start));
   device.queue.writeBuffer(mapping,0,table);
   device.queue.writeBuffer(uniform,0,new Uint32Array([rows,count,chunks.length,0]));device.queue.writeBuffer(errors,0,new Uint32Array([0]));
   // Empty edits retain the allocation and clear validation state, but have no
   // instances to convert. Avoid a command buffer and zero-sized dispatch.
   if(count>0){const commands=device.createCommandEncoder(),pass=commands.beginComputePass();pass.setPipeline(pipeline);pass.setBindGroup(0,binding);pass.dispatchWorkgroups(Math.ceil(count*16/64));pass.end();device.queue.submit([commands.finish()]);}
   metrics.commits++;metrics.uploadedBytes+=bytes+table.byteLength;metrics.scannedNumericSlots+=count*16;metrics.instanceBytes+=count*stride;generation++;
   return Object.freeze({buffer:output,errorBuffer:errors,count,stride,revision,generation});
  }finally{if(e.vkf_vm_rewind(checkpoint)!==checkpoint)throw Error('VKF allocation checkpoint was not restored');}
 }
 function dispose(){if(!destroyed){destroyed=true;raw?.destroy();output?.destroy();mapping?.destroy();uniform.destroy();errors.destroy();}}
 return Object.freeze({commit,dispose,metrics});
}
