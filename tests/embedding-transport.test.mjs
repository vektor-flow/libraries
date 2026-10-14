import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createEmbeddingTransport as create, orderedMassCoupling as ordered,
  sampleEmbeddingTransport as sample, sampleEmbeddingHalf as half,
  sampleEmbeddingKinematics as kinematics } from '../browser-ui/vf-embedding-transport.mjs';
import { fixture } from '../examples/embedding-transport/fixtures.mjs';

const near = (a, b, e=1e-9) => assert.ok(Math.abs(a-b) < e, `${a} != ${b}`);
const atoms = positions => positions.map((position, i) => ({ id: String(i), position, weight: 1 / positions.length }));
const match = a => a.map(p => ({ source: p.id, target: p.id, weight: p.weight }));
const distance = (a, b) => Math.hypot(...a.map((x, k) => x-b[k]));

test('split/merge coupling recovers both endpoint marginals, preserves weight and meets at the midpoint', () => {
  const a = atoms([[-1, 0], [1, 0]]), b = atoms([[-2, 1], [0, 2], [2, 1]]);
  const plan = create(a, b, ordered(a, b));
  for (const [t, expected, key] of [[0,a,'source'], [1,b,'target']]) {
    const frame = sample(plan,t);
    for (const p of expected) {
      const routes = frame.filter(r => r[key] === p.id);
      near(routes.reduce((s, r) => s+r.weight,0),p.weight);
      routes.forEach(r => assert.deepEqual(r.position,p.position));
    }
  }
  for (let i=0;i<=100;i++) near(sample(plan,i/100).reduce((s,r)=>s+r.weight,0),1);
  assert.deepEqual(half(plan,'source',1), half(plan,'target',1));
  assert.deepEqual(sample(plan,0.31),sample(plan,0.31));
});

test('rigid rotation and translation preserve ALL pair distances at every sampled time', () => {
  const a = atoms([[-1,-1], [1,-1], [0,1]]);
  const angle=2*Math.PI/3,c=Math.cos(angle),s=Math.sin(angle);
  const b=atoms(a.map(p=>[3+c*p.position[0]-s*p.position[1],-2+s*p.position[0]+c*p.position[1]]));
  const plan=create(a,b,match(a),{motion:'rigid-2d'});
  near(plan.pose.angle,angle);near(plan.pose.residualRms,0);
  for(let n=0;n<=100;n++) {
    const f=sample(plan,n/100);
    for(let i=0;i<a.length;i++) for(let j=i+1;j<a.length;j++) near(distance(f[i].position,f[j].position),distance(a[i].position,a[j].position));
  }
  const baseline=create(a,b,match(a),{motion:'linear'});
  assert.ok(distance(sample(baseline,.5)[0].position,sample(baseline,.5)[1].position)<1.01);
  assert.deepEqual(half(plan,'source',1),half(plan,'target',1));
});

test('pure translation has zero rotation and constant shape; one point reports undetermined rotation',()=>{
  const a=atoms([[-1,0],[1,0],[0,1]]),b=atoms(a.map(p=>p.position.map(x=>x+2)));
  const plan=create(a,b,match(a),{motion:'rigid-2d'});
  near(plan.pose.angle,0);near(plan.pose.residualRms,0);
  sample(plan,.5).forEach((r,i)=>r.position.forEach((x,k)=>near(x,a[i].position[k]+1)));
  assert.equal(create(atoms([[0,0]]),atoms([[2,2]]),[{source:'0',target:'0',weight:1}],{motion:'rigid-2d'}).pose.rotationDetermined,false);
});

test('time reversal follows the same non-degenerate rigid/residual path',()=>{
  const a=atoms([[-1,-1],[1,-1],[0,1]]),b=atoms([[1,-.5],[.3,1.7],[-1,0]]);
  const forward=create(a,b,match(a),{motion:'rigid-2d'}),reverse=create(b,a,match(a),{motion:'rigid-2d'});
  for(let n=0;n<=30;n++) sample(forward,n/30).forEach((r,i)=>r.position.forEach((x,k)=>near(x,sample(reverse,1-n/30)[i].position[k])));
});

test('custom bridge is shared exactly, and values approach it continuously from both sides',()=>{
  const a=atoms([[-1,0]]),b=atoms([[1,0]]);
  const plan=create(a,b,[{source:'0',target:'0',weight:1,midpoint:[0,2]}],{motion:'linear'});
  assert.deepEqual(sample(plan,.5)[0].position,[0,2]);
  for(const t of [.5-1e-7,.5+1e-7]) assert.ok(distance(sample(plan,t)[0].position,[0,2])<1e-5);
});

test('reject invalid topology-free inputs instead of silently repairing identities, units or mass',()=>{
  const a=atoms([[0,0],[1,1]]),b=atoms([[0,1],[1,2]]);
  assert.throws(()=>create(a,b,[{source:'0',target:'0',weight:1}]),/marginal/);
  assert.throws(()=>create(a,b,[...match(a),match(a)[0]]),/Duplicate/);
  assert.throws(()=>create(a,b,[{source:'unknown',target:'0',weight:1}]),/Unknown/);
  assert.throws(()=>ordered(a,[{id:'x',position:[0,0],weight:2}]),/Unequal/);
  assert.throws(()=>ordered(a,atoms([[0,0,0]])),/coordinate/);
  assert.throws(()=>ordered(a,atoms([[NaN,0]])),/position/);
  assert.throws(()=>ordered([{id:'x',position:[0,0],weight:0}],b),/positive/);
  assert.throws(()=>sample(create(a,b,match(a)),1.01),/Time/);
  assert.throws(()=>sample({},.5),/validated/);
  assert.throws(()=>create(a,b,match(a),{motion:'automatic-topology'}),/motion/);
});

test('plans own immutable endpoint snapshots',()=>{
  const a=atoms([[0,0]]),b=atoms([[1,1]]),plan=create(a,b,match(a));
  a[0].position[0]=100;
  assert.deepEqual(sample(plan,0)[0].position,[0,0]);
  assert.throws(()=>{plan.routes[0].start[0]=100;},TypeError);
});

test('constructed O to D preserves ordered radial contours and a positive hole at all sampled times',()=>{
  const f=fixture('annulus'),plan=create(f.source,f.target,f.coupling,{motion:'rigid-2d'}),count=f.rings[0];
  near(plan.pose.angle,0);
  for(let n=0;n<=100;n++) {
    const points=sample(plan,n/100);
    for(let i=0;i<count;i++) {
      const outer=points[i].position,inner=points[i+count].position,next=points[(i+1)%count].position;
      near(inner[0],.48*outer[0]);near(inner[1],.48*outer[1]);
      assert.ok(Math.hypot(...inner)>.25);
      assert.ok(Math.hypot(...outer)-Math.hypot(...inner)>.28);
      // Each edge stays in its strictly ordered angular wedge; no edge can cross
      // another wedge or the proportional inner contour in this constructed family.
      assert.ok(outer[0]*next[1]-outer[1]*next[0]>0);
    }
  }
});

test('every route starts and ends with exactly zero velocity and acceleration',()=>{
  for(const name of ['rotation','translation','affine','annulus','split']) {
    const f=fixture(name),edges=f.coupling??ordered(f.source,f.target);
    for(const motion of ['linear','rigid-2d','affine-2d']) {
      const p=create(f.source,f.target,edges,{motion});
      for(const t of [0,1]) for(const r of kinematics(p,t,4)) {
        assert.deepEqual(r.velocity,[0,0]);assert.deepEqual(r.acceleration,[0,0]);
      }
    }
  }
});

test('analytic velocity and acceleration agree with independent differences; duration scales derivatives',()=>{
  const f=fixture('affine');
  for(const motion of ['linear','rigid-2d','affine-2d']) {
    const p=create(f.source,f.target,f.coupling,{motion}),h=1e-5;
    for(const t of [.1,.3,.5,.8]) {
      const now=kinematics(p,t),before=sample(p,t-h),after=sample(p,t+h);
      now.forEach((r,i)=>r.position.forEach((x,k)=>{
        near(r.velocity[k],(after[i].position[k]-before[i].position[k])/(2*h),1e-7);
        // Five-point stencil avoids cancellation from subtracting O(1) positions
        // then dividing by 1e-10 in the original second-difference harness.
        const step=1e-3,at=offset=>sample(p,t+offset*step)[i].position[k];
        near(r.acceleration[k],(-at(2)+16*at(1)-30*x+16*at(-1)-at(-2))/(12*step*step),2e-5);
        near(kinematics(p,t,2)[i].velocity[k],r.velocity[k]/2);
        near(kinematics(p,t,2)[i].acceleration[k],r.acceleration[k]/4);
      }));
    }
  }
});

test('changing points in the rotation/translation examples keep moving until the common deadline',()=>{
  for(const name of ['rotation','translation','affine']) {
    const f=fixture(name),p=create(f.source,f.target,f.coupling,{motion:'affine-2d'});
    for(let n=1;n<200;n++) for(const r of kinematics(p,n/200,4)) {
      assert.ok(Math.hypot(...r.velocity)>1e-8);
      assert.ok(distance(r.position,f.target.find(a=>a.id===r.target).position)>1e-8);
    }
  }
});

test('affine hierarchy uses translation, rotation and scale before general affine or morphology',()=>{
  for(const [name,kind] of [['translation','translation'],['rotation','rigid'],['affine','affine'],['annulus','morphology']]) {
    const f=fixture(name),p=create(f.source,f.target,f.coupling,{motion:'affine-2d'});
    assert.equal(p.pose.fit.kind,kind);
    if(kind!=='morphology')near(p.pose.residualRms,0);
  }
  const a=atoms([[-1,0],[1,0]]),b=atoms([[0,-2],[0,2]]);
  const p=create(a,b,match(a),{motion:'affine-2d'});
  assert.equal(p.pose.fit.kind,'similarity');assert.equal(p.pose.fit.fullRank,false);
});

test('affine paths preserve barycentric relations and orientation through a large rotation/shear',()=>{
  const a=atoms([[0,0],[1,0],[0,1],[1,1],[.3,.6]]),angle=170*Math.PI/180;
  const A=[1.4,.4,.4,.8];
  const b=atoms(a.map(({position:[x,y]})=>{
    const X=A[0]*x+A[1]*y,Y=A[2]*x+A[3]*y;
    return [Math.cos(angle)*X-Math.sin(angle)*Y+2,Math.sin(angle)*X+Math.cos(angle)*Y-1];
  }));
  const p=create(a,b,match(a),{motion:'affine-2d'});
  assert.equal(p.pose.fit.kind,'affine');near(p.pose.residualRms,0);
  for(let n=0;n<=100;n++){
    const f=sample(p,n/100).map(r=>r.position),ex=f[1].map((v,k)=>v-f[0][k]),ey=f[2].map((v,k)=>v-f[0][k]);
    assert.ok(ex[0]*ey[1]-ex[1]*ey[0]>.5);
    for(let k=0;k<2;k++){
      near(f[3][k],f[0][k]+ex[k]+ey[k]);
      near(f[4][k],f[0][k]+.3*ex[k]+.6*ey[k]);
    }
  }
});

test('reflection and singular affine endpoints require an explicit policy',()=>{
  const a=atoms([[0,0],[1,0],[0,1],[1,1]]);
  for(const transform of [([x,y])=>[-x,y],([x])=>[x,0]]){
    const b=atoms(a.map(p=>transform(p.position)));
    assert.throws(()=>create(a,b,match(a),{motion:'affine-2d'}),/explicit event/);
  }
});

test('smooth timing does not hide a geometric stall in a reversing path',()=>{
  const p=create(atoms([[0,0]]),atoms([[1,0]]),[{source:'0',target:'0',weight:1,midpoint:[1,0]}],{motion:'linear'});
  // Quadratic control=1.5, so dq/du=3-4u vanishes at u=.75.
  let lo=0,hi=1;
  for(let n=0;n<60;n++){const t=(lo+hi)/2,u=t*t*t*(10+t*(-15+6*t));if(u<.75)lo=t;else hi=t;}
  near(kinematics(p,(lo+hi)/2)[0].velocity[0],0);
  assert.throws(()=>kinematics(p,.5,0),/Duration/);
});
