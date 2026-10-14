// Software-tested WGSL; not native VKF compiler-integrated or physical-GPU verified.
// One linear rgba8unorm atlas per draw batch. MTSDF alpha is distance, not opacity.
// Instance attributes: rect, uvBounds, color, distanceRange/atlasWidth/atlasHeight.
struct View { size: vec2f, padding: vec2f }
@group(0) @binding(0) var<uniform> view: View;
@group(0) @binding(1) var atlas: texture_2d<f32>;
@group(0) @binding(2) var atlasSampler: sampler;
struct Output {
  @builtin(position) position: vec4f,
  @location(0) uv: vec2f,
  @location(1) color: vec4f,
  @location(2) @interpolate(flat) atlasInfo: vec3f,
  @location(3) @interpolate(flat) fieldKind: f32,
}
@vertex fn vs(@builtin(vertex_index) vertex: u32,
  @location(0) rect: vec4f, @location(1) bounds: vec4f,
  @location(2) color: vec4f, @location(3) info: vec4f) -> Output {
  let corners = array<vec2f, 6>(vec2f(0,0), vec2f(1,0), vec2f(0,1),
    vec2f(0,1), vec2f(1,0), vec2f(1,1));
  let corner = corners[vertex];
  let pixel = rect.xy + corner * rect.zw;
  var o: Output;
  o.position = vec4f(pixel.x / view.size.x * 2 - 1, 1 - pixel.y / view.size.y * 2, 0, 1);
  o.uv = mix(bounds.xy, bounds.zw, corner);
  o.color = color;
  o.atlasInfo = info.xyz;
  o.fieldKind = info.w;
  return o;
}
fn median(v: vec3f) -> f32 { return max(min(v.r,v.g), min(max(v.r,v.g),v.b)); }
@fragment fn fs(input: Output) -> @location(0) vec4f {
  let sample = textureSample(atlas, atlasSampler, input.uv);
  let unitRange = vec2f(input.atlasInfo.x) / input.atlasInfo.yz;
  let pixelRange = max(0.5 * dot(unitRange, 1.0 / fwidth(input.uv)), 1.0);
  var coverage = clamp((median(sample.rgb) - 0.5) * pixelRange + 0.5, 0.0, 1.0);
  let dx=dpdx(input.uv);let dy=dpdy(input.uv);
  if(input.fieldKind>0.5) {
    coverage=0.0;
    for(var y=0;y<2;y+=1){for(var x=0;x<2;x+=1){
      let uv=input.uv+dx*((f32(x)+0.5)/2.0-0.5)+dy*((f32(y)+0.5)/2.0-0.5);
      let distance=textureSampleLevel(atlas,atlasSampler,uv,0.0).r-0.5;
      coverage+=clamp(distance*pixelRange*2.0+0.5,0.0,1.0)/4.0;
    }}
  }
  let alpha = coverage * input.color.a;
  return vec4f(input.color.rgb * alpha, alpha);
}
