// Local edge bins + binary scanline winding lookup. Positive distance inside.
struct Parameters { count: u32, scale: f32, padding: f32, range: f32 }
@group(0) @binding(0) var<storage,read> segments: array<vec4f>;
@group(0) @binding(1) var field: texture_storage_2d<rgba8unorm,write>;
@group(0) @binding(2) var<uniform> params: Parameters;
@group(0) @binding(3) var<storage,read> tileRanges: array<vec2u>;
@group(0) @binding(4) var<storage,read> tileIndices: array<u32>;
@group(0) @binding(5) var<storage,read> rowRanges: array<vec2u>;
@group(0) @binding(6) var<storage,read> crossings: array<vec2f>;
@compute @workgroup_size(8,8) fn build(@builtin(global_invocation_id) id: vec3u) {
  let size=textureDimensions(field);
  if (id.x>=size.x || id.y>=size.y) { return; }
  let p=(vec2f(id.xy)+0.5-params.padding)/params.scale;
  let columns=(size.x+15u)/16u;
  let bucket=tileRanges[(id.y/16u)*columns+id.x/16u];
  var nearest=params.range*0.5/params.scale;
  for(var i=0u;i<bucket.y;i+=1u) {
    let segment=segments[tileIndices[bucket.x+i]];
    let a=segment.xy;let delta=segment.zw-a;
    let t=clamp(dot(p-a,delta)/max(dot(delta,delta),1e-20),0.0,1.0);
    nearest=min(nearest,length(p-a-t*delta));
  }
  let row=rowRanges[id.y];
  var lo=0u;var hi=row.y;
  loop {
    if(lo>=hi){break;}
    let mid=lo+(hi-lo)/2u;
    if(crossings[row.x+mid].x<=p.x){lo=mid+1u;}else{hi=mid;}
  }
  var inside=false;
  if(lo>0u){inside=crossings[row.x+lo-1u].y!=0.0;}
  let signedDistance=select(-nearest,nearest,inside);
  let encoded=clamp(0.5+signedDistance*params.scale/params.range,0.0,1.0);
  textureStore(field,vec2i(id.xy),vec4f(encoded));
}
