import test from'node:test';import assert from'node:assert/strict';import{readFileSync}from'node:fs';import{expandDocumentMacros,stripDocumentComments}from'../latex-modules/core/macros.mjs';import{typesetDocumentText,hyphenate}from'../document-text.mjs';import{typeset}from'../typing-layout.mjs';
const data=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url)));
test('author macros preserve token boundaries, aliases, options and literal examples',()=>{const source=String.raw`\newcommand{\base}[1]{\mathit{#1}}\let\alias=\base \newcommand{\ntt}{\ttfamily}\newcommand{\code}[1]{{\ntt#1}}\newcommand{\pick}[2][x]{#1+#2}\alias{v}+\pick{y} \code{sum}\begin{verbatim}\alias{z}% unchanged
\end{verbatim}`;const result=expandDocumentMacros(source).source;assert.match(result,/\\mathit\{v\}/);assert.match(result,/x\+y/);assert.match(result,/\\ttfamily sum/);assert.match(result,/\\alias\{z\}% unchanged/);assert.equal(stripDocumentComments('a% comment\nb\\%c'),'ab\\%c');assert.throws(()=>expandDocumentMacros(String.raw`\def\loop{\loop}\loop`),/limit/);});
test('line breaking permits shrinking while keeping unbroken ligatures',()=>{const source='Words are separated by one or more spaces. Paragraphs are separated by one or more blank lines. The output is not affected by adding extra spaces or extra blank lines to the input file.';const box=typesetDocumentText(source,data,{width:345*72/72.27});assert.equal(box.lines.length,3);const text=line=>box.items.filter(i=>i.flowLine===line).map(i=>Number(i.key.split(':').at(-1)));assert.ok(text(1).slice(-5).every((c,i)=>c==='extra'.charCodeAt(i)));assert.ok(text(1).includes(11));assert.ok(box.lines[1].ratio<0);});
test('escaped symbols reset sentence spacing and native optical fonts remain distinct',()=>{const a=typesetDocumentText(String.raw`Text: \$ x`,data,{width:1000,justify:false}),b=typesetDocumentText(String.raw`Text: \$\ x`,data,{width:1000,justify:false});assert.ok(Math.abs(a.width-b.width)<.001);assert.equal(data.documentFonts.section.name,'cmbx12');assert.ok(Math.abs(data.documentFonts.section.size-14.4*72/72.27)<1e-10);assert.ok(hyphenate('representation').length>0);});
test('valid empty nuclei and primes differ from unfinished script operands',()=>{const b=typeset(String.raw`{}^{\mathrm{1}}+x''+\mathinner{[x]}+\substack{i=1\\j=2}+\mathop{X}\limits_0^n`,data.maps);assert.equal(b.complete,true,JSON.stringify(b.diagnostics));assert.ok(!b.items.some(i=>i.kind==='placeholder'));assert.equal(b.items.filter(i=>i.key==='script/\\prime').length,2);assert.ok(b.items.some(i=>i.key==='script/n'));assert.ok(b.items.some(i=>i.key==='script/0'));assert.ok(typeset(String.raw`x^`,data.maps).items.some(i=>i.kind==='placeholder'));});
test('theorem/proof nesting and footnotes retain independent visible primitives',async()=>{const{typesetDocument}=await import('../document-layout.mjs');const source=String.raw`\documentclass{article}\usepackage{amsthm}\newtheorem{thm}{Theorem}[section]\begin{document}\section{Test}\begin{thm}\label{t}Claim $x'=1$.\end{thm}\begin{proof}Proof text.\end{proof}A note\footnote{A native footnote.} and Theorem \ref{t}.\end{document}`;const r=await typesetDocument(source,data);assert.equal(r.complete,true,JSON.stringify(r.diagnostics));assert.equal(r.pages[0].footnoteNumbers.length,1);assert.ok(r.pages[0].items.some(i=>i.key?.startsWith('text/@document:footnote:')));assert.ok(r.pages[0].items.some(i=>i.key?.startsWith('text/@document:footnotemark:')));assert.ok(r.pages[0].items.filter(i=>i.kind==='rule').length>=5);assert.ok(r.pages[0].items.every(i=>Number.isFinite(i.x+i.y)));});

test('math environments preserve surrounding paragraph geometry like dollar math',async()=>{const{typesetDocument}=await import('../document-layout.mjs');const wrap=body=>String.raw`\documentclass{article}\begin{document}`+body+String.raw`\end{document}`;const a=await typesetDocument(wrap(String.raw`Before $x^2+\alpha$ after.`),data),b=await typesetDocument(wrap(String.raw`Before \begin{math}x^2+\alpha\end{math} after.`),data);assert.equal(b.complete,true,JSON.stringify(b.diagnostics));assert.deepEqual(b.pages,a.pages);});

test('literal URLs preserve percent/hash/math markers through macros and document flow',async()=>{
 const {typesetDocument}=await import('../document-layout.mjs');
 const literal=String.raw`https://a.b/x_y%20?q=1#s$~\TeX`,source=String.raw`\documentclass{article}\usepackage{url}\newcommand{\around}[1]{Before #1 after.}\begin{document}\around{\url{`+literal+String.raw`}}\end{document}`;
 const expanded=expandDocumentMacros(source).source;assert.ok(expanded.includes(literal));
 const result=await typesetDocument(source,data);assert.equal(result.complete,true,JSON.stringify(result.diagnostics));
 const codes=result.pages[0].items.filter(i=>i.key?.startsWith('text/@document:mono:')).map(i=>String.fromCharCode(Number(i.key.split(':').at(-1)))).join('');assert.equal(codes,literal);
 const delimited=await typesetDocument(String.raw`\documentclass{article}\usepackage{url}\begin{document}\url!https://a.b/~x!\end{document}`,data);assert.equal(delimited.complete,true,JSON.stringify(delimited.diagnostics));
 const noPackage=await typesetDocument(String.raw`\documentclass{article}\begin{document}\url{abc}\end{document}`,data);assert.ok(noPackage.diagnostics.some(d=>d.includes('requires url')));
 assert.ok(typesetDocumentText(String.raw`\url{`+'a'.repeat(120)+'}',data,{width:100}).diagnostics.some(d=>d.includes('URL line breaking')));
});

test('standalone AMS text/bold and bm imports use native mapped math glyphs',async()=>{
 const {typesetDocument}=await import('../document-layout.mjs');
 const result=await typesetDocument(String.raw`\documentclass{article}\usepackage{bm,amstext,amsbsy}\begin{document}$\bm{\alpha}+\boldsymbol{\beta}+\text{office}$\end{document}`,data);
 assert.equal(result.complete,true,JSON.stringify(result.diagnostics));assert.deepEqual(result.modules.packages,['bm','amstext','amsbsy']);
 assert.ok(result.pages[0].items.some(i=>i.key?.includes('boldsymbol')));
});

test('nonbreaking spaces use interword spacing after sentence punctuation',()=>{
 const nbsp=typesetDocumentText('Mr.~Jones',data,{width:1000,justify:false});
 const explicit=typesetDocumentText(String.raw`Mr.\ Jones`,data,{width:1000,justify:false});
 assert.ok(Math.abs(nbsp.width-explicit.width)<1e-10);
 const ordinary=typesetDocumentText('Mr. Jones',data,{width:1000,justify:false});assert.ok(ordinary.width>nbsp.width);
});

test('unsupported URL encoding remains diagnostic instead of throwing',()=>{
 for(const value of ['café','a b','line\nbreak']){
  const result=typesetDocumentText('\\url{'+value+'}',data);assert.equal(result.complete,false);assert.ok(result.diagnostics.some(d=>d.includes('normalization')));
 }
});
