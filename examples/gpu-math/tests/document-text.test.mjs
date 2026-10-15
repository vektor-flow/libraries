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

test('native text kern precedence preserves the measured value width',()=>{
 // pdfTeX hbox trace: 22.50006pt; the shared-tail va kern is -0.055555em.
 assert.ok(Math.abs(typeset(String.raw`\text{value}`,data.maps).width/(72/72.27)-22.50006)<.0001);
 assert.ok(data.maps.text.symbols['@roman:v'].kerns['97']<-.55);
});

test('explicit hyphen breaks retain exactly one visible hyphen and all letters',()=>{
 const box=typesetDocumentText('one-line',data,{width:30,justify:false});
 const line=n=>box.items.filter(i=>i.flowLine===n).map(i=>String.fromCharCode(Number(i.key.split(':').at(-1)))).join('');
 assert.equal(box.complete,true,JSON.stringify(box.diagnostics));assert.equal(line(0),'one-');assert.equal(line(1),'line');
});

test('inline math exports stretch and break opportunities without changing its natural width',()=>{
 const math=typeset('x+3y=z',data.maps,{mode:'inline',paragraphMode:true});
 assert.ok(math.paragraphNodes.some(n=>n.type==='glue'&&n.stretch>0));
 assert.ok(math.paragraphNodes.some(n=>n.type==='penalty'&&n.penalty===500));
 const width=math.paragraphNodes.reduce((sum,n)=>sum+(n.type==='box'?n.box.width:n.type==='glue'||n.type==='kern'?n.width:0),0);assert.ok(Math.abs(width-math.width)<1e-10);
});

test('base display skips and subsequent paragraph indentation match native reductions',async()=>{
 const {typesetDocument}=await import('../document-layout.mjs'),wrap=body=>String.raw`\documentclass{article}\begin{document}`+body+String.raw`\end{document}`;
 for(const [gap,after,x,y]of [['', 'Next line.',133.768,164.653],['','\n\nNext paragraph.',148.712,164.653],['\n\n','Following text.',133.768,180.538]]){
  const r=await typesetDocument(wrap(String.raw`Text $g$.`+gap+String.raw`\[x=y\]`+after),data),items=r.pages[0].items,next=items.find(i=>i.key==='text/@document:roman:'+(after.includes('Following')?70:78));assert.equal(r.complete,true,JSON.stringify(r.diagnostics));assert.ok(Math.abs(next.x-x)<.03);assert.ok(Math.abs(next.y-y)<.03);
 }
});

test('quotes resume the paragraph and itemize uses the native text-companion bullet',async()=>{
 const {typesetDocument}=await import('../document-layout.mjs');
 const r=await typesetDocument(String.raw`\documentclass{article}\begin{document}Before quote.\begin{quote}Quoted text.\end{quote}Continued text.`+'\n\n'+String.raw`New paragraph.\begin{itemize}\item First.\item Second.\end{itemize}\end{document}`,data);
 assert.equal(r.complete,true,JSON.stringify(r.diagnostics));const c=r.pages[0].items.find(i=>i.key==='text/@document:roman:67');assert.ok(Math.abs(c.x-133.768)<.03);assert.ok(Math.abs(c.y-174.615)<.03);
 assert.equal(r.pages[0].items.filter(i=>i.key==='text/@text:bullet').length,2);assert.equal(data.maps.text.symbols['@text:bullet'].glyphParts[0].fontCode,136);
});
