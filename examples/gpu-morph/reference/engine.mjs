/** GPU-only correspondence and field transport. CPU supplies endpoint scene data. */
export class MorphEngine {
 static async create(canvas,mapping,atlasBytes,shader,{validation=false}={}) {
  const boot=performance.now();if(!navigator.gpu)throw Error('WebGPU is unavailable in this browser.');
  const adapter=await navigator.gpu.requestAdapter({powerPreference:'high-performance'});if(!adapter)throw Error('No WebGPU device is available.');
  const info=adapter.info;const software=info.isFallbackAdapter||/swiftshader|llvmpipe|software/i.test([info.description,info.vendor,info.architecture].join(' '));
  const local=['localhost','127.0.0.1'].includes(location.hostname);
  if(software&&!(validation&&local))throw Error('A software GPU was detected. This test requires a hardware GPU; no CPU fallback is used.');
  const timestamps=adapter.features.has('timestamp-query');const device=await adapter.requestDevice({requiredFeatures:timestamps?['timestamp-query']:[]});
  const self=new MorphEngine();Object.assign(self,{gpu:navigator.gpu,adapter,device,canvas,info,software,timestamps,errors:[],generation:0,ready:false,reads:new Set(),phase:0});
  device.addEventListener('uncapturederror',e=>{self.errors.push(e.error.message);self.ready=false;self.onError?.(e.error.message);});
  device.lost.then(i=>{self.ready=false;self.onError?.('GPU device lost: '+i.message);});
  const [w,h]=mapping.atlasSize;if(atlasBytes.byteLength!==w*h*4)throw Error('Invalid distance-field atlas length');
  self.atlas=device.createTexture({size:[w,h],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});device.queue.writeTexture({texture:self.atlas},atlasBytes,{bytesPerRow:w*4},[w,h]);
  self.sampler=device.createSampler({minFilter:'linear',magFilter:'linear'});self.uniform=device.createBuffer({size:32,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
  self.uniformBytes=new ArrayBuffer(32);self.u32=new Uint32Array(self.uniformBytes);self.f32=new Float32Array(self.uniformBytes);
  const header=shader.slice(0,shader.indexOf('@compute'));
  const flowIndex=shader.slice(shader.indexOf('fn flowIndex'),shader.indexOf('@compute @workgroup_size(64) fn relax'));
  const module=device.createShaderModule({code:shader.slice(0,shader.indexOf('fn ease'))});
  const renderCode=(header+flowIndex+shader.slice(shader.indexOf('fn ease'))).replace('var<storage,read_write> assignment','var<storage,read> assignment');
  const renderModule=device.createShaderModule({code:renderCode});
  for(const m of [module,renderModule]){const messages=await m.getCompilationInfo();const errors=messages.messages.filter(x=>x.type==='error');if(errors.length)throw Error(errors.map(x=>x.message).join('\n'));}
  const storage=b=>({binding:b,visibility:GPUShaderStage.COMPUTE,buffer:{type:[1,6].includes(b)?'read-only-storage':'storage'}});
  self.computeLayout=device.createBindGroupLayout({entries:[{binding:0,visibility:GPUShaderStage.COMPUTE,buffer:{type:'uniform'}},...[1,2,3,4,5,6,7].map(storage),{binding:8,visibility:GPUShaderStage.COMPUTE,texture:{}},{binding:9,visibility:GPUShaderStage.COMPUTE,sampler:{}}]});
  const computePipelineLayout=device.createPipelineLayout({bindGroupLayouts:[self.computeLayout]});self.compute={};
  for(const name of ['describe','compare','assign_pairs','relax'])self.compute[name]=await device.createComputePipelineAsync({layout:computePipelineLayout,compute:{module,entryPoint:name}});
  self.renderLayout=device.createBindGroupLayout({entries:[{binding:0,visibility:3,buffer:{type:'uniform'}},...[1,4,6].map(binding=>({binding,visibility:3,buffer:{type:'read-only-storage'}})),{binding:8,visibility:2,texture:{}},{binding:9,visibility:2,sampler:{}}]});
  const format=navigator.gpu.getPreferredCanvasFormat();self.context=canvas.getContext('webgpu');self.context.configure({device,format,alphaMode:'opaque'});
  self.renderPipeline=await device.createRenderPipelineAsync({layout:device.createPipelineLayout({bindGroupLayouts:[self.renderLayout]}),vertex:{module:renderModule,entryPoint:'vertex'},fragment:{module:renderModule,entryPoint:'fragment',targets:[{format,blend:{color:{srcFactor:'one',dstFactor:'one-minus-src-alpha'},alpha:{srcFactor:'one',dstFactor:'one-minus-src-alpha'}}}]},primitive:{topology:'triangle-list'}});
  await device.queue.onSubmittedWorkDone();self.bootMs=performance.now()-boot;return self;
 }
 timer(){
  if(!this.timestamps)return null;const d=this.device;
  return {query:d.createQuerySet({type:'timestamp',count:2}),resolve:d.createBuffer({size:16,usage:GPUBufferUsage.QUERY_RESOLVE|GPUBufferUsage.COPY_SRC}),read:d.createBuffer({size:16,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ})};
 }
 resolveTimer(encoder,timer){if(timer){encoder.resolveQuerySet(timer.query,0,2,timer.resolve,0);encoder.copyBufferToBuffer(timer.resolve,0,timer.read,0,16);}}
 async readTimer(timer){
  if(!timer)return null;
  try{await timer.read.mapAsync(GPUMapMode.READ);const times=new BigUint64Array(timer.read.getMappedRange());return Number(times[1]-times[0])/1e6;}
  finally{timer.read.unmap();timer.read.destroy();timer.resolve.destroy();timer.query.destroy();}
 }
 async generate(a,b,{grid=32,iterations=12}={}){
  this.ready=false;await this.device.queue.onSubmittedWorkDone();this.buffers?.forEach(x=>x.destroy());
  const started=performance.now(),d=this.device,n=Math.max(a.length,b.length)/16;if(!Number.isInteger(n)||n<1||n>1024)throw Error('Scene must contain1–1024 bodies.');
  if(a.length!==b.length)throw Error('Endpoint packets must be padded to equal length.');
  this.n=n;this.grid=grid;this.u32[0]=n;this.u32[1]=grid;this.f32[2]=0;this.f32[4]=this.canvas.width;this.f32[5]=this.canvas.height;d.queue.writeBuffer(this.uniform,0,this.uniformBytes);
  const buffer=(size,extra=0)=>d.createBuffer({size:Math.max(4,size),usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST|extra});
  const endpoints=buffer(a.byteLength+b.byteLength);d.queue.writeBuffer(endpoints,0,a);d.queue.writeBuffer(endpoints,a.byteLength,b);
  const descriptors=buffer(n*2*64*4),costs=buffer(n*n*4),assignment=buffer(n*4,GPUBufferUsage.COPY_SRC),used=buffer(n*4),flows=[buffer(n*grid*grid*8),buffer(n*grid*grid*8)];
  this.assignment=assignment;this.endpoints=endpoints;this.buffers=[endpoints,descriptors,costs,assignment,used,...flows];
  const base=[{binding:0,resource:{buffer:this.uniform}},{binding:1,resource:{buffer:endpoints}},{binding:2,resource:{buffer:descriptors}},{binding:3,resource:{buffer:costs}},{binding:4,resource:{buffer:assignment}},{binding:5,resource:{buffer:used}},{binding:8,resource:this.atlas.createView()},{binding:9,resource:this.sampler}];
  const binds=flows.map((f,i)=>d.createBindGroup({layout:this.computeLayout,entries:[...base,{binding:6,resource:{buffer:f}},{binding:7,resource:{buffer:flows[1-i]}}]}));
  this.computeBinds=binds;this.flows=flows;this.iterations=iterations;
  const finalFlow=flows[iterations%2];this.bind=d.createBindGroup({layout:this.renderLayout,entries:[base[0],base[1],base[4],base[6],base[7],{binding:6,resource:{buffer:finalFlow}}]});
  const timer=this.timer(),encoder=d.createCommandEncoder();
  const pass=encoder.beginComputePass(timer?{timestampWrites:{querySet:timer.query,beginningOfPassWriteIndex:0,endOfPassWriteIndex:1}}:{});
  pass.setBindGroup(0,binds[0]);pass.setPipeline(this.compute.describe);pass.dispatchWorkgroups(Math.ceil(n*2*64/64));
  pass.setPipeline(this.compute.compare);pass.dispatchWorkgroups(Math.ceil(n*n/64));pass.setPipeline(this.compute.assign_pairs);pass.dispatchWorkgroups(1);
  pass.setPipeline(this.compute.relax);for(let i=0;i<iterations;i++){pass.setBindGroup(0,binds[i%2]);pass.dispatchWorkgroups(Math.ceil(n*grid*grid/64));}pass.end();this.resolveTimer(encoder,timer);d.queue.submit([encoder.finish()]);
  const gpuMs=await this.readTimer(timer);await d.queue.onSubmittedWorkDone();this.ready=true;this.generation++;this.preparation={wallMs:performance.now()-started,gpuMs,bodies:n,grid,iterations};return this.preparation;
 }
 encodeSolve(encoder,timer){
  const n=this.n,g=this.grid;
  for(const f of this.flows)encoder.clearBuffer(f);
  const p=encoder.beginComputePass(timer?{timestampWrites:{querySet:timer.query,beginningOfPassWriteIndex:0}}:{});
  p.setBindGroup(0,this.computeBinds[0]);p.setPipeline(this.compute.describe);p.dispatchWorkgroups(Math.ceil(n*2*64/64));
  p.setPipeline(this.compute.compare);p.dispatchWorkgroups(Math.ceil(n*n/64));p.setPipeline(this.compute.assign_pairs);p.dispatchWorkgroups(1);
  p.setPipeline(this.compute.relax);for(let i=0;i<this.iterations;i++){p.setBindGroup(0,this.computeBinds[i%2]);p.dispatchWorkgroups(Math.ceil(n*g*g/64));}p.end();
 }
 draw(phase,{measure=false}={}){
  if(!this.ready)return Promise.resolve(null);const wallStart=performance.now(),d=this.device;this.phase=Math.max(0,Math.min(1,phase));this.f32[2]=this.phase;this.f32[4]=this.canvas.width;this.f32[5]=this.canvas.height;
  // Only controls cross the CPU/GPU boundary. Every frame recomputes descriptors,
  // all-pairs costs, assignment and flow from resident endpoint scenes.
  d.queue.writeBuffer(this.uniform,0,this.uniformBytes);const encoder=d.createCommandEncoder();const timer=measure?this.timer():null;
  this.encodeSolve(encoder,timer);
  const descriptor={colorAttachments:[{view:this.context.getCurrentTexture().createView(),clearValue:[.035,.055,.065,1],loadOp:'clear',storeOp:'store'}]};if(timer)descriptor.timestampWrites={querySet:timer.query,endOfPassWriteIndex:1};
  const pass=encoder.beginRenderPass(descriptor);pass.setPipeline(this.renderPipeline);pass.setBindGroup(0,this.bind);pass.draw(6,this.n);pass.end();this.resolveTimer(encoder,timer);d.queue.submit([encoder.finish()]);
  const submitMs=performance.now()-wallStart;
  return (async()=>{const gpuMs=await this.readTimer(timer);await d.queue.onSubmittedWorkDone();return {gpuMs,submitMs,wallMs:performance.now()-wallStart};})();
 }
 async inspectAssignment(){
  // Explicit verification path, never used for correspondence or playback.
  const d=this.device,r=d.createBuffer({size:this.n*4,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ}),e=d.createCommandEncoder();e.copyBufferToBuffer(this.assignment,0,r,0,this.n*4);d.queue.submit([e.finish()]);await r.mapAsync(GPUMapMode.READ);const values=Array.from(new Uint32Array(r.getMappedRange()));r.unmap();r.destroy();return values;
 }
}
