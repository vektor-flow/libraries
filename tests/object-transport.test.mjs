import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createObjectTransport,sampleObjectTransport} from '../browser-ui/vf-object-transport.mjs';
const obj=(id,positions)=>({id,atoms:positions.map((position,i)=>({id:String(i),position,weight:1/positions.length}))});
const square=[[0,0],[1,0],[1,1],[0,1]];
test('independent objects recover translation and morphology in one scene',()=>{
 const a=[obj('move',square),obj('change',square)];
 const b=[obj('change',[[0,0],[1,0],[.6,1],[0,1]]),obj('move',square.map(([x,y])=>[x+3,y+2]))];
 const plan=createObjectTransport(a,b);
 assert.deepEqual(plan.objects.map(o=>o.fit),['translation','morphology']);
 const mid=sampleObjectTransport(plan,.5,4);
 for(let i=0;i<4;i++)assert.deepEqual(mid[0].samples[i].position,[square[i][0]+1.5,square[i][1]+1]);
 for(const t of [0,1])for(const object of sampleObjectTransport(plan,t,4))for(const p of object.samples){
  assert.ok(p.velocity.every(x=>x===0));assert.ok(p.acceleration.every(x=>x===0));
 }
});
test('no cross-object transport even with repeated atom IDs',()=>{
 const source=[obj('left',square),obj('right',square.map(([x,y])=>[x+10,y]))];
 const plan=createObjectTransport(source,[source[1],source[0]]);
 assert.deepEqual(sampleObjectTransport(plan,.5).map(o=>o.samples.map(p=>p.position)),source.map(o=>o.atoms.map(p=>p.position)));
});
test('reject ambiguous identities and implicit object creation',()=>{
 const a=obj('a',square);
 assert.throws(()=>createObjectTransport([a,a],[a]),/unique/);
 assert.throws(()=>createObjectTransport([a],[obj('b',square)]),/explicit mapping/);
 assert.throws(()=>sampleObjectTransport({},.5),/Expected/);
});
