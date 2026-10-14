import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createVisualProperties as create,sampleVisualProperties as sample,linearRgbToCss} from '../browser-ui/vf-visual-properties.mjs';
const near=(a,b,e=1e-8)=>assert.ok(Math.abs(a-b)<e,`${a} != ${b}`);
const from={mass:1,coverage:.2,opacity:0,color:[1,1,1]},to={mass:2,coverage:.6,opacity:1,color:[.1,.6,.3]};
test('all scalar, RGB and premultiplied channels settle with zero first and second derivative',()=>{
 const p=create(from,to);
 for(const t of [0,1]){
  const f=sample(p,t,4),expected=t?to:from;
  for(const key of ['mass','coverage','opacity'])assert.equal(f[key].value,expected[key]);
  assert.deepEqual(f.color.map(x=>x.value),expected.color);
  for(const c of [f.mass,f.coverage,f.opacity,...f.color,...f.premultiplied]){assert.equal(Math.abs(c.velocity),0);assert.equal(Math.abs(c.acceleration),0);}
 }
});
test('changing channels progress monotonically, remain bounded and do not finish early',()=>{
 const p=create(from,to);let previous=1;
 for(let i=1;i<100;i++){
  const f=sample(p,i/100);assert.ok(f.mass.value>previous&&f.mass.value<2);assert.ok(f.mass.velocity>0);
  assert.ok(f.coverage.value>.2&&f.coverage.value<.6);assert.ok(f.opacity.value>0&&f.opacity.value<1);
  f.color.forEach((c,k)=>assert.ok(c.value>to.color[k]&&c.value<from.color[k]));previous=f.mass.value;
 }
 const fixed=sample(create(from,from),.5);assert.equal(fixed.mass.value,1);assert.equal(fixed.mass.velocity,0);
});
test('premultiplied derivatives obey the product rule against numerical differences',()=>{
 const p=create(from,to),h=1e-4;
 for(const t of [.2,.5,.8]){
  const a=sample(p,t-h),b=sample(p,t),c=sample(p,t+h);
  b.premultiplied.forEach((v,k)=>{
   near(v.velocity,(c.premultiplied[k].value-a.premultiplied[k].value)/(2*h),1e-6);
   near(v.acceleration,(c.premultiplied[k].value-2*v.value+a.premultiplied[k].value)/(h*h),1e-5);
  });
 }
});
test('zero mass and opacity are valid, while negative quantities and out-of-gamut inputs are rejected',()=>{
 const zero={mass:0,coverage:0,opacity:0,color:[0,0,0]};assert.equal(sample(create(zero,zero),.5).mass.value,0);
 assert.throws(()=>create({...from,mass:-1},to));assert.throws(()=>create(from,{...to,color:[2,0,0]}));
 assert.throws(()=>sample(create(from,to),.5,0));assert.throws(()=>sample({},.5));
 assert.equal(linearRgbToCss([0,0,0]),'rgb(0 0 0)');
 const channels=linearRgbToCss([1,.5,0]).slice(4,-1).split(' ').map(Number);
 near(channels[0],255);near(channels[1],187.51603067837462);near(channels[2],0);
});
