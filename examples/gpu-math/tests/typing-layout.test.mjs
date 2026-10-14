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

test('accents, annotated braces, lines and labelled arrows nest in both styles',()=>{
 const sources=['\\hat{x}+\\widehat{ABC}+\\tilde{x}+\\widetilde{abc}+\\vec{v}','\\dot{x}+\\ddot{x}+\\dddot{x}+\\ddddot{x}+\\acute{a}+\\grave{a}+\\breve{a}+\\check{a}+\\mathring{a}','\\overbrace{\\underbrace{a+b}_{k}+c}^{n}','\\overline{\\frac{x}{y}}+\\underline{z}','A\\xrightarrow[k]{n+1}B+\\overrightarrow{AB}+\\underleftarrow{xy}','\\overset{n}{=}+\\underset{x}{\\lim}'];
 for(const mode of ['inline','display'])for(const source of sources){const b=typeset(source,maps,{mode});assert.equal(b.complete,true,source+JSON.stringify(b.diagnostics));assert.ok(!b.items.some(i=>i.kind==='placeholder'),source);assert.ok(b.items.every(i=>Number.isFinite(i.x)&&Number.isFinite(i.y)&&Number.isFinite(i.flowX)));}
 const b=typeset('\\overbrace{x+y}^n',maps),deleted=typeset('\\overbrace{x+y}^',maps);assert.ok(glyphs(b).includes('script/n'));assert.ok(!glyphs(deleted).includes('script/n'));assert.ok(deleted.items.some(i=>i.kind==='placeholder'));
 for(const source of ['\\hat{','\\overline{\\frac{x}{','\\xrightarrow[k','\\underbrace{x+y}_'])assert.equal(typeset(source,maps).complete,false,source);
});
test('SI quantities use upright units, prefixes, powers and explicit options',()=>{
 const sources=['\\qty{9.81}{\\metre\\per\\second\\squared}','\\SI{1.2e3}{\\kilo\\ohm}','\\si{\\micro\\metre}','\\unit{\\degreeCelsius}','\\num{12345.67890}','\\ang{30;15;20}'];
 for(const source of sources){const b=typeset(source,maps);assert.equal(b.complete,true,source+JSON.stringify(b.diagnostics));assert.ok(!b.items.some(i=>i.kind==='placeholder'),source);}
 assert.ok(glyphs(typeset('\\unit{\\micro\\metre}',maps)).includes('display/@unit:micro'));
 const power=typeset('\\qty{9.81}{\\metre\\per\\second\\squared}',maps);assert.ok(glyphs(power).includes('script/@roman:2'));assert.ok(glyphs(power).includes('display/@roman:m'));
 const frac=typeset('\\unit[per-mode=fraction]{\\metre\\per\\second}',maps);assert.equal(frac.items.filter(i=>i.kind==='rule').length,1);
 assert.ok(glyphs(typeset('\\unit[per-mode=symbol]{\\metre\\per\\second}',maps)).includes('display//'));
 assert.ok(typeset('\\num{12345}',maps).width>typeset('\\num[group-digits=false]{12345}',maps).width);
 assert.equal(typeset('\\unit[not-an-option=true]{\\metre}',maps).complete,false);
 for(const source of ['\\qty{9.81}{\\metre\\per','\\num{1.2e','\\qty{','\\unit{\\metre\\tothe{','\\unit{\\unknown}']){const b=typeset(source,maps);assert.equal(b.complete,false,source);assert.ok(b.items.some(i=>i.kind==='placeholder'),source);}
});
