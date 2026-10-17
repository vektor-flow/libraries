import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {compileTikzPicture,prepareTikzPictures,tikzNumber} from '../tikz-layout.mjs';
import {vectorPacket,vectorPaintItems} from '../vector-packets.mjs';
import {typesetDocument} from '../document-layout.mjs';
const pt=72/72.27,sp=pt/65536;
const close=(a,b)=>assert.ok(Math.abs(a-b)<2*sp,`${a} != ${b}`);
for(const fixture of JSON.parse(readFileSync(new URL('./tikz-native.json',import.meta.url))))test('independent native TikZ geometry: '+fixture.name,()=>{
 const box=compileTikzPicture(fixture.source);
 for(const dimension of ['width','height','depth'])assert.ok(Math.abs(box[dimension]-fixture[dimension])*96/72<=.1,'Native '+dimension);
 const curves=box.items.filter(i=>i.kind==='bezier');assert.equal(curves.length,fixture.curves.length);
 for(const [index,curve]of curves.entries()){
  for(const axis of [0,1])assert.ok(Math.abs(curve.delta[axis]-fixture.curves[index].delta[axis])*96/72<=.1,'Native endpoint');
  for(const [control,p]of curve.controls.entries())for(const axis of ['x','y'])assert.ok(Math.abs(p[axis]-fixture.curves[index].controls[control][axis])*96/72<=.1,'Native control point');
 }
});
test('TikZ coordinate arithmetic parses dimensions, nested expressions and signs',()=>{
 close(tikzNumber('2*(1cm-3mm)/7').value,2*(72/2.54-3*72/25.4)/7);
 close(tikzNumber('-.5*\\gap',{dimensions:{gap:12*pt}}).value,-6*pt);
 assert.equal(tikzNumber('1+2*3').dimensioned,false);
 for(const source of ['1/0','1+','NaN','process.exit()','1;globalThis.x=1'])assert.throws(()=>tikzNumber(source));
});
test('TikZ names and argument order are independent of this paper',()=>{
 const first=compileTikzPicture(String.raw`[x=9mm,y=-7mm,baseline=2pt]\node[draw,circle,inner sep=0pt,minimum size=4pt](alpha) at (-2,3){};\node[draw,circle,inner sep=0pt,minimum size=4pt](beta) at (5,-1){};\draw[red,thick](alpha) to[out=20,in=145](beta);`);
 const second=compileTikzPicture(String.raw`[x=9mm,y=-7mm,baseline=2pt]\node at (-2,3) [draw,circle,inner sep=0pt,minimum size=4pt](leftEnd){};\node at (5,-1)(rightEnd)[draw,circle,inner sep=0pt,minimum size=4pt]{};\draw[red,thick](leftEnd) to[out=20,in=145](rightEnd);`);
 assert.deepEqual(first,second);assert.equal(first.items.filter(i=>i.kind==='bezier').length,1);
 const curve=first.items.find(i=>i.kind==='bezier'),packet=vectorPacket(curve,curve.color);
 assert.equal(packet.length,16);assert.equal(packet[12],6);assert.ok(packet.every(Number.isFinite));
});
test('TikZ styles are applied in source order, with no retroactive or cross-document state',()=>{
 const source=String.raw`\tikzset{dot/.style={draw,circle,inner sep=0pt,minimum size=2pt}}\begin{tikzpicture}\node[dot] (first) at (0,0) {};\end{tikzpicture}\tikzset{dot/.style={draw,circle,inner sep=0pt,minimum size=8pt}}\begin{tikzpicture}\node[dot] (second) at (0,0) {};\end{tikzpicture}`;
 const r=prepareTikzPictures(source);assert.equal(r.boxes.length,2);close(r.boxes[1].width-r.boxes[0].width,6*pt);
 assert.throws(()=>prepareTikzPictures(String.raw`\begin{tikzpicture}\node[dot] (other) at (0,0) {};\end{tikzpicture}`),/Unsupported TikZ option/);
});
test('TikZ length registers, default pt values and local integer arithmetic work',()=>{
 const r=prepareTikzPictures(String.raw`\newlength\gap\setlength\gap{1cm}\begin{tikzpicture}\multiply\gap by 2\draw(0pt,0pt)--(\gap,0pt);\end{tikzpicture}\begin{tikzpicture}\draw(0pt,0pt)--(\gap,0pt);\end{tikzpicture}`);
 close(r.boxes[0].items[0].delta[0],2*72/2.54);close(r.boxes[1].items[0].delta[0],72/2.54);
 const box=compileTikzPicture(String.raw`\node[draw,circle,inner sep=0,minimum size=3] at (0,0){};`);close(box.items[0].width,3*pt);
});
test('literal TeX examples are never executed by TikZ preparation',()=>{
 const source=String.raw`\verb|\begin{tikzpicture}\node{};\end{tikzpicture}|\begin{verbatim}\begin{tikzpicture}\node{};\end{tikzpicture}\end{verbatim}`;
 const r=prepareTikzPictures(source);assert.equal(r.boxes.length,0);assert.equal(r.source,source);
});
test('unsupported TikZ features and bad arguments fail explicitly',()=>{
 for(const source of [String.raw`\draw(missing)--(0,0);`,String.raw`\draw(0,0) arc(0:90:1cm);`,String.raw`\node[unknown]{};`,String.raw`\node[regular polygon,regular polygon sides=9]{};`])assert.throws(()=>compileTikzPicture(source));
 assert.throws(()=>prepareTikzPictures(String.raw`\tikzset{a/.style={b},b/.style={a}}\begin{tikzpicture}\node[a]{};\end{tikzpicture}`),/Recursive TikZ style/);
});
test('TikZ package gate retains native vector boxes in both prose and mathematics',async()=>{
 const data=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url)));
 const picture=String.raw`\begin{tikzpicture}\draw[blue](0,0)--(1,1);\end{tikzpicture}`;
 for(const body of ['A '+picture+' B.','A $x='+picture+'$ B.']){
  const r=await typesetDocument(String.raw`\documentclass{article}\usepackage{tikz}\begin{document}`+body+String.raw`\end{document}`,data);
  assert.deepEqual(r.diagnostics,[]);assert.ok(r.pages[0].items.some(i=>i.kind==='segment'));assert.ok(!r.pages[0].items.some(i=>i.kind==='placeholder'));
 }
 const absent=await typesetDocument(String.raw`\documentclass{article}\begin{document}`+picture+String.raw`\end{document}`,data);assert.ok(absent.diagnostics.some(d=>d.includes('tikzpicture')));
});
test('separate fill/stroke colors and dotted rectangles retain every drawing operation',()=>{
 const box=compileTikzPicture(String.raw`\node[circle,draw=red,fill=blue,minimum size=4pt,inner sep=0]{};\draw[dotted](1,2) rectangle(3,4);`);
 const painted=vectorPaintItems(box.items);assert.deepEqual(painted[0].color,[0,0,1,1]);assert.deepEqual(painted[1].color,[1,0,0,1]);assert.equal(painted.filter(i=>i.kind==='segment').length,4);
});
