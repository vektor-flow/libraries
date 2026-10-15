struct Params { count:u32, grid:u32, phase:f32, pad:f32, view:vec2f, unused:vec2f }
struct Item { rect:vec4f, uv:vec4f, color:vec4f, info:vec4f }
@group(0) @binding(0) var<uniform> params:Params;
@group(0) @binding(1) var<storage,read> items:array<Item>;
@group(0) @binding(2) var<storage,read_write> descriptors:array<f32>;
@group(0) @binding(3) var<storage,read_write> costs:array<f32>;
@group(0) @binding(4) var<storage,read_write> assignment:array<u32>;
@group(0) @binding(5) var<storage,read_write> used:array<u32>;
@group(0) @binding(6) var<storage,read> flow:array<vec2f>;
@group(0) @binding(7) var<storage,read_write> nextFlow:array<vec2f>;
@group(0) @binding(8) var atlas:texture_2d<f32>;
@group(0) @binding(9) var linearSampler:sampler;
fn boxDistance(p:vec2f,half:vec2f,r:f32)->f32 {
 let d=abs(p)-half+vec2f(r);return -(length(max(d,vec2f(0)))+min(max(d.x,d.y),0.0)-r);
}
fn field(item:Item,p:vec2f)->f32 {
 if(item.info.x>1.5 && item.info.x<2.5){return -.8;}
 if(item.info.x>4.5){return min(boxDistance(p-.5,vec2f(.45),.13),-boxDistance(p-.5,vec2f(.26),.09));}
 if(item.info.x>3.5){let r=length(p-.5);return min(.45-r,r-.26);}
 if(item.info.x>.5){return boxDistance(p-.5,vec2f(.48),0);}
 let q=clamp(p,vec2f(0),vec2f(1));
 let sample=textureSampleLevel(atlas,linearSampler,mix(item.uv.xy,item.uv.zw,q),0).a;
 let tile=(item.uv.zw-item.uv.xy)*vec2f(textureDimensions(atlas));
 return (sample-.5)*8.0/max(max(tile.x,tile.y),1.0)-length(p-q);
}
@compute @workgroup_size(64) fn describe(@builtin(global_invocation_id) id:vec3u){
 let k=id.x;if(k>=params.count*2u*64u){return;}
 let i=k/64u;let cell=k%64u;let p=(vec2f(f32(cell%8u),f32(cell/8u))+.5)/8.;
 descriptors[k]=clamp(field(items[i],p)*16.,-1.,1.);
}
@compute @workgroup_size(64) fn compare(@builtin(global_invocation_id) id:vec3u){
 let k=id.x;let n=params.count;if(k>=n*n){return;}
 let i=k/n;let j=k%n;var difference=0.;
 for(var d=0u;d<64u;d++){let delta=descriptors[i*64u+d]-descriptors[(j+n)*64u+d];difference+=delta*delta;}
 let a=items[i].rect;let b=items[j+n].rect;
 let transport=length((a.xy+a.zw*.5)-(b.xy+b.zw*.5))/1440.;
 let extent=length(log(max(a.zw,vec2f(.1))/max(b.zw,vec2f(.1))));
 costs[k]=difference*100.+transport+extent*.1;
}
// Deterministic GPU greedy assignment. No CPU IDs or correspondence table.
// Bounded to1024 bodies; this is not globally optimal transport.
@compute @workgroup_size(1) fn assign_pairs(){
 let n=params.count;for(var j=0u;j<n;j++){used[j]=0u;}
 for(var i=0u;i<n;i++){
  var best=0u;var value=1e30;
  for(var j=0u;j<n;j++){if(used[j]==0u && costs[i*n+j]<value){value=costs[i*n+j];best=j;}}
  assignment[i]=best;used[best]=1u;
 }
}
fn flowIndex(body:u32,p:vec2i)->u32 {
 let g=i32(params.grid);let q=clamp(p,vec2i(0),vec2i(g-1));return body*params.grid*params.grid+u32(q.y*g+q.x);
}
@compute @workgroup_size(64) fn relax(@builtin(global_invocation_id) id:vec3u){
 let k=id.x;let g=params.grid;let pixels=g*g;if(k>=params.count*pixels){return;}
 let body=k/pixels;let xy=vec2i(i32(k%g),i32((k/g)%g));let p=(vec2f(xy)+.5)/f32(g);
 let a=items[body];let b=items[assignment[body]+params.count];
 let delta=1./f32(g);let dx=vec2f(delta,0);let dy=vec2f(0,delta);
 let gradient=vec2f(field(a,p+dx)-field(a,p-dx)+field(b,p+dx)-field(b,p-dx),field(a,p+dy)-field(a,p-dy)+field(b,p+dy)-field(b,p-dy))/(4.*delta);
 let average=(flow[flowIndex(body,xy+vec2i(1,0))]+flow[flowIndex(body,xy-vec2i(1,0))]+flow[flowIndex(body,xy+vec2i(0,1))]+flow[flowIndex(body,xy-vec2i(0,1))])*.25;
 let residual=field(b,p)-field(a,p);
 let velocity=average-gradient*(dot(gradient,average)+residual)/(.03*.03+dot(gradient,gradient));
 nextFlow[k]=velocity/max(1.,length(velocity)/.3);
}
fn ease(t:f32)->f32{return t*t*t*(10.+t*(-15.+6.*t));}
struct VertexOut { @builtin(position) position:vec4f, @location(0) local:vec2f, @location(1) @interpolate(flat) body:u32 }
@vertex fn vertex(@builtin(vertex_index) v:u32,@builtin(instance_index) i:u32)->VertexOut {
 let corners=array<vec2f,6>(vec2f(0,0),vec2f(1,0),vec2f(0,1),vec2f(0,1),vec2f(1,0),vec2f(1,1));
 let a=items[i];let b=items[assignment[i]+params.count];let rect=mix(a.rect,b.rect,ease(params.phase));
 let scale=min(params.view.x/1200.,params.view.y/760.);let pos=(rect.xy+corners[v]*rect.zw)*scale+(params.view-vec2f(1200,760)*scale)*.5;
 var result:VertexOut;result.position=vec4f(pos.x/params.view.x*2.-1.,1.-pos.y/params.view.y*2.,0,1);result.local=corners[v];result.body=i;return result;
}
fn interpolatedFlow(body:u32,p:vec2f)->vec2f {
 let q=p*f32(params.grid)-.5;let lo=vec2i(floor(q));let t=fract(q);
 return mix(mix(flow[flowIndex(body,lo)],flow[flowIndex(body,lo+vec2i(1,0))],t.x),mix(flow[flowIndex(body,lo+vec2i(0,1))],flow[flowIndex(body,lo+vec2i(1,1))],t.x),t.y);
}
@fragment fn fragment(i:VertexOut)->@location(0) vec4f {
 let a=items[i.body];let b=items[assignment[i.body]+params.count];let t=ease(params.phase);let velocity=interpolatedFlow(i.body,i.local);
 let da=field(a,i.local-t*velocity);let db=field(b,i.local+(1.-t)*velocity);let distance=mix(da,db,t);
 let coverage=clamp(distance/max(fwidth(distance),.00001)+.5,0.,1.);
 let color=mix(a.color,b.color,t);let alpha=color.a*coverage;return vec4f(color.rgb*alpha,alpha);
}
