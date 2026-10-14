import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createBranchingCopies as create,sampleBranchingCopies as sample} from '../browser-ui/vf-branching-transport.mjs';
const near=(a,b,e=1e-8)=>assert.ok(Math.abs(a-b)<e,`${a} != ${b}`);
const config={source:[0,-.9],targets:[{id:'left',position:[-.8,.75]},{id:'right',position:[.8,.75]}],radius:.24};
test('one visible source becomes two full-size copies, with exact endpoints and zero endpoint derivatives',()=>{
 const p=create(config);
 for(const t of [0,1])sample(p,t,4).forEach((r,i)=>{
  assert.deepEqual(r.position,t===0?config.source:config.targets[i].position);
  assert.equal(r.radius,config.radius);assert.deepEqual(r.velocity,[0,0]);assert.deepEqual(r.acceleration,[0,0]);
 });
});
test('shared translation and increasing separation happen together; no midpoint stop or teleport',()=>{
 const p=create(config);let separation=0,lastY=-.9;
 for(let i=1;i<=100;i++){
  const t=i/100,r=sample(p,t),width=r[1].position[0]-r[0].position[0];
  assert.ok(width>separation);assert.ok(r[0].position[1]>lastY);
  if(i<100)r.forEach(x=>assert.ok(Math.hypot(...x.velocity)>0));
  separation=width;lastY=r[0].position[1];
 }
 assert.ok(sample(p,.25)[1].position[0]<sample(p,.5)[1].position[0]);
 const q=sample(p,.5);near(q[0].position[1],-.075);near(q[1].position[0],.2);
});
test('the duplicated-disc union is connected early and has two components later',()=>{
 const p=create(config);
 const components=t=>{const r=sample(p,t);return Math.hypot(...r[0].position.map((x,k)=>x-r[1].position[k]))<=2*p.radius?1:2;};
 assert.equal(components(0),1);assert.equal(components(.5),1);assert.equal(components(.8),2);assert.equal(components(1),2);
});
test('analytic branch velocities and acceleration match independent differences',()=>{
 const p=create(config),h=1e-4;
 for(const t of [.2,.5,.8]){
  const r=sample(p,t),a=sample(p,t-h),b=sample(p,t+h);
  r.forEach((x,i)=>x.position.forEach((v,k)=>{
   near(x.velocity[k],(b[i].position[k]-a[i].position[k])/(2*h),2e-6);
   near(x.acceleration[k],(b[i].position[k]-2*v+a[i].position[k])/(h*h),1e-5);
  }));
 }
});
test('invalid branch requests fail and input mutation cannot change a plan',()=>{
 const c=structuredClone(config),p=create(c);c.source[0]=99;assert.equal(sample(p,0)[0].position[0],0);
 assert.throws(()=>create({...config,separationPower:0}));assert.throws(()=>create({...config,radius:-1}));
 assert.throws(()=>sample(p,NaN));assert.throws(()=>sample(p,.5,0));assert.throws(()=>sample({},.5));
});
