import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {typeset} from '../typing-layout.mjs';
const {maps}=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url),'utf8'));
const glyphs=b=>b.items.filter(i=>i.kind==='glyph').map(i=>i.key);
test('optical scripts, nested fractions and current-source deletion',()=>{
 const b=typeset('x_i^2+\\frac{a}{\\frac{b}{c}}',maps);
 assert.ok(glyphs(b).includes('script/i'));assert.equal(b.items.filter(p=>p.kind==='rule').length,2);
 const before=typeset('\\sum_x^n',maps),after=typeset('\\sum_x^',maps);
 assert.ok(glyphs(before).includes('script/n'));assert.ok(!glyphs(after).includes('script/n'));assert.ok(after.items.some(i=>i.kind==='placeholder'));
 assert.ok(!glyphs(typeset('\\frac{1}{x^}',maps)).some(k=>k.endsWith('/2')));
});
test('unfinished scopes and operands render recoverable drafts',()=>{
 for(const source of ['\\frac{x}{','x^','x+','x-','x^^2','\\unknown','{x','\\left(\\left[x^','\\sum_x^','\\begin{pmatrix}a&b\\\\c&']){
  const b=typeset(source,maps);assert.ok(b.items.length,source);assert.ok(b.items.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)&&Number.isFinite(p.flowX)),source);assert.equal(b.complete,false,source);
 }
 assert.equal(typeset('',maps).items.length,0);
 assert.deepEqual(typeset('\\left(\\frac{x}{y}',maps).items,typeset('\\left(\\frac{x}{y}\\right.',maps).items);
 assert.equal(typeset('\\frac{x+}{y}',maps).items.filter(i=>i.kind==='placeholder').length,1);
 const nested=typeset('\\left(\\begin{pmatrix}a&b\\right)',maps);assert.ok(nested.diagnostics.some(s=>s.startsWith('Inferred \\end')));
});
test('all Greek including capitals, ordinary Pi versus large product',()=>{
 const names='alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega'.split(' ');
 for(const name of names){for(const token of ['\\'+name,'\\'+name[0].toUpperCase()+name.slice(1)])assert.equal(typeset(token,maps).complete,true,token);}
 assert.equal(typeset('αβγΩΣΠ',maps).complete,true);
 assert.ok(maps.display.symbols['\\prod'].height+maps.display.symbols['\\prod'].depth>maps.display.symbols['\\Pi'].height);
});
test('operators, matrices, cases, delimiters and power towers',()=>{
 const formulas=['\\sum_{x=0}^n x^2','\\prod_{k=1}^n k','\\int_0^1 f(x)\\,dx','\\oint_C f(x)\\,dx','\\oiint_S F\\cdot n\\,dS','\\langle x,y\\rangle','\\left\\langle\\frac{1}{\\left(1+x^{2^{n+1}}\\right)}\\right\\rangle'];
 for(const name of ['matrix','pmatrix','bmatrix','Bmatrix','vmatrix','Vmatrix','smallmatrix','cases','aligned'])formulas.push(`\\begin{${name}}a&b\\\\c&d\\end{${name}}`);
 formulas.push('\\begin{array}{rl}x&y\\\\z&w\\end{array}');
 for(const source of formulas){const b=typeset(source,maps);assert.equal(b.complete,true,source+JSON.stringify(b.diagnostics));assert.ok(!b.items.some(i=>i.kind==='placeholder'),source);}
 const tower=typeset('x^{2^{n+1}}',maps);assert.ok(glyphs(tower).includes('scriptscript/n'));
 const tall=typeset('\\left\\{\\begin{matrix}'+Array(8).fill('x').join('\\\\')+'\\end{matrix}\\right.',maps);assert.ok(tall.items.some(i=>i.crop));
});
test('bounded parsing rejects overload and never hangs on closing tokens',()=>{
 assert.throws(()=>typeset('x'.repeat(12001),maps),/limit/);
 for(const source of ['}','\\right)','\\end{matrix}','&','\\\\','\\left.','\\begin{'])assert.ok(typeset(source,maps));
});

test('inline and display use distinct TeX styles and explicit overrides',()=>{
 const source='\\sum_{i=0}^n\\frac{a}{b}';const display=typeset(source,maps),inline=typeset(source,maps,{mode:'inline'});
 assert.ok(glyphs(display).includes('display/\\sum'));assert.ok(glyphs(inline).includes('text/\\sum'));assert.ok(display.height>inline.height);
 const explicit=typeset('\\displaystyle '+source,maps,{mode:'inline'});assert.deepEqual(glyphs(explicit),glyphs(display));
});
