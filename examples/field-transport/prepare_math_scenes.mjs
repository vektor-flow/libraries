import {readFileSync,writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const [runtime,atlas,out]=process.argv.slice(2);
const {typeset}=await import(pathToFileURL(runtime));
const data=JSON.parse(readFileSync(atlas));
const definitions=[['reorder','x^2+y^2+z^2','z^2+x^2+y^2'],['distribute','a(b+c+d)','ab+ac+ad'],['collect','x+x+x+y+y','3x+2y'],['factor','x^2+2x+1','(x+1)^2'],['cancel','\\frac{x^2-1}{x-1}','x+1']];
const cases=definitions.map(([id,a,b])=>({id,from:typeset(a,data.maps),to:typeset(b,data.maps)}));
for(const c of cases)for(const s of ['from','to'])if(!c[s].complete||c[s].diagnostics.length)throw Error(JSON.stringify(c[s].diagnostics));
writeFileSync(out,JSON.stringify(cases,null,2));
