import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {projectPath,resolveDocumentProject,pngPhysicalSize} from '../document-project.mjs';
import {typesetDocument} from '../document-layout.mjs';
const data=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url)));
test('project resolves nested relative inputs and the job bibliography without interpreting literals',()=>{
 const source=String.raw`\input{sections/a} % \input{missing}
\verb|\input{also-missing}|\begin{verbatim}\input{not-code}\end{verbatim}
\bibliographystyle{siam}\bibliography{database}`;
 const files={'sections/a.tex':String.raw`A \input{../common.tex}`,'common.tex':'B','paper.bbl':String.raw`\begin{thebibliography}{1}\bibitem{x}A reference.\end{thebibliography}`};
 const out=resolveDocumentProject(source,{files,jobName:'paper',entry:'paper.tex'});
 assert.deepEqual(out.diagnostics,[]);assert.deepEqual(out.inputs,['sections/a.tex','common.tex','paper.bbl']);assert.match(out.source,/A \nB/);assert.match(out.source,/bibitem/);assert.match(out.source,/input\{not-code\}/);assert.doesNotMatch(out.source,/bibliographystyle/);
 const escaped=resolveDocumentProject(String.raw`\input{../secret}`);assert.match(escaped.diagnostics[0],/escapes root/);
 const cycle=resolveDocumentProject(String.raw`\input{a}`,{files:{'a.tex':String.raw`\input{b}`,'b.tex':String.raw`\input{a}`}});assert.match(cycle.diagnostics[0],/Cyclic/);
 assert.throws(()=>projectPath('/etc/passwd'),/Invalid/);
});
test('bibliography content resolves citations and verbatim input preserves code glyphs',async()=>{
 const source=String.raw`\documentclass{article}\begin{document}See \cite{ref}.\verbatiminput{code.m}\bibliography{unrelated-database}\end{document}`;
 const result=await typesetDocument(source,data,{buildContext:{jobName:'main',paper:'letter'},files:{'main.bbl':String.raw`\begin{thebibliography}{9}\bibitem{ref}A reference.\end{thebibliography}`,'code.m':String.raw`x = {10}; % $\input{no}`}});
 assert.deepEqual(result.diagnostics,[]);assert.deepEqual(result.projectInputs,['main.bbl']);assert.equal(result.config.paperHeight,792);assert.ok(result.pages[0].items.some(i=>i.key==='text/@document:mono:120'));
 const explicit=await typesetDocument(String.raw`\documentclass[a4paper]{article}\begin{document}X\end{document}`,data,{buildContext:{paper:'letter'}});assert.equal(explicit.config.paperWidth,210*72/25.4);
});
test('PNG physical resolution matches pdfTeX pHYs and 72dpi default',()=>{
 const bytes=new Uint8Array(8+21+12);bytes.set([137,80,78,71,13,10,26,10]);const view=new DataView(bytes.buffer);view.setUint32(8,9);bytes.set([... 'pHYs'].map(c=>c.charCodeAt(0)),12);view.setUint32(16,5906);view.setUint32(20,5906);bytes[24]=1;bytes.set([... 'IEND'].map(c=>c.charCodeAt(0)),33);
 const physical=pngPhysicalSize(bytes,875,656);assert.equal(physical.widthBp,420);assert.equal(pngPhysicalSize(new Uint8Array(),100,50).widthBp,100);
 bytes[24]=0;assert.equal(pngPhysicalSize(bytes,875,656).widthBp,875);
 view.setUint32(8,1000000);assert.throws(()=>pngPhysicalSize(bytes,875,656),/Truncated/);
});

test('nested description flow retains math, references, and custom file listings',async()=>{
 const source=String.raw`\documentclass{article}\usepackage{float,verbatim}\newfloat{listing}{tp}{lst}[section]\floatname{listing}{Listing}\begin{document}\section{Methods}\begin{description}\item Compute $x^2$.\begin{description}\item See \ref{list:a}.\end{description}\end{description}\begin{listing}\caption{Code}\label{list:a}\begin{center}\footnotesize\verbatiminput{code.m}\end{center}\end{listing}\end{document}`;
 const result=await typesetDocument(source,data,{files:{'code.m':'x = 10;\ny = 20;'}});
 assert.deepEqual(result.diagnostics,['Experimental float pagination: global TeX page-break optimization remains incomplete']);assert.ok(result.pages.flatMap(p=>p.items).some(i=>i.key==='text/@document:footnotemono:120'));assert.ok(result.pages.flatMap(p=>p.items).some(i=>i.key==='text/x'));
});
test('eqnarray relations retain native glyphs and resolve each row number',async()=>{
 const source=String.raw`\documentclass{article}\begin{document}\begin{eqnarray}a&=&b\label{first}\\c&=&d\label{second}\end{eqnarray}Rows \ref{first} and \eqref{second}.\end{document}`;
 const result=await typesetDocument(source,data);assert.deepEqual(result.diagnostics,[]);assert.ok(!result.pages.flatMap(p=>p.items).some(i=>i.kind==='placeholder'));assert.ok(result.pages[0].items.some(i=>i.key==='text/@document:roman:50'));
});
