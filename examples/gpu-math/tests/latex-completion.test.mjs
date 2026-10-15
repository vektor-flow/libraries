import test from 'node:test';import assert from 'node:assert/strict';import{readFileSync}from'node:fs';
import{typeset}from'../typing-layout.mjs';import{typesetText}from'../text-flow.mjs';import{typesetDocument}from'../document-layout.mjs';import{resolveModules,registerModule}from'../latex-modules/registry.mjs';
const data=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url)));
test('roots, generalized fractions, operators, boxes and text format complete without placeholders',()=>{
 for(const source of [String.raw`\sqrt[3]{\frac{x}{\sqrt{y}}}`,String.raw`\binom{n}{k}+\genfrac{[}{]}{0pt}{1}{a}{b}`,String.raw`\boxed{\operatorname*{argmax}_{x} f(x)}`,String.raw`a\not\subset B\pmod{n}`,String.raw`a\hphantom{x}\vphantom{\frac{a}{b}}\smash[t]{y}\hspace{1em}z`,String.raw`\text{office \textbf{bold} \textit{italics} \% \{escaped\}}`])for(const mode of ['display','inline']){const b=typeset(source,data.maps,{mode});assert.equal(b.complete,true,source+JSON.stringify(b.diagnostics));assert.ok(!b.items.some(i=>i.kind==='placeholder'));assert.ok(b.items.every(i=>Number.isFinite(i.x+i.y)));}
 const before=typeset(String.raw`\sqrt[3]{x}`,data.maps),after=typeset(String.raw`\sqrt[]{x}`,data.maps);assert.ok(before.items.some(i=>i.key==='scriptscript/3'));assert.ok(!after.items.some(i=>i.key==='scriptscript/3'));
 for(const source of [String.raw`\sqrt[3]{`,String.raw`\sqrt[`,String.raw`\binom{n}`,String.raw`\boxed{`,String.raw`\hspace{`,String.raw`\operatorname*{`,String.raw`\text{\textbf{unfinished`])assert.equal(typeset(source,data.maps).complete,false,source);
});
test('alignment, equation variants, row spacing, tags and middle delimiters',()=>{
 const a=typeset(String.raw`\begin{align}x&=y\\z&=w\end{align}`,data.maps),b=typeset(String.raw`\begin{align*}x&=y\\[9pt]z&=w\end{align*}`,data.maps);assert.equal(a.nextEquationNumber,3);assert.ok(a.items.some(i=>i.equationTag));assert.ok(!b.items.some(i=>i.equationTag));assert.ok(b.height+b.depth>a.height+a.depth);
 for(const name of ['equation','equation*','split','gather','gather*','multline','multline*'])assert.equal(typeset(`\\begin{${name}}x=y\\end{${name}}`,data.maps).complete,true,name);
 const array=typeset(String.raw`\begin{array}{|cr|}\hline a&b\\[2pt]\cline{1-2}c&d\\\hline\end{array}`,data.maps);assert.equal(array.complete,true,JSON.stringify(array.diagnostics));assert.ok(array.items.filter(i=>i.kind==='rule').length>=5);
 assert.equal(typeset(String.raw`\left\{x\middle|\frac{a}{b}\right\}`,data.maps).complete,true);
 const prose=typesetText(String.raw`Text. \begin{equation}x=y\end{equation} More text.`,data.maps);assert.equal(prose.complete,true);assert.ok(prose.lines.length>=3);assert.ok(prose.items.some(i=>i.key==='display/x'));
});
test('class and package resolution is explicit and dependency aware',async()=>{
 const modules=await resolveModules(String.raw`\documentclass{article}\usepackage{amsmath,amssymb,graphicx}`);assert.equal(modules.classModule.name,'article');assert.ok(modules.packages.has('amsfonts'));assert.equal(modules.diagnostics.length,0);
 assert.ok((await resolveModules(String.raw`\documentclass{invented}\usepackage{amsmath}`)).diagnostics.some(s=>s.includes('class')));
 assert.ok((await resolveModules(String.raw`\documentclass{article}\usepackage{missing}`)).diagnostics.some(s=>s.includes('missing')));
});
test('document flow retains pages, source references and explicit figure asset boxes',async()=>{
 const source=String.raw`\documentclass{article}\usepackage{amsmath,graphicx}\begin{document}\section{Test}\label{sec:a}See Section \ref{sec:a}.\begin{equation}\sqrt{x}=y\label{eq:a}\end{equation}Equation \eqref{eq:a}.\begin{figure}[h]\includegraphics[width=100bp]{plot.png}\caption{A plot}\label{fig:a}\end{figure}\newpage Last page.\end{document}`;
 const result=await typesetDocument(source,data,{assets:{'plot.png':{width:200,height:100}}});assert.equal(result.pages.length,2);assert.equal(result.config.paperWidth,612);assert.ok(result.pages[0].items.some(i=>i.kind==='image'&&i.width===100&&i.height===50));assert.ok(!result.diagnostics.some(d=>d.includes('Undefined reference')));assert.ok(!result.pages.some(p=>p.items.some(i=>!Number.isFinite(i.x+i.y))));
 const missing=await typesetDocument(source,data);assert.equal(missing.complete,false);assert.ok(missing.diagnostics.some(d=>d.includes('Missing image')));
});

test('a separately registered package extends math without changing the core parser',async()=>{
 const source=String.raw`\documentclass{article}\usepackage{test-extension}\begin{document}$\answer$\end{document}`;
 assert.ok((await typesetDocument(source,data)).diagnostics.some(s=>s.includes('test-extension')));
 registerModule('package','test-extension',async()=>({default:{name:'test-extension',dependencies:[],options:[]},mathCommands:['\\answer'],parseMathCommand(raw,{take}){take();return{type:'glyph',token:'4'};}}));
 const result=await typesetDocument(source,data);assert.equal(result.complete,true,JSON.stringify(result.diagnostics));assert.ok(result.pages[0].items.some(i=>i.key==='text/4'));
 assert.ok((await resolveModules(String.raw`\documentclass{constructor}`)).diagnostics.some(s=>s.includes('Unsupported')));
});
