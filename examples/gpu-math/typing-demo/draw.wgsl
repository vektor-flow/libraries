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
 let c=corners[id];let p=rect.xy+c*rect.zw-view.unused;var o:Out;
 o.position=vec4f(2*p.x/view.size.x-1,1-2*p.y/view.size.y,0,1);
 o.uv=mix(uv.xy,uv.zw,c);o.color=color;o.info=info;o.local=c*rect.zw;return o;
}
@fragment fn fs(i:Out)->@location(0) vec4f{
 let range=max(.5*dot(vec2f(8.0)/vec2f(textureDimensions(atlas)),1.0/max(fwidth(i.uv),vec2f(1e-8))),1.0);
 // World units covered by one physical fragment; evaluate before material branches.
 let pixelSize=max(fwidth(i.local),vec2f(1e-8));
 let sampled=textureSample(atlas,sampler0,i.uv);
 if(i.info.x>2.5){let alpha=sampled.a*i.color.a;return vec4f(i.color.rgb*alpha,alpha);}
 if(i.info.x>1.5){let alpha=sampled.a*i.color.a;return vec4f(sampled.rgb*i.color.rgb*alpha,alpha);}
 let v=sampled.rgb;
 let m=max(min(v.r,v.g),min(max(v.r,v.g),v.b));
 var coverage=clamp((m-.5)*range+.5,0.0,1.0);
 if(i.info.x>0.5){
  // Exact axis-aligned rectangle / pixel intersection. A fixed world-space
  // smoothing band grows when magnified; this footprint stays one screen pixel
  // and preserves the area of rules thinner than a pixel when zoomed out.
  let half=i.info.yz*.5;let p=i.local-(half+1);
  let lo=max(p-pixelSize*.5,-half);
  let hi=min(p+pixelSize*.5,half);
  let area=clamp((hi-lo)/pixelSize,vec2f(0),vec2f(1));
  coverage=area.x*area.y;
 }
 let alpha=coverage*i.color.a;return vec4f(i.color.rgb*alpha,alpha);
}
