struct View { size: vec2f, unused: vec2f }
@group(0) @binding(0) var<uniform> view: View;
@group(0) @binding(1) var atlas: texture_2d<f32>;
@group(0) @binding(2) var sampler0: sampler;
struct Out {
 @builtin(position) position: vec4f,
 @location(0) uv: vec2f,
 @location(1) color: vec4f,
 @location(2) @interpolate(flat) info: vec4f,
 @location(3) local: vec2f,
}
@vertex fn vs(@builtin(vertex_index) id:u32,@location(0) rect:vec4f,
 @location(1) uv:vec4f,@location(2) color:vec4f,@location(3) info:vec4f)->Out{
 let corners=array<vec2f,6>(vec2f(0,0),vec2f(1,0),vec2f(0,1),vec2f(0,1),vec2f(1,0),vec2f(1,1));
 let c=corners[id];let p=rect.xy+c*rect.zw;var o:Out;
 o.position=vec4f(2*p.x/view.size.x-1,1-2*p.y/view.size.y,0,1);
 o.uv=mix(uv.xy,uv.zw,c);o.color=color;o.info=info;o.local=c*rect.zw;return o;
}
@fragment fn fs(i:Out)->@location(0) vec4f{
 let v=textureSample(atlas,sampler0,i.uv).rgb;
 let m=max(min(v.r,v.g),min(max(v.r,v.g),v.b));
 let range=max(.5*dot(vec2f(8.0/2048.0),1.0/max(fwidth(i.uv),vec2f(1e-8))),1.0);
 var coverage=clamp((m-.5)*range+.5,0.0,1.0);
 if(i.info.x>0.5){
  let half=i.info.yz*.5;let d=abs(i.local-(half+1))-half;
  let distance=length(max(d,vec2f(0)))+min(max(d.x,d.y),0.0);
  coverage=clamp(.5-distance,0.0,1.0);
 }
 let alpha=coverage*i.color.a;return vec4f(i.color.rgb*alpha,alpha);
}
