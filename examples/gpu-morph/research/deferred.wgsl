struct Params { count:u32, grid:u32, phase:f32, iterations:u32, view:vec2f, unused:vec2f }
struct Item { rect:vec4f, uv:vec4f, color:vec4f, info:vec4f }
@group(0) @binding(0) var<uniform> params:Params;
@group(0) @binding(1) var<storage,read> items:array<Item>;
@group(0) @binding(2) var<storage,read_write> descriptors:array<f32>;
@group(0) @binding(3) var<storage,read_write> costs:array<f32>;
@group(0) @binding(4) var<storage,read_write> assignment:array<u32>;
@group(0) @binding(5) var<storage,read_write> used:array<atomic<u32>>;
@group(0) @binding(6) var<storage,read> flow:array<vec2f>;
@group(0) @binding(7) var<storage,read_write> nextFlow:array<vec2f>;
@group(0) @binding(8) var atlas:texture_2d<f32>;
@group(0) @binding(9) var linearSampler:sampler;
@group(0) @binding(10) var<storage,read_write> coefficients:array<vec4f>;
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
 descriptors[cell*params.count*2u+i]=clamp(field(items[i],p)*16.,-1.,1.);
}
@compute @workgroup_size(64) fn compare(@builtin(global_invocation_id) id:vec3u){
 let k=id.x;let n=params.count;if(k>=n*n){return;}
 let i=k/n;let j=k%n;var difference=0.;
 for(var d=0u;d<64u;d++){let delta=descriptors[d*n*2u+i]-descriptors[d*n*2u+j+n];difference+=delta*delta;}
 let a=items[i].rect;let b=items[j+n].rect;
 let transport=length((a.xy+a.zw*.5)-(b.xy+b.zw*.5))/1440.;
 let extent=length(log(max(a.zw,vec2f(.1))/max(b.zw,vec2f(.1))));
 costs[k]=difference*100.+transport+extent*.1;
}
// Exact source-ordered greedy assignment, cooperatively evaluated by64 lanes.
// Lowest target index wins equal costs, matching the original serial oracle.
var<workgroup> unavailable:array<u32,1024>;
var<workgroup> bestCost:array<f32,64>;
var<workgroup> bestTarget:array<u32,64>;
// Bounded deferred acceptance. All targets use the same source-index priority.
// A complete stable assignment is exactly source-ordered greedy; if unfinished,
// the exact cooperative fallback below recomputes the full answer.
var<workgroup> roundFlag:u32;
@compute @workgroup_size(64) fn init_matching(@builtin(global_invocation_id) id:vec3u){
 let i=id.x;let n=params.count;if(i<n){atomicStore(&used[i],n);assignment[i]=n;}
 if(i==0u){atomicStore(&used[n],0u);atomicStore(&used[n+1u],0u);}
}
@compute @workgroup_size(64) fn propose(@builtin(workgroup_id) group:vec3u,@builtin(local_invocation_index) lane:u32){
 let n=params.count;let i=group.x;
 if(lane==0u){roundFlag=atomicLoad(&used[n]);}
 let done=workgroupUniformLoad(&roundFlag);if(done!=0u){return;}
 var value=1e30;var best=0xffffffffu;
 for(var j=lane;j<n;j+=64u){let c=costs[i*n+j];if(atomicLoad(&used[j])>=i && (c<value || (c==value && j<best))){value=c;best=j;}}
 bestCost[lane]=value;bestTarget[lane]=best;workgroupBarrier();
 for(var stride=32u;stride>0u;stride/=2u){if(lane<stride){let c=bestCost[lane+stride];let j=bestTarget[lane+stride];if(c<bestCost[lane] || (c==bestCost[lane] && j<bestTarget[lane])){bestCost[lane]=c;bestTarget[lane]=j;}}workgroupBarrier();}
 if(lane==0u){descriptors[i]=f32(bestTarget[0]);}
}
@compute @workgroup_size(64) fn claim(@builtin(global_invocation_id) id:vec3u){
 let i=id.x;let n=params.count;if(i>=n || atomicLoad(&used[n])!=0u){return;}
 let j=u32(descriptors[i]);assignment[i]=j;atomicMin(&used[j],i);
}
@compute @workgroup_size(64) fn matching_done(@builtin(local_invocation_index) lane:u32){
 let n=params.count;var bad=0u;
 for(var i=lane;i<n;i+=64u){if(atomicLoad(&used[assignment[i]])!=i){bad=1u;}}
 bestTarget[lane]=bad;workgroupBarrier();
 for(var stride=32u;stride>0u;stride/=2u){if(lane<stride){bestTarget[lane]|=bestTarget[lane+stride];}workgroupBarrier();}
 if(lane==0u && atomicLoad(&used[n])==0u){atomicAdd(&used[n+1u],1u);if(bestTarget[0]==0u){atomicStore(&used[n],1u);}}
}
@compute @workgroup_size(64) fn assign_pairs(@builtin(local_invocation_index) lane:u32){
 let n=params.count;
 if(lane==0u){roundFlag=atomicLoad(&used[n]);}
 let done=workgroupUniformLoad(&roundFlag);if(done!=0u){return;}
 for(var j=lane;j<n;j+=64u){unavailable[j]=0u;}
 workgroupBarrier();
 for(var i=0u;i<n;i++){
  var best=0xffffffffu;var value=1e30;
  for(var j=lane;j<n;j+=64u){let c=costs[i*n+j];if(unavailable[j]==0u && (c<value || (c==value && j<best))){value=c;best=j;}}
  bestCost[lane]=value;bestTarget[lane]=best;workgroupBarrier();
  for(var stride=32u;stride>0u;stride/=2u){
   if(lane<stride){let c=bestCost[lane+stride];let j=bestTarget[lane+stride];if(c<bestCost[lane] || (c==bestCost[lane] && j<bestTarget[lane])){bestCost[lane]=c;bestTarget[lane]=j;}}
   workgroupBarrier();
  }
  if(lane==0u){let j=bestTarget[0];assignment[i]=j;unavailable[j]=1u;}
  workgroupBarrier();
 }
}
fn flowIndex(body:u32,p:vec2i)->u32 {
 let g=i32(params.grid);let q=clamp(p,vec2i(0),vec2i(g-1));return body*params.grid*params.grid+u32(q.y*g+q.x);
}
@compute @workgroup_size(64) fn prepare_flow(@builtin(global_invocation_id) id:vec3u){
 let k=id.x;let g=params.grid;let pixels=g*g;if(k>=params.count*pixels){return;}
 let body=k/pixels;let xy=vec2i(i32(k%g),i32((k/g)%g));let p=(vec2f(xy)+.5)/f32(g);
 let a=items[body];let b=items[assignment[body]+params.count];
 let delta=1./f32(g);let dx=vec2f(delta,0);let dy=vec2f(0,delta);
 let gradient=vec2f(field(a,p+dx)-field(a,p-dx)+field(b,p+dx)-field(b,p-dx),field(a,p+dy)-field(a,p-dy)+field(b,p+dy)-field(b,p-dy))/(4.*delta);
 let residual=field(b,p)-field(a,p);
 coefficients[k]=vec4f(gradient,residual,.03*.03+dot(gradient,gradient));
}
@compute @workgroup_size(64) fn relax(@builtin(global_invocation_id) id:vec3u){
 let k=id.x;let g=params.grid;let pixels=g*g;if(k>=params.count*pixels){return;}
 let body=k/pixels;let xy=vec2i(i32(k%g),i32((k/g)%g));let c=coefficients[k];
 let average=(flow[flowIndex(body,xy+vec2i(1,0))]+flow[flowIndex(body,xy-vec2i(1,0))]+flow[flowIndex(body,xy+vec2i(0,1))]+flow[flowIndex(body,xy-vec2i(0,1))])*.25;
 let velocity=average-c.xy*(dot(c.xy,average)+c.z)/c.w;
 nextFlow[k]=velocity/max(1.,length(velocity)/.3);
}
// One32×32 field per workgroup. Both Jacobi states remain in shared memory.
// Same12 (or configured) iterations, same clamped boundary and arithmetic.
var<workgroup> localFlowA:array<vec2f,1024>;
var<workgroup> localFlowB:array<vec2f,1024>;
fn localIndex(xy:vec2i)->u32 {let q=clamp(xy,vec2i(0),vec2i(31));return u32(q.y*32+q.x);}
@compute @workgroup_size(256) fn solve_local(@builtin(workgroup_id) group:vec3u,@builtin(local_invocation_index) lane:u32){
 let body=group.x;
 for(var k=lane;k<1024u;k+=256u){localFlowA[k]=vec2f(0);localFlowB[k]=vec2f(0);}
 workgroupBarrier();
 for(var iteration=0u;iteration<params.iterations;iteration++){
  for(var k=lane;k<1024u;k+=256u){
   let xy=vec2i(i32(k%32u),i32(k/32u));let a=localIndex(xy+vec2i(1,0));let b=localIndex(xy-vec2i(1,0));let c=localIndex(xy+vec2i(0,1));let d=localIndex(xy-vec2i(0,1));
   var average:vec2f;
   if(iteration%2u==0u){average=(localFlowA[a]+localFlowA[b]+localFlowA[c]+localFlowA[d])*.25;}
   else {average=(localFlowB[a]+localFlowB[b]+localFlowB[c]+localFlowB[d])*.25;}
   let coeff=coefficients[body*1024u+k];let velocity=average-coeff.xy*(dot(coeff.xy,average)+coeff.z)/coeff.w;let result=velocity/max(1.,length(velocity)/.3);
   if(iteration%2u==0u){localFlowB[k]=result;}else{localFlowA[k]=result;}
  }
  workgroupBarrier();
 }
 for(var k=lane;k<1024u;k+=256u){if(params.iterations%2u==0u){nextFlow[body*1024u+k]=localFlowA[k];}else{nextFlow[body*1024u+k]=localFlowB[k];}}
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
