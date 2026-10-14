import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {typeset} from '../typing-layout.mjs';
const {maps}=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url),'utf8'));
test('optical-size scripts and nested fraction rules survive independent layout',()=>{
 const b=typeset('x_i^2+\\frac{a}{\\frac{b}{c}}',maps);
 assert.ok(b.items.some(p=>p.kind==='glyph'&&p.key==='script/i'));
 assert.equal(b.items.filter(p=>p.kind==='rule').length,2);
 assert.ok(b.items.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)&&Number.isFinite(p.flowX)));
});
test('incomplete and unsupported source cannot become a misleading expression',()=>{
 for(const source of ['\\frac{x}{','x^','x^^2','\\unknown','{x','\\sqrt{x}'])assert.throws(()=>typeset(source,maps));
 assert.equal(typeset('',maps).items.length,0);
});
