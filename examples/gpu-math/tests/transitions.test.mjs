import {test} from 'node:test';
import assert from 'node:assert/strict';
import {planTransition,transitionFrame} from '../typing-demo/transitions.mjs';
const glyph=(x,uv=0,color=[1,0,0,1])=>[x,20,10,12,uv,0,uv+.1,.1,...color,0,0,0,0];
test('repeated symbols match once and preserve exact endpoints',()=>{
 const from=new Float32Array([...glyph(0),...glyph(100)]),to=new Float32Array([...glyph(90),...glyph(10)]),plan=planTransition(from,to);
 assert.equal(plan.matched,2);assert.deepEqual(plan.pairs,[[0,16],[16,0]]);assert.equal(transitionFrame(plan,0),from);assert.equal(transitionFrame(plan,1),to);
 const middle=transitionFrame(plan,.5);assert.equal(middle[0],5);assert.equal(middle[16],95);
});
test('different outlines crossfade without interpolating atlas coordinates',()=>{
 const from=new Float32Array(glyph(0)),to=new Float32Array(glyph(40,.5,[0,0,1,1])),plan=planTransition(from,to),frame=transitionFrame(plan,.5);
 assert.equal(plan.matched,0);assert.equal(frame[11],.5);assert.equal(frame[27],.5);assert.equal(frame[4],from[4]);assert.equal(frame[20],to[4]);
 for(const p of [0,.01,.25,.5,.9,1])assert.ok([...transitionFrame(plan,p)].every(Number.isFinite));
});
test('matched ink interpolates and combined instance budget is enforced',()=>{
 const plan=planTransition(new Float32Array(glyph(0)),new Float32Array(glyph(10,0,[0,0,1,.5]))),frame=transitionFrame(plan,.5);
 assert.equal(frame[8],.5);assert.equal(frame[10],.5);assert.equal(frame[11],.75);
 const a=new Float32Array(Array.from({length:6001},()=>glyph(0)).flat()),b=new Float32Array(Array.from({length:6001},()=>glyph(0,.5)).flat());assert.throws(()=>planTransition(a,b),/limit/);
});
