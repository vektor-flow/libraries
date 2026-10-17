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
 @location(4) @interpolate(flat) parameters: vec4f,
 @location(5) @interpolate(flat) geometry: vec2f,
}
@vertex fn vs(@builtin(vertex_index) id:u32,@location(0) rect:vec4f,
 @location(1) uv:vec4f,@location(2) color:vec4f,@location(3) info:vec4f)->Out{
 let corners=array<vec2f,6>(vec2f(0,0),vec2f(1,0),vec2f(0,1),vec2f(0,1),vec2f(1,0),vec2f(1,1));
 let c=corners[id];var local=c*rect.zw;var p=rect.xy+local-view.unused;
 if(info.x>3.5){
  let pad=info.y*.5+1.0;
  if(info.x==4.0||info.x==6.0){
   var lo=min(vec2f(0),rect.zw);var hi=max(vec2f(0),rect.zw);
   if(info.x==6.0){lo=min(lo,min(uv.xy,uv.zw));hi=max(hi,max(uv.xy,uv.zw));}
   local=mix(lo-vec2f(pad),hi+vec2f(pad),c);p=rect.xy+local-view.unused;
  }else{local=mix(vec2f(-pad),rect.zw+vec2f(pad),c);p=rect.xy+local-view.unused;local-=rect.zw*.5;}
 }
 var o:Out;
 o.position=vec4f(2*p.x/view.size.x-1,1-2*p.y/view.size.y,0,1);
 o.uv=mix(uv.xy,uv.zw,c);o.color=color;o.info=info;o.local=local;o.parameters=uv;o.geometry=rect.zw;return o;
}
fn cubic(t:f32,a:vec2f,b:vec2f,c:vec2f)->vec2f{let u=1.0-t;return 3.0*u*u*t*a+3.0*u*t*t*b+t*t*t*c;}
fn vectorDistance(i:Out)->f32{
 let p=i.local;let half=i.info.y*.5;
 if(i.info.x==4.0){
  let len=length(i.geometry);if(len<1e-8){return 1e8;}
  let axis=i.geometry/len;let position=dot(p,axis);let across=dot(p,vec2f(-axis.y,axis.x));
  let d=vec2f(abs(position-len*.5)-len*.5,abs(across)-half);
  var result=length(max(d,vec2f(0)))+min(max(d.x,d.y),0.0);
  if(i.info.z>0.0){let period=i.info.z+i.info.w;let phase=position-floor(position/period)*period;result=max(result,abs(phase-i.info.z*.5)-i.info.z*.5);}
  return result;
 }
 if(i.info.x==6.0){
  let a=i.parameters.xy;let b=i.parameters.zw;let c=i.geometry;
  var best=length(p);var bestT=0.0;
  if(length(p-c)<best){best=length(p-c);bestT=1.0;}
  // Multiple independent starts cover the competing closest-point minima.
  for(var seed=0u;seed<5u;seed++){
   var t=f32(seed)*.25;
   for(var iteration=0u;iteration<8u;iteration++){
    let u=1.0-t;let q=cubic(t,a,b,c)-p;
    let velocity=3.0*u*u*a+6.0*u*t*(b-a)+3.0*t*t*(c-b);
    let acceleration=6.0*u*(b-2.0*a)+6.0*t*(c-2.0*b+a);
    let denominator=dot(velocity,velocity)+dot(q,acceleration);
    if(abs(denominator)<1e-9){break;}
    t=clamp(t-dot(q,velocity)/denominator,0.0,1.0);
   }
   let distance=length(cubic(t,a,b,c)-p);if(distance<best){best=distance;bestT=t;}
  }
  var distance=best-half;
  if(bestT<1e-6&&length(a)>1e-8){distance=max(distance,-dot(p,normalize(a)));}
  if(bestT>1.0-1e-6&&length(c-b)>1e-8){distance=max(distance,dot(p-c,normalize(c-b)));}
  return distance;
 }
 let extents=i.geometry*.5;var distance=0.0;
 if(i.info.x==5.0){distance=length(p)-extents.x;}
 else{let d=abs(p)-extents;distance=length(max(d,vec2f(0)))+min(max(d.x,d.y),0.0);}
 if(i.info.z>0.5){return distance;}
 return abs(distance)-half;
}
@fragment fn fs(i:Out)->@location(0) vec4f{
 let range=max(.5*dot(vec2f(8.0)/vec2f(textureDimensions(atlas)),1.0/max(fwidth(i.uv),vec2f(1e-8))),1.0);
 // World units covered by one physical fragment; evaluate before material branches.
 let pixelSize=max(fwidth(i.local),vec2f(1e-8));
 let sampled=textureSample(atlas,sampler0,i.uv);
 if(i.info.x>3.5){let distance=vectorDistance(i);let footprint=max(length(pixelSize)*.70710678,1e-6);let alpha=clamp(.5-distance/footprint,0.0,1.0)*i.color.a;return vec4f(i.color.rgb*alpha,alpha);}
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
  if(i.info.w!=0.0){let inside=max(half-vec2f(abs(i.info.w)),vec2f(0));let innerLo=max(p-pixelSize*.5,-inside);let innerHi=min(p+pixelSize*.5,inside);let innerArea=clamp((innerHi-innerLo)/pixelSize,vec2f(0),vec2f(1));coverage=max(0.0,coverage-innerArea.x*innerArea.y);if(i.info.w<0.0){coverage=select(0.0,1.0,all(abs(p)<=half)&&!all(abs(p)<inside));}}
 }
 let alpha=coverage*i.color.a;return vec4f(i.color.rgb*alpha,alpha);
}
