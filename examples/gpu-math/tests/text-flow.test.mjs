import test from 'node:test';import assert from 'node:assert/strict';import{readFileSync}from'node:fs';import{typeset}from'../typing-layout.mjs';import{typesetText}from'../text-flow.mjs';import{parseColor}from'../colors.mjs';
const{maps}=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url),'utf8'));
test('explicit line breaks create independent baselines and preserve matrix rows',()=>{
 const b=typeset('x=1\\\\y=2\\\\z=3',maps);assert.equal(b.lines.length,3);assert.ok(b.lines[1].baseline>b.lines[0].baseline);assert.ok(b.items.some(i=>i.flowLine===2));assert.equal(b.complete,true);
 const tall=typeset('\\frac{a}{b}\\\\\\sum_i^n x_i',maps);assert.ok(tall.lines[1].baseline>=tall.lines[0].depth+tall.lines[1].height);assert.equal(typeset('\\begin{pmatrix}a\\\\b\\end{pmatrix}',maps).complete,true);
 assert.equal(typeset('x\\\\',maps).lines.length,2);
});
test('prose shares Roman atlas glyphs and reflows at word boundaries',()=>{
 const source='This regular text contains $x_i^2$ and Swedish letters å ä ö.';const wide=typesetText(source,maps,{width:300}),narrow=typesetText(source,maps,{width:75});
 assert.equal(wide.complete,true);assert.equal(narrow.complete,true);assert.ok(narrow.lines.length>wide.lines.length);assert.ok(narrow.items.every(i=>Number.isFinite(i.x)&&Number.isFinite(i.y)&&Number.isFinite(i.flowLine)));
 assert.ok(wide.items.some(i=>i.key==='text/@roman:T'));assert.ok(wide.items.some(i=>i.key==='script/i'));
 assert.equal(typesetText('Text $x^',maps).complete,false);assert.equal(typesetText('A\\\\B',maps).lines.length,2);assert.ok(typesetText('A\n\nB',maps).lines.length>=2);
});
test('math alphabets and nested scripts select independent native font tiles',()=>{
 for(const name of ['mathrm','mathbf','mathit','mathsf','mathtt','mathfrak','mathbb','mathbbold','boldsymbol']){const source=`\\${name}{Abc012}_i^2`,b=typeset(source,maps);assert.equal(b.complete,true,source);assert.ok(b.items.some(i=>i.key.endsWith('/@font:'+name+':A')),source);}
 for(const name of ['mathcal','mathscr'])assert.equal(typeset(`\\${name}{ABC}_{\\mathbb{R}}`,maps).complete,true);
 const nested=typeset('\\mathbf{x^{\\mathit{n+1}}}',maps);assert.ok(nested.items.some(i=>i.key==='script/@font:mathit:n'));
 assert.equal(typeset('\\mathscr{abc}',maps).complete,false);assert.equal(typeset('\\mathbb{',maps).complete,false);
});
test('explicit colors scope glyphs and rules without leaking into neighbouring text',()=>{
 const b=typeset('\\textcolor{red}{\\frac{x}{y}}+z',maps);const red=b.items.filter(i=>i.color?.[0]===1&&i.color?.[1]===0);assert.ok(red.some(i=>i.kind==='rule'));assert.ok(red.some(i=>i.kind==='glyph'));assert.equal(b.items.at(-1).color,null);
 const rows=typeset('\\color{blue}x\\\\y',maps);assert.ok(rows.items.every(i=>i.color?.[2]===1));assert.deepEqual(parseColor('00FF00','HTML'),[0,1,0,1]);assert.equal(parseColor('unknown'),null);
});
