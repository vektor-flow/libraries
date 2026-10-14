import test from 'node:test';
import assert from 'node:assert/strict';
import {fieldInstance} from '../field-packet.mjs';
const texture={type:'mtsdf',format:'linear rgba8unorm',size:[800,240],
  quadBounds:[-1,-1,99,29],distanceRangeTexels:8};
test('field keeps source geometry scale and padded bounds in the viewport',()=>{
  const data=fieldInstance(texture,{x:100,y:40,unitsToPixels:2});
  assert.equal(data.byteLength,64);
  assert.deepEqual([...data.slice(0,8)],[98,38,200,60,0,0,1,1]);
  assert.deepEqual([...data.slice(12,15)],[8,800,240]);
});
test('rejects sRGB distance data, invalid scale and overflowing placement',()=>{
  assert.throws(()=>fieldInstance({...texture,format:'rgba8unorm-srgb'}));
  assert.throws(()=>fieldInstance(texture,{unitsToPixels:0}));
  assert.throws(()=>fieldInstance(texture,{x:1e100}));
});
