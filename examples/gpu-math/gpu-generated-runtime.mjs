import {createLatexFieldRenderer} from './field-packet.mjs';
async function fetchAsset(base,name,binary=false) {
  const response=await fetch(new URL(name,base));
  if (!response.ok) throw Error(`Missing generated asset ${name}: ${response.status}`);
  return binary ? response.arrayBuffer() : response.text();
}
export async function createGeneratedLatex({device,format,metadata,base}) {
  const names=Object.keys(metadata.assets);
  const [arrays,computeSource,drawSource]=await Promise.all([
    Promise.all(names.map(n=>fetchAsset(base,n,true))),fetchAsset(base,'compute-field.wgsl'),fetchAsset(base,'mtsdf.wgsl')]);
  const assets=Object.fromEntries(names.map((n,i)=>[n,arrays[i]]));
  const bytes=assets['segments.bin'];
  if (metadata.schema!=='vkf.generated-latex-gpu/1' || bytes.byteLength!==metadata.segmentCount*16) throw Error('Invalid generated segment buffer');
  for (const name of names) {
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',assets[name])),v=>v.toString(16).padStart(2,'0')).join('');
    if (digest!==metadata.assets[name]) throw Error('Generated asset hash mismatch: '+name);
  }
  const textureInfo=metadata.texture;
  const [width,height]=textureInfo.size;
  if (maxDimension(width,height)>device.limits.maxTextureDimension2D || bytes.byteLength>device.limits.maxStorageBufferBindingSize) throw Error('Generated expression exceeds device limits');
  const module=device.createShaderModule({code:computeSource});
  const info=await module.getCompilationInfo();
  const errors=info.messages.filter(m=>m.type==='error');
  if (errors.length) throw Error(errors.map(m=>m.message).join('\n'));
  const pipeline=await device.createComputePipelineAsync({layout:'auto',compute:{module,entryPoint:'build'}});
  const buffers=Object.fromEntries(names.map(name=>{
    const data=assets[name];
    if(data.byteLength>device.limits.maxStorageBufferBindingSize) throw Error('Generated buffer exceeds device limits');
    const buffer=device.createBuffer({size:Math.max(data.byteLength,8),usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST});
    if(data.byteLength)device.queue.writeBuffer(buffer,0,data);
    return [name,buffer];
  }));
  const parameters=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
  const params=new ArrayBuffer(16), view=new DataView(params);
  view.setUint32(0,metadata.segmentCount,true);
  view.setFloat32(4,1/textureInfo.shapeUnitsPerTexel,true);
  view.setFloat32(8,textureInfo.paddingTexels,true);
  view.setFloat32(12,textureInfo.distanceRangeTexels,true);
  device.queue.writeBuffer(parameters,0,params);
  const texture=device.createTexture({size:[width,height],format:'rgba8unorm',
    usage:GPUTextureUsage.STORAGE_BINDING|GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_SRC});
  const bind=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[
    {binding:0,resource:{buffer:buffers['segments.bin']}},{binding:1,resource:texture.createView()},
    {binding:2,resource:{buffer:parameters}},
    ...['tile-ranges.bin','tile-indices.bin','row-ranges.bin','crossings.bin'].map((name,i)=>({binding:i+3,resource:{buffer:buffers[name]}}))]});
  const encoder=device.createCommandEncoder();
  const pass=encoder.beginComputePass();
  pass.setPipeline(pipeline);pass.setBindGroup(0,bind);
  pass.dispatchWorkgroups(Math.ceil(width/8),Math.ceil(height/8));pass.end();
  device.queue.submit([encoder.finish()]);await device.queue.onSubmittedWorkDone();
  Object.values(buffers).forEach(b=>b.destroy());parameters.destroy();
  const renderer=createLatexFieldRenderer({device,format,shaderSource:drawSource,texture:textureInfo,existingTexture:texture});
  return {texture,metadata,draw:renderer.draw,
    dispose(){renderer.dispose();texture.destroy();}};
}
function maxDimension(w,h){return Math.max(w,h);}
