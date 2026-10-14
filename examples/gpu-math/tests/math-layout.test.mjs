import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {layoutMath} from '../math-layout.mjs';
const mapping=JSON.parse(readFileSync(new URL('../symbol-mapping.json',import.meta.url),'utf8'));
test('independent mapping preserves repeated geometry and unary binary spacing',()=>{
 const p=layoutMath('x+x',mapping);assert.equal(Object.keys(p.outlines).length,2);
 const unary=layoutMath('-x',mapping),binary=layoutMath('x-x',mapping);
 assert.ok(binary.primitives[1].transform[4]>mapping.symbols.x.width);
 assert.equal(unary.primitives[1].transform[4],mapping.symbols['-'].width);
});
test('rejects syntax without verified runtime layout rules',()=>{
 for(const s of ['\\frac{x}{y}','x^2','x_i','\\unknown',''])assert.throws(()=>layoutMath(s,mapping));
});
