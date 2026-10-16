/* SUBGROUP_FEATURE */
struct Params { count:u32, grid:u32, phase:f32, iterations:u32, view:vec2f, unused:vec2f }
struct Item { rect:vec4f, uv:vec4f, color:vec4f, info:vec4f }
@group(0) @binding(0) var<uniform> params:Params;
@group(0) @binding(1) var<storage,read> items:array<Item>;
@group(0) @binding(2) var<storage,read_write> descriptors:array<f32>;
@group(0) @binding(3) var<storage,read_write> costs:array<f32>;
@group(0) @binding(4) var<storage,read_write> assignment:array<u32>;
@group(0) @binding(5) var<storage,read> groups:array<u32>;
@group(0) @binding(6) var<storage,read> flow:array<vec2f>;
@group(0) @binding(7) var<storage,read_write> nextFlow:array<vec2f>;
@group(0) @binding(8) var atlas:texture_2d<f32>;
@group(0) @binding(9) var linearSampler:sampler;
@group(0) @binding(10) var<storage,read_write> coefficients:array<vec4f>;
fn boxDistance(p:vec2f,half:vec2f,r:f32)->f32 {
 let d=abs(p)-half+vec2f(r);return -(length(max(d,vec2f(0)))+min(max(d.x,d.y),0.0)-r);
}
// Exact object-space field identity: any placement/scale/colour change is
// affine-only and the Jacobi field has the exact zero fixed point.
fn sameField(a:Item,b:Item)->bool {return a.info.x==b.info.x && (a.info.x>.5 || all(a.uv==b.uv));}
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
//16×16 pair tile: each64-sample descriptor is fetched once per tile,
// reused across16 comparisons, with contiguous global descriptor reads.
var<workgroup> sourceTile:array<f32,1024>;
var<workgroup> targetTile:array<f32,1024>;
@compute @workgroup_size(16,16) fn compare(@builtin(workgroup_id) group:vec3u,@builtin(local_invocation_id) local:vec3u,@builtin(local_invocation_index) lane:u32){
 let n=params.count;let si=group.y*16u;let tj=group.x*16u;
 for(var k=lane;k<1024u;k+=256u){let d=k/16u;let x=k%16u;var a=0.;var b=0.;if(si+x<n){a=descriptors[d*n*2u+si+x];}if(tj+x<n){b=descriptors[d*n*2u+tj+x+n];}sourceTile[k]=a;targetTile[k]=b;}
 workgroupBarrier();
 let i=si+local.y;let j=tj+local.x;if(i>=n || j>=n){return;}
 var difference=0.;for(var d=0u;d<64u;d++){let delta=sourceTile[d*16u+local.y]-targetTile[d*16u+local.x];difference+=delta*delta;}
 let a=items[i].rect;let b=items[j+n].rect;
 let transport=length((a.xy+a.zw*.5)-(b.xy+b.zw*.5))/1440.;
 let extent=length(log(max(a.zw,vec2f(.1))/max(b.zw,vec2f(.1))));
 costs[i*n+j]=difference*100.+transport+extent*.1;
}
// Maximal unchanged syntax groups are reserved atomically, largest first.
// Repeated occurrences compete by the cost of the whole group, never a glyph.
@compute @workgroup_size(1) fn assign_groups(){
 let n=params.count;for(var i=0u;i<n;i++){assignment[i]=0xffffffffu;}
 let na=groups[0];let nb=groups[1];
 for(var g=0u;g<na;g++){
  let at=2u+3u*g;let key=groups[at];let start=groups[at+1u];let size=groups[at+2u];
  var free=true;for(var k=0u;k<size;k++){if(assignment[start+k]!=0xffffffffu){free=false;}}
  if(!free){continue;}
  var best=0xffffffffu;var value=1e30;
  for(var h=0u;h<nb;h++){
   let bt=2u+3u*(na+h);let destination=groups[bt+1u];
   if(groups[bt]!=key || groups[bt+2u]!=size){continue;}
   var available=true;
   for(var i=0u;i<n;i++){let j=assignment[i];if(j>=destination && j<destination+size){available=false;}}
   if(!available){continue;}
   var cost=0.;for(var k=0u;k<size;k++){cost+=costs[(start+k)*n+destination+k];}
   if(cost<value || (cost==value && destination<best)){value=cost;best=destination;}
  }
  if(best!=0xffffffffu){for(var k=0u;k<size;k++){assignment[start+k]=best+k;}}
 }
}
// Exact source-ordered greedy assignment, cooperatively evaluated by64 lanes.
// Lowest destination index wins equal costs, matching the original serial oracle.
var<workgroup> unavailable:array<u32,1024>;
var<workgroup> bestCost:array<f32,64>;
var<workgroup> bestTarget:array<u32,64>;
@compute @workgroup_size(64) fn assign_pairs(@builtin(local_invocation_index) lane:u32){
 let n=params.count;
 for(var j=lane;j<n;j+=64u){unavailable[j]=0u;}
 workgroupBarrier();
 for(var i=lane;i<n;i+=64u){let j=assignment[i];if(j!=0xffffffffu){unavailable[j]=1u;}}
 workgroupBarrier();
 for(var i=0u;i<n;i++){
  var best=0xffffffffu;var value=1e30;
  for(var j=lane;j<n;j+=64u){let c=costs[i*n+j];if(((assignment[i]==0xffffffffu && unavailable[j]==0u)||assignment[i]==j) && (c<value || (c==value && j<best))){value=c;best=j;}}
  bestCost[lane]=value;bestTarget[lane]=best;workgroupBarrier();
  for(var stride=32u;stride>0u;stride/=2u){
   if(lane<stride){let c=bestCost[lane+stride];let j=bestTarget[lane+stride];if(c<bestCost[lane] || (c==bestCost[lane] && j<bestTarget[lane])){bestCost[lane]=c;bestTarget[lane]=j;}}
   workgroupBarrier();
  }
  if(lane==0u){let j=bestTarget[0];assignment[i]=j;unavailable[j]=1u;}
  workgroupBarrier();
 }
}
/* SUBGROUP_START */
// Optional subgroup reduction. No assumed hardware subgroup width; up to256
// subgroup leaders share minima, then one leader combines their exact choices.
var<workgroup> subgroupCosts:array<f32,256>;
var<workgroup> subgroupTargets:array<u32,256>;
var<workgroup> subgroupCount:atomic<u32>;
@compute @workgroup_size(256) fn assign_subgroups(@builtin(local_invocation_index) lane:u32){
 let n=params.count;
 if(lane==0u){atomicStore(&subgroupCount,0u);}
 workgroupBarrier();
 var slot=0u;if(subgroupElect()){slot=atomicAdd(&subgroupCount,1u);}
 let subgroup=subgroupBroadcastFirst(slot);
 for(var j=lane;j<n;j+=256u){unavailable[j]=0u;}
 workgroupBarrier();
 for(var i=lane;i<n;i+=256u){let j=assignment[i];if(j!=0xffffffffu){unavailable[j]=1u;}}
 workgroupBarrier();
 for(var i=0u;i<n;i++){
  var value=1e30;var best=0xffffffffu;
  for(var j=lane;j<n;j+=256u){let c=costs[i*n+j];if(((assignment[i]==0xffffffffu && unavailable[j]==0u)||assignment[i]==j) && (c<value || (c==value && j<best))){value=c;best=j;}}
  let minimum=subgroupMin(value);let selected=subgroupMin(select(0xffffffffu,best,value==minimum));
  if(subgroupElect()){subgroupCosts[subgroup]=minimum;subgroupTargets[subgroup]=selected;}
  workgroupBarrier();
  if(lane==0u){var c=1e30;var j=0xffffffffu;for(var k=0u;k<atomicLoad(&subgroupCount);k++){let v=subgroupCosts[k];let t=subgroupTargets[k];if(v<c || (v==c && t<j)){c=v;j=t;}}assignment[i]=j;unavailable[j]=1u;}
  workgroupBarrier();
 }
}
/* SUBGROUP_END */
fn flowIndex(body:u32,p:vec2i)->u32 {
 let g=i32(params.grid);let q=clamp(p,vec2i(0),vec2i(g-1));return body*params.grid*params.grid+u32(q.y*g+q.x);
}
@compute @workgroup_size(64) fn prepare_flow(@builtin(global_invocation_id) id:vec3u){
 let k=id.x;let g=params.grid;let pixels=g*g;if(k>=params.count*pixels){return;}
 let body=k/pixels;let xy=vec2i(i32(k%g),i32((k/g)%g));let p=(vec2f(xy)+.5)/f32(g);
 let a=items[body];let b=items[assignment[body]+params.count];
 if(sameField(a,b)){coefficients[k]=vec4f(0,0,0,.03*.03);return;}
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
 if(lane==0u){localFlowA[0]=vec2f(select(0.,1.,sameField(items[body],items[assignment[body]+params.count])),0);}
 let identity=workgroupUniformLoad(&localFlowA[0]);
 if(identity.x==1.){for(var k=lane;k<1024u;k+=256u){nextFlow[body*1024u+k]=vec2f(0);}return;}
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
