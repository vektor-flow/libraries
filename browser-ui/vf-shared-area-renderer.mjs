import {buildScreenSpaceSimplexVertices} from 'vektor-flow/screen-simplex-renderer';
import {COVERAGE_POLICY,areaSampleOffsets} from './vf-stroke-contract.mjs';
const failure=(message,status='FAIL')=>Object.assign(Error(message),{status,code:message});
export function areaTarget({cssWidth,cssHeight,pixelRatio=1,samplesPerAxis=COVERAGE_POLICY.samplesPerAxis,maxTextureSize=16384,maxBytes=536870912}) {
  areaSampleOffsets(samplesPerAxis);
  if(![cssWidth,cssHeight,pixelRatio].every(x=>Number.isFinite(x)&&x>0))throw failure('PLOT_COVERAGE_VIEWPORT');
  const width=Math.max(1,Math.round(cssWidth*pixelRatio)),height=Math.max(1,Math.round(cssHeight*pixelRatio));
  const areaWidth=width*samplesPerAxis,areaHeight=height*samplesPerAxis,bytes=areaWidth*areaHeight*4;
  if(areaWidth>maxTextureSize||areaHeight>maxTextureSize||bytes>maxBytes)throw failure('PLOT_COVERAGE_TARGET_BUDGET','BLOCKED');
  return Object.freeze({width,height,areaWidth,areaHeight,bytes,samplesPerAxis,cssWidth,cssHeight,pixelRatio});
}
// Exact accepted vector geometry is re-rasterized at centered area samples and
// box resolved in premultiplied space. Zoom never enlarges an old bitmap.
// Shared triangle edges are resolved once after the whole scene is drawn.
export function createSharedAreaRenderer(canvas,options={}) {
  const ratio=options.pixelRatio??(()=>globalThis.devicePixelRatio||1);
  const sampleCount=options.samplesPerAxis??COVERAGE_POLICY.samplesPerAxis;
  areaSampleOffsets(sampleCount);
  let gl=null,paint=null,resolve=null,buffer=null,texture=null,framebuffer=null,vao=null;
  let cssWidth=1,cssHeight=1,target=null,vertices=new Float32Array(),closed=false,capacity=0;
  const live=()=>{if(closed)throw failure('PLOT_COVERAGE_CLOSED')};
  function shader(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)){const log=gl.getShaderInfoLog(s);gl.deleteShader(s);throw failure('PLOT_COVERAGE_SHADER: '+log)}return s;}
  function program(v,f){const p=gl.createProgram(),vs=shader(gl.VERTEX_SHADER,v);let fs;
    try{fs=shader(gl.FRAGMENT_SHADER,f);gl.attachShader(p,vs);gl.attachShader(p,fs);gl.linkProgram(p);
      if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw failure('PLOT_COVERAGE_LINK: '+gl.getProgramInfoLog(p));return p;
    }catch(error){gl.deleteProgram(p);throw error}finally{gl.deleteShader(vs);if(fs)gl.deleteShader(fs)}}
  async function initialize(){live();gl=canvas.getContext('webgl2',{alpha:true,antialias:false,premultipliedAlpha:true});
    if(!gl)throw failure('PLOT_AREA_WEBGL2_UNAVAILABLE','BLOCKED');
    try{
      paint=program(`#version 300 es
        layout(location=0) in vec2 position; layout(location=1) in vec4 color;
        uniform vec2 viewport; out vec4 rgba;
        void main(){gl_Position=vec4(position.x/viewport.x*2.-1.,1.-position.y/viewport.y*2.,0.,1.);rgba=color;}`,
      `#version 300 es
        precision highp float; in vec4 rgba; out vec4 result;
        void main(){result=vec4(rgba.rgb*rgba.a,rgba.a);}`);
      resolve=program(`#version 300 es
        void main(){vec2 p=vec2(float((gl_VertexID<<1)&2),float(gl_VertexID&2));gl_Position=vec4(p*2.-1.,0.,1.);}`,
      `#version 300 es
        precision highp float; precision highp int;
        uniform highp sampler2D area; uniform int samples; out vec4 result;
        void main(){ivec2 base=ivec2(gl_FragCoord.xy)*samples;vec4 sum=vec4(0.);
          for(int y=0;y<8;y++){if(y>=samples)break;for(int x=0;x<8;x++){if(x>=samples)break;sum+=texelFetch(area,base+ivec2(x,y),0);}}
          result=sum/float(samples*samples);}`);
      buffer=gl.createBuffer();texture=gl.createTexture();framebuffer=gl.createFramebuffer();vao=gl.createVertexArray();
      resize(canvas.clientWidth||cssWidth,canvas.clientHeight||cssHeight);return 'webgl2-area';
    }catch(error){destroy();throw error}
  }
  function resize(width=canvas.clientWidth,height=canvas.clientHeight){live();cssWidth=Math.max(1,Number(width)||1);cssHeight=Math.max(1,Number(height)||1);
    if(!gl)return;
    const next=areaTarget({cssWidth,cssHeight,pixelRatio:ratio(),samplesPerAxis:sampleCount,maxTextureSize:gl.getParameter(gl.MAX_TEXTURE_SIZE),maxBytes:options.maxCoverageBytes??536870912});
    if(canvas.width!==next.width)canvas.width=next.width;if(canvas.height!==next.height)canvas.height=next.height;
    if(!target||target.areaWidth!==next.areaWidth||target.areaHeight!==next.areaHeight){
      gl.bindTexture(gl.TEXTURE_2D,texture);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,next.areaWidth,next.areaHeight,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
      gl.bindFramebuffer(gl.FRAMEBUFFER,framebuffer);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,texture,0);
      if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw failure('PLOT_COVERAGE_FRAMEBUFFER','BLOCKED');
    }
    target=next;draw();
  }
  function draw(){if(!gl||!target)return;
    gl.bindVertexArray(vao);gl.bindFramebuffer(gl.FRAMEBUFFER,framebuffer);gl.viewport(0,0,target.areaWidth,target.areaHeight);
    gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(paint);gl.uniform2f(gl.getUniformLocation(paint,'viewport'),cssWidth,cssHeight);gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    if(capacity<vertices.byteLength){capacity=Math.max(256,vertices.byteLength);gl.bufferData(gl.ARRAY_BUFFER,capacity,gl.DYNAMIC_DRAW)}
    if(vertices.length){gl.bufferSubData(gl.ARRAY_BUFFER,0,vertices);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,24,0);gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,4,gl.FLOAT,false,24,8);gl.drawArrays(gl.TRIANGLES,0,vertices.length/6)}
    gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,target.width,target.height);gl.disable(gl.BLEND);gl.useProgram(resolve);
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);gl.uniform1i(gl.getUniformLocation(resolve,'area'),0);gl.uniform1i(gl.getUniformLocation(resolve,'samples'),sampleCount);gl.drawArrays(gl.TRIANGLES,0,3);gl.bindVertexArray(null);
  }
  function setPackedVertices(next){live();if(!(next instanceof Float32Array)||next.length%18)throw failure('PLOT_COVERAGE_TRIANGLES');vertices=next;draw()}
  function destroy(){if(closed)return;closed=true;vertices=new Float32Array();if(gl){if(buffer)gl.deleteBuffer(buffer);if(texture)gl.deleteTexture(texture);if(framebuffer)gl.deleteFramebuffer(framebuffer);if(vao)gl.deleteVertexArray(vao);if(paint)gl.deleteProgram(paint);if(resolve)gl.deleteProgram(resolve)}gl=null;target=null}
  return Object.freeze({initialize,resize,setPackedVertices,setScene:scene=>setPackedVertices(buildScreenSpaceSimplexVertices(scene)),destroy,
    get backend(){return gl?'webgl2-area':null},coveragePolicy:()=>Object.freeze({...COVERAGE_POLICY,samplesPerAxis:sampleCount,target})});
}
