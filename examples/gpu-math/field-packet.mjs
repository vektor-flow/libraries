/** Position a complete LaTeX field in the shared GPU viewport. */
export function fieldInstance(texture, {x=0,y=0,unitsToPixels=1,color=[0,0,0,1]}={}) {
  const [width,height]=texture.size ?? [];
  const bounds=texture.quadBounds ?? [];
  if (texture.type !== 'mtsdf' || texture.format !== 'linear rgba8unorm' ||
      ![width,height].every(v=>Number.isInteger(v)&&v>0) || bounds.length!==4 ||
      ![...bounds,x,y,unitsToPixels,texture.distanceRangeTexels].every(Number.isFinite) ||
      bounds[2]<=bounds[0] || bounds[3]<=bounds[1] || unitsToPixels<=0 ||
      texture.distanceRangeTexels<=0 || color.length!==4 ||
      !color.every(v=>Number.isFinite(v)&&v>=0&&v<=1)) throw Error('Invalid LaTeX field placement');
  const data=[x+bounds[0]*unitsToPixels,y+bounds[1]*unitsToPixels,
    (bounds[2]-bounds[0])*unitsToPixels,(bounds[3]-bounds[1])*unitsToPixels,
    0,0,1,1,...color,texture.distanceRangeTexels,width,height,0];
  if (!data.every(v=>Number.isFinite(Math.fround(v)))) throw Error('Field exceeds float32 range');
  return new Float32Array(data);
}

/** Candidate WebGPU adapter. The host supplies its device and shared render pass.
 * Shader compilation, draw execution and browser/GPU acceptance remain unverified.
 */
export function createLatexFieldRenderer({device,format,shaderSource,texture,rgba}) {
  fieldInstance(texture); // Validate before allocating GPU resources.
  const [width,height]=texture.size;
  if (!(rgba instanceof Uint8Array) || rgba.byteLength!==width*height*4) throw Error('Expected raw linear RGBA bytes');
  if (width>device.limits.maxTextureDimension2D || height>device.limits.maxTextureDimension2D) throw Error('Field exceeds device texture limit');
  const image=device.createTexture({size:[width,height],format:'rgba8unorm',
    usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
  device.queue.writeTexture({texture:image},rgba,{bytesPerRow:width*4,rowsPerImage:height},[width,height]);
  const module=device.createShaderModule({code:shaderSource});
  const pipeline=device.createRenderPipeline({layout:'auto',
    vertex:{module,entryPoint:'vs',buffers:[{arrayStride:64,stepMode:'instance',attributes:
      [0,1,2,3].map(i=>({shaderLocation:i,offset:i*16,format:'float32x4'}))}]},
    fragment:{module,entryPoint:'fs',targets:[{format,blend:{
      color:{srcFactor:'one',dstFactor:'one-minus-src-alpha'},
      alpha:{srcFactor:'one',dstFactor:'one-minus-src-alpha'}}}]},
    primitive:{topology:'triangle-list'}});
  const uniform=device.createBuffer({size:16,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
  const instance=device.createBuffer({size:64,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
  const bind=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[
    {binding:0,resource:{buffer:uniform}},{binding:1,resource:image.createView()},
    {binding:2,resource:device.createSampler({minFilter:'linear',magFilter:'linear',addressModeU:'clamp-to-edge',addressModeV:'clamp-to-edge'})}]});
  let disposed=false;
  return {
    draw(pass,{viewport,...placement}) {
      if (disposed) throw Error('LaTeX field renderer disposed');
      if (!viewport || viewport.length!==2 || !viewport.every(v=>Number.isFinite(v)&&v>0&&Number.isFinite(Math.fround(v)))) throw Error('Invalid viewport');
      device.queue.writeBuffer(uniform,0,new Float32Array([...viewport,0,0]));
      device.queue.writeBuffer(instance,0,fieldInstance(texture,placement));
      pass.setPipeline(pipeline);pass.setBindGroup(0,bind);pass.setVertexBuffer(0,instance);
      pass.draw(6,1);
    },
    dispose() {if (!disposed) {image.destroy();uniform.destroy();instance.destroy();disposed=true;}}
  };
}
