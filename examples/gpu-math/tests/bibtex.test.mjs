import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseBibtex,bibtexNames,prepareBiblatex} from '../bibtex.mjs';
import {maskTexLiterals} from '../latex-modules/core/literals.mjs';
test('BibTeX balanced fields, strings, case, concatenation and crossrefs',()=>{
 const parsed=parseBibtex(String.raw`@string{venue="Journal " # {of Tests}} @book{parent, publisher={Press},year=2024} @article(child, AUTHOR="Smith, Jo and {A and B Foundation}",title={A {Nested} Title},journal=VENUE,crossref={parent})`);
 assert.deepEqual(parsed.diagnostics,[]);const fields=parsed.entries.get('child').fields;
 assert.equal(fields.journal,'Journal of Tests');assert.equal(fields.title,'A {Nested} Title');assert.equal(fields.publisher,'Press');assert.equal(fields.year,'2024');
 assert.deepEqual(bibtexNames(fields.author).map(n=>n.family),['Smith','A and B Foundation']);
 for(const input of ['@book{x,title={x}', '@book{x,title="x}', '@book{x,title={a}}@book{x,title={b}}','@book{x,crossref={y}}@book{y,crossref={x}}'])assert.throws(()=>parseBibtex(input));
});
test('Biblatex numeric labels follow requested citation order and relative resources',()=>{
 const result=prepareBiblatex(String.raw`\addbibresource{db}\cite[see][p.~2]{z,a}\printbibliography`,{entry:'papers/main.tex',files:{'papers/db.bib':'@book{a,author={Zed, Ada},title={First},year={2020}}@book{z,author={Able, Bea},title={Last},year={2021}}'},options:['style=numeric','sorting=none']});
 assert.deepEqual(result.diagnostics,[]);assert.deepEqual([...result.labels],[['z','1'],['a','2']]);assert.deepEqual(result.inputs,['papers/db.bib']);assert.ok(result.source.includes('\\bibitem[1]{z}'));
});
test('Biblatex ignores quoted TeX, URLs, escaped controls and commented declarations',()=>{
 const literal=String.raw`é😀 \verb|\bibliography{missing}\cite{missing}\printbibliography| \begin{verbatim}\bibliography{missing}\nocite{*}\end{verbatim}
% \bibliography{missing}
\\bibliography{missing} \url{https://example.org/\cite{missing}}`;
 assert.equal(maskTexLiterals(literal).length,literal.length);
 const result=prepareBiblatex(literal+String.raw`\bibliography{ok}\cite{x}\printbibliography`,{files:{'ok.bib':'@book{x,author={Smith, Jo},title={A},year={2020}}'}});
 assert.deepEqual(result.diagnostics,[]);assert.deepEqual(result.inputs,['ok.bib']);assert.ok(result.source.startsWith(literal));assert.equal(result.labels.size,1);
});
test('Biblatex labels agree with all 24 independent native Biber labels',()=>{
 const native=JSON.parse(readFileSync(new URL('./biblatex-native.json',import.meta.url)));
 const result=prepareBiblatex(String.raw`\bibliography{refs}\cite{`+Object.keys(native.labels).join(',')+String.raw`}\printbibliography`,{files:{'refs.bib':native.database},options:['style=alphabetic','sorting=nyt']});
 assert.deepEqual(result.diagnostics,[]);assert.deepEqual(Object.fromEntries(result.labels),native.labels);
});
test('unsupported bibliography styles and missing citation inputs stay explicit',()=>{
 const result=prepareBiblatex(String.raw`\bibliography{missing}\cite{unknown}\printbibliography[heading=none]`,{options:['style=unsupported']});
 assert.ok(result.diagnostics.some(d=>d.includes('style')));assert.ok(result.diagnostics.some(d=>d.includes('Missing bibliography')));assert.ok(result.diagnostics.some(d=>d.includes('Undefined citation')));assert.ok(result.diagnostics.some(d=>d.includes('printbibliography')));
});
