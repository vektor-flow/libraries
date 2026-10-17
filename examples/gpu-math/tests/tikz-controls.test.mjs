import test from 'node:test';
import assert from 'node:assert/strict';
import {compileTikzPicture,prepareTikzPictures} from '../tikz-layout.mjs';
import {vectorPacket} from '../vector-packets.mjs';
import {exportVectorPdf} from '../vector-pdf.mjs';
import {inflateSync} from 'node:zlib';
const sp=72/72.27/65536,q=x=>Math.round(x/sp)*sp,u=x=>q(x*q(1));
const source=String.raw`[x=1bp,y=1bp]\draw[red,line width=2bp] (2,3) .. controls (4,8) and (9,-2) .. (12,5);`;
const curve=()=>compileTikzPicture(source).items[0];
test('explicit controls and endpoint retain exact scaled-point geometry and paint',()=>{
 const c=curve();assert.equal(c.kind,'bezier');assert.deepEqual(c.delta,[u(12)-u(2),u(-5)-u(-3)]);
 assert.deepEqual(c.controls,[{x:u(4)-u(2),y:u(-8)-u(-3)},{x:u(9)-u(2),y:u(2)-u(-3)}]);assert.deepEqual(c.color,[1,0,0,1]);assert.equal(c.lineWidth,q(2));
 const p=vectorPacket(c,c.color);assert.deepEqual(p.slice(2,8),[...c.delta,...c.controls.flatMap(p=>[p.x,p.y])]);assert.equal(p[12],6);
});
test('anisotropic axes, negative y, scale, dimensions and arithmetic share coordinate conversion',()=>{
 const a=compileTikzPicture(String.raw`[x=2bp,y=-3bp,scale=2]\draw(1,2).. controls (2,3) and (3,4)..(4,5);`).items[0];
 const b=compileTikzPicture(String.raw`\draw(4bp,-12bp).. controls (8bp,-18bp) and (12bp,-24bp)..(16bp,-30bp);`).items[0];assert.deepEqual(a.delta,[q(4*q(2)*2)-q(q(2)*2),q(-5*q(-3)*2)-q(-2*q(-3)*2)]);assert.deepEqual(a.controls,[{x:q(2*q(2)*2)-q(q(2)*2),y:q(-3*q(-3)*2)-q(-2*q(-3)*2)},{x:q(3*q(2)*2)-q(q(2)*2),y:q(-4*q(-3)*2)-q(-2*q(-3)*2)}]);
 const c=compileTikzPicture(String.raw`\draw(2*2bp,-12bp).. controls (\gap,-18bp) and (12bp,-24bp)..(16bp,-30bp);`,{dimensions:{gap:8}}).items[0];assert.deepEqual(b,c);
});
test('mixed straight, explicit and angle routes preserve path continuity',()=>{
 const b=compileTikzPicture(String.raw`[x=1bp,y=1bp]\draw(0,0)--(2,3).. controls (4,8) and (9,-2)..(12,5) to[out=20,in=160](20,0);`);
 assert.deepEqual(b.items.map(i=>i.kind),['segment','bezier','bezier']);
 for(let i=1;i<3;i++){const p=b.items[i-1],n=b.items[i];assert.ok(Math.abs(p.x+p.delta[0]-n.x)<1e-12);assert.ok(Math.abs(p.y+p.delta[1]-n.y)<1e-12);}
 assert.deepEqual(b.items[1].controls,curve().controls);
});
test('named node borders follow the explicit control tangents',()=>{
 const b=compileTikzPicture(String.raw`[x=1bp,y=1bp]\node[circle,inner sep=0,outer sep=0,minimum size=2bp](a) at (0,0){};\node[circle,inner sep=0,outer sep=0,minimum size=2bp](b) at (10,0){};\draw(a).. controls (0,4) and (10,4)..(b);`);const c=b.items[0];
 assert.ok(Math.abs(c.delta[0]-u(10))<1e-12);assert.ok(Math.abs(c.delta[1])<1e-12);assert.ok(Math.abs(c.controls[0].y-(u(-4)+q(2)/2))<1e-12);
});
test('preparation honors explicit curves and styles',()=>{
 const b=prepareTikzPictures(String.raw`\tikzset{curve/.style={blue,line width=2bp}}\begin{tikzpicture}\draw[curve](0,0)..controls(1,2)and(2,1)..(3,0);\end{tikzpicture}`);
 assert.equal(b.boxes[0].items[0].kind,'bezier');assert.deepEqual(b.boxes[0].items[0].color,[0,0,1,1]);
});
test('malformed, single-control, relative and filled paths reject explicitly',()=>{
 for(const s of [String.raw`\draw(0,0)..(1,1);`,String.raw`\draw(0,0)..controls(1,1)..(2,2);`,String.raw`\draw(0,0)..controls(1,1)and(2,2)(3,3);`,String.raw`\draw(0,0)..controls +(1,1)and(2,2)..(3,3);`,String.raw`\draw(0,0)..controls(1,1)and(2,2)..++(3,3);`,String.raw`\fill(0,0)..controls(1,1)and(2,2)..(3,3);`,String.raw`\draw(0,0)..controls(missing)and(2,2)..(3,3);`])assert.throws(()=>compileTikzPicture(s));
});
test('actual PDF cubic operator retains every explicit coordinate',async()=>{
 const c=curve(),pdf=Buffer.from(await exportVectorPdf({pages:[{width:200,height:200,items:[c]}]},{schema:'vkf.pdf-vectors/1',keys:{}},{compressionWorker:false}));
 let found=false,at=0;
 while((at=pdf.indexOf('stream\n',at))>=0){const start=at+7,end=pdf.indexOf('\nendstream',start);const dict=pdf.subarray(pdf.lastIndexOf(' obj\n',at),at).toString();const text=(dict.includes('/FlateDecode')?inflateSync(pdf.subarray(start,end)):pdf.subarray(start,end)).toString();if(text.includes(' c')){const coords=text.match(/0 0 m ([\d.e+\- ]+) c/);if(coords){const actual=coords[1].split(' ').map(Number),expected=[...c.controls.flatMap(p=>[p.x,p.y]),...c.delta];assert.equal(actual.length,6);actual.forEach((v,i)=>assert.ok(Math.abs(v-expected[i])<1e-8));found=true;}}at=end+10;
 }assert.ok(found);
});
