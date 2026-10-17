// Synthetic backend reused verbatim from fragment-session-incremental.mjs.
export function backend(){
 const resources=[],gates=[],commands=[];let uploads=0;let lossResolve;
 const d={auto:true,validation:null,throwWrite:false,lost:new Promise(r=>lossResolve=r),lose(){lossResolve({reason:'synthetic'});},limits:{maxTextureDimension2D:8192},
  pushErrorScope(){},async popErrorScope(){return d.validation;},
  createTexture(desc){const r={desc,kind:'texture',destroyed:0,destroy(){this.destroyed++;},createView(){return {texture:this};}};resources.push(r);return r;},
  createBuffer(desc){const r={desc,kind:'buffer',destroyed:0,destroy(){this.destroyed++;}};resources.push(r);return r;},
  createSampler:x=>x,createBindGroup:x=>x,
  createCommandEncoder(){if(d.encodeError)throw d.encodeError;const c={draws:[],beginRenderPass(){return {setPipeline(){},setVertexBuffer(i,b){c.buffer=b;},setBindGroup(i,b){c.bind=b;},draw(...args){c.draws.push({args,bind:c.bind});},end(){}};},finish(){if(d.finishError)throw d.finishError;return c;}};commands.push(c);return c;},
  queue:{writeTexture({texture},bytes,layout,size){if(d.throwWrite)throw Error('synthetic write failure');uploads++;texture.bytes=bytes.slice();texture.layout=layout;texture.size=size;},writeBuffer(buffer,offset,bytes){buffer.bytes=bytes.slice();if(d.writeError)throw d.writeError;},submit(c){if(d.submitError)throw d.submitError;d.submitted=c;},onSubmittedWorkDone(){if(d.fenceError)throw d.fenceError;return d.auto?Promise.resolve():new Promise((resolve,reject)=>gates.push({resolve,reject}));}},
  flush(){for(const x of gates.splice(0))x.resolve();},resources,commands,gates,get uploads(){return uploads;}};return d;
}
