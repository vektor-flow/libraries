// Real canonical compiler and guest execution; JS supplies independent oracles only.
import {pathToFileURL} from 'node:url';
import {mkdtemp,cp,writeFile,mkdir,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
const base=process.env.VKF_CANONICAL || '/home/viktor/Projects/Tesseracs/.worktrees/platonic-phone-web-20261104/public/vkf-0.7.5/playground/canonical';
const {createProjectCompiler}=await import(pathToFileURL(path.join(base,'package-tools/project.mjs')));
const dir=await mkdtemp(path.join(os.tmpdir(),'vkf-interp-verify-'));
const sources={};
for(const name of ['Morphing.vkf','Interpolation.vkf','Interp.vkf','morphing','interpolation'])await cp(name,path.join(dir,name),{recursive:true});
for(const name of ['Morphing.vkf','Interpolation.vkf','Interp.vkf','morphing/state.vkf','morphing/unfold.vkf'])sources[name]=createHash('sha256').update(await readFile(name)).digest('hex');
const c=await createProjectCompiler({compilerModule:path.join(base,'compiler.mjs'),compilerOptions:{printErr:()=>{}}});
const lines=['i:.Interpolation','check()->bit:', '    state:i.state_interp()', '    cubic:i.state_interp(1)', '    reveal:i.spectral_interp()', '    still:i.spectral_interp(velocity:0,grow:false)', '    gas:i.vapor_interp(seed:127)', '    p:i.prepare_interp(state,[0,1],[2,6],1)', '    cp:i.prepare_interp(cubic,[0,1,2],[0,1,0],1)', '    (i.sample(cp,0.5).value.(0)=0.6875)?! "natural cubic delegates same backend"', '    (i.reveal_advance(still,3,17)=3)?! "zero velocity holds"', '    (i.reveal_channel(still,0.2,1)=1)?! "grow false"'];
lines.push('    (state.state.length()=1 /\\ state.reveal.length()=0 /\\ state.vapor.length()=0 /\\ state.state.(0).path=0)?! "typed state defaults"',
 '    (reveal.reveal.(0).k=4 /\\ reveal.reveal.(0).velocity=0.54 /\\ reveal.reveal.(0).overshoot=0.32 /\\ reveal.reveal.(0).grow)?! "typed reveal defaults"',
 '    tuned:i.spectral_interp(k:7,velocity:0.25,overshoot:0.1,grow:false)',
 '    (tuned.state.length()=0 /\\ tuned.vapor.length()=0 /\\ tuned.reveal.(0).k=7 /\\ tuned.reveal.(0).velocity=0.25 /\\ tuned.reveal.(0).overshoot=0.1 /\\ tuned.reveal.(0).grow=false)?! "named optional reveal overrides"',
 '    hot:i.vapor_interp(spread:2,lift:3,seed:42,k:2,velocity:0,overshoot:0,grow:false)',
 '    (hot.vapor.(0).temperature=1 /\\ hot.vapor.(0).spread=2 /\\ hot.vapor.(0).lift=3 /\\ hot.vapor.(0).seed=42 /\\ hot.reveal.(0).k=2 /\\ hot.reveal.(0).grow=false)?! "named vapor fields"',
 '    omitted:i.interp(mode:2)',
 '    (omitted.state.length()=0 /\\ omitted.reveal.length()=0 /\\ omitted.vapor.length()=0)?! "absent named optional groups"',
 '    (i.vapor_channel(omitted,0.5,17,0)=i.vapor_channel(i.vapor_interp(),0.5,17,0))?! "omitted optional groups resolve native defaults"');
let checks=9;
const assertNear=(actual,expected,label)=>{lines.push(`    (|${actual}-(${Number(expected).toPrecision(17)})|<0.00000001)?! "${label}"`);checks++;};
for(let j=0;j<=16;j++){
 const t=j/16,q=t<.5?2*t*t:1-2*(1-t)**2;
 assertNear(`i.time_coordinate(${t})`,q,'shared clock');
 assertNear(`i.sample(p,${t}).value.(0)`,2+4*t,'linear state');
 assertNear(`i.source_alpha(${t})`,(1-t)**2,'source alpha');
 for(let ch=0;ch<4;ch++){
  const noise=lane=>((((j*251+127*199+lane*101+17)%65521)*251+37)%65521)/65520;
  const expected=[.35*t*(2*noise(0)-1),.65*t*(.5+noise(1)),4*t*(1-t)**2,1+3*t*noise(2)][ch];
  assertNear(`i.vapor_channel(gas,${t},${j},${ch})`,expected,'seeded gas oracle');
 }
 const distance=t*.5,a=Math.sin(Math.min(Math.PI/2,4*distance))**2;
 assertNear(`i.reveal_channel(reveal,${distance},0)`,a,'native spectral alpha');
 for(let ch=0;ch<3;ch++){
  const phase=(4.5*Math.min(1,a/.8)+[0,4,2][ch])%6;
  const rgb=Math.min(1,Math.max(0,Math.abs(phase-3)-1));
  const finish=Math.min(1,Math.max(0,(a-.8)/.2)),w=finish*finish*(3-2*finish);
  assertNear(`i.reveal_channel(reveal,${distance},${ch+2})`,rgb+(1-rgb)*w,'spectral oracle');
 }
}
lines.push('    @:true','::check()');
const cases=[{name:'positive-oracles',source:lines.join('\n')+'\n',pass:true},
 {name:'irrelevant-payload',source:'i:.Interp\n::i.settings(0,reveal:[(k:4,velocity:0.54,overshoot:0.32,grow:true)])\n',pass:false},
 {name:'invalid-temperature',source:'i:.Interp\n::i.evaporate(temperature:0.5)\n',pass:false},
 {name:'text-cubic-path',source:'i:.Interp\n::i.settings(1,state:[(path:0,)])\n',pass:false},
 {name:'invalid-seed',source:'i:.Interp\n::i.evaporate(seed:65536)\n',pass:false},
 {name:'duplicate-optional-group',source:'i:.Interp\n::i.settings(0,state:[(path:0,),(path:1,)])\n',pass:false},
 {name:'invalid-reveal-default-override',source:'i:.Interp\n::i.spectral(k:11)\n',pass:false},
 {name:'invalid-state-path',source:'i:.Interp\n::i.state(path:2)\n',pass:false},
 {name:'invalid-velocity',source:'i:.Interp\n::i.spectral(velocity:2)\n',pass:false},
 {name:'invalid-spread',source:'i:.Interp\n::i.evaporate(spread:5)\n',pass:false},
 {name:'inapplicable-named-factory-field',source:'i:.Interp\n::i.spectral(seed:1)\n',pass:false},
 {name:'opaque-positional-settings-rejected',source:'i:.Interp\n::i.settings(1,[],[4,0.54,0.32,1],[])\n',pass:false},
 {name:'carrier-bound',source:'i:.Interp\nv:i.evaporate()\n::i.vapor_channel(v,0.5,65536,0)\n',pass:false}];
const results=[];
for(const test of cases){
 await writeFile(path.join(dir,'main.vkf'),test.source);const start=Date.now();
 try{const r=await c.runProject(dir);if(!test.pass)throw Error('EXPECTED_REJECTION_DID_NOT_OCCUR');if(r.stdout.trim()!=='true')throw Error('positive output '+r.stdout);await writeFile(path.join(dir,test.name+'.wasm'),r.wasm);results.push({name:test.name,passed:true,stdout:r.stdout,ms:Date.now()-start,sourceSha256:createHash('sha256').update(test.source).digest('hex')});}
 catch(e){if(test.pass||String(e).includes('EXPECTED_REJECTION_DID_NOT_OCCUR'))throw e;results.push({name:test.name,passed:true,expectedRejection:String(e),ms:Date.now()-start,sourceSha256:createHash('sha256').update(test.source).digest('hex')});}
 console.log(test.name,'PASS');
}
const report={version:c.compilerVersion,binding:c.sourceBinding,sourceHashes:sources,checks,results,dir,scope:'canonical client WASM execution only; no native ELF, GPU, renderer or visual qualification'};
await mkdir('tests/interp/evidence',{recursive:true});await writeFile('tests/interp/evidence/qualification.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
