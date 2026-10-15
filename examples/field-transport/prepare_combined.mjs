import {readFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const runtime=resolve(process.argv[2]);
const outputPath=resolve(process.argv[3]);
const {typeset}=await import(pathToFileURL(runtime+'/typing-layout.mjs'));
const data=JSON.parse(readFileSync(runtime+'/typing-data.json'));
const definitions=[
 ['power-graph','f(x)=x^2','f(x)=x^3'],
 ['cubic-quintic','h(x)=x^3-x','h(x)=x^5+x'],
 ['scale-shift','g(x)=2x^2+1','g(x)=3x^2-1'],
 ['mixed-split','A+B=C-D','A+B=C=D'],
 ['mixed-merge','u+v\\equiv w+2','u+v=w+3'],
 ['reorder-morph','x^2+y^2=2','y^2+x^2=3']
];
const output=definitions.map(([id,a,b])=>({id,source:a,target:b,from:typeset(a,data.maps),to:typeset(b,data.maps)}));
for(const c of output)for(const side of ['from','to']){if(!c[side].complete||c[side].diagnostics.length)throw Error(c.id+JSON.stringify(c[side].diagnostics));if(c[side].items.filter(x=>x.kind==='glyph').length<6)throw Error('Need six visible glyphs');}
writeFileSync(outputPath,JSON.stringify(output,null,2));console.log(output.map(x=>[x.id,x.from.width,x.from.items.length,x.to.items.length]));
