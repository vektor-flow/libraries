// Typesetting supplies endpoint placement only. No text/keys enter correspondence.
import {readFileSync,writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const [runtime,atlas,out]=process.argv.slice(2);
const {typeset}=await import(pathToFileURL(runtime));
const data=JSON.parse(readFileSync(atlas));
const definitions=[
 ['sentence','\\text{These shapes move.}','\\text{These shapes move.}'],
 ['powers','O^2+2O+1','D^2+2D+1'],
 ['fraction','\\frac{8+O}{0+O}','\\frac{B+D}{O+D}'],
 ['mixed','x+O','x+D'],
 ['factor','ab+ac','a(b+c)'],
 ['collect','x+x+x','3x'],
];
const scenes=definitions.map(([id,a,b])=>({id,from:typeset(a,data.maps),to:typeset(b,data.maps)}));
for(const s of scenes)for(const side of ['from','to'])if(!s[side].complete||s[side].diagnostics.length)throw Error(JSON.stringify(s[side].diagnostics));
writeFileSync(out,JSON.stringify(scenes,null,2));
