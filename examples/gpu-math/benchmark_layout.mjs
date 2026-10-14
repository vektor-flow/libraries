/** Reproducible independent long-expression layout benchmark and path packet. */
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
import {layoutMath} from './math-layout.mjs';
const output=process.argv[2];if(!output)throw Error('Provide a fresh output directory');mkdirSync(output);
const mapping=JSON.parse(readFileSync(new URL('./symbol-mapping.json',import.meta.url),'utf8'));
const row=Array(5).fill('(x+\\alpha+y)').join('+');
const lines=25,times=[];let packet;
for(let iteration=0;iteration<150;iteration++) {
 const start=performance.now(),one=layoutMath(row,mapping),primitives=[];
 for(let line=0;line<lines;line++)for(const p of one.primitives)primitives.push({...p,id:`row-${line}/${p.id}`,transform:[...p.transform.slice(0,5),p.transform[5]+line*14]});
 packet={...one,primitives,bounds:[0,0,one.bounds[2],lines*14]};times.push(performance.now()-start);
}
times.sort((a,b)=>a-b);
writeFileSync(`${output}/independent-long-packet.json`,JSON.stringify(packet));
const timing={atoms:packet.primitives.length,iterations:150,p50ms:times[75],p95ms:times[142],maxms:times.at(-1),
 scope:'Independent bounded Node layout and explicit row assembly; excludes curve preparation, upload and GPU work'};
writeFileSync(`${output}/layout-timing.json`,JSON.stringify(timing,null,2)+'\n');console.log(JSON.stringify(timing));
