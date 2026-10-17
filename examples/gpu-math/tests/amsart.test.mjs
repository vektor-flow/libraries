import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import amsart from '../latex-modules/classes/amsart.mjs';
import {resolveModules} from '../latex-modules/registry.mjs';
import {requestedFontProfile} from '../font-profile.mjs';
const unit=72/72.27/65536;
for(const fixture of JSON.parse(readFileSync(new URL('./amsart-native.json',import.meta.url))))test('AMS class dimensions from independent native build: '+fixture.options.join(','),()=>{
 const config=amsart.configure(fixture.options),n=fixture.scaledPoints;
 const native={paperWidth:n.paperwidth*unit,paperHeight:n.paperheight*unit,textWidth:n.textwidth*unit,textHeight:n.textheight*unit,left:72+n.oddsidemargin*unit,top:72+(n.topmargin+n.headheight+n.headsep)*unit,lineHeight:n.baselineskip*unit,paragraphIndent:n.parindent*unit};
 for(const [key,value]of Object.entries(native))assert.ok(Math.abs(config[key]-value)<.001,key+': '+config[key]+' versus '+value);
});
test('AMS class dependencies and font profile follow class options in project inputs',async()=>{
 const source=String.raw`\input{header}\begin{document}Body.\end{document}`,files={'header.tex':String.raw`\documentclass[12pt]{amsart}`};
 assert.equal(await requestedFontProfile(source,{files,buildContext:{entry:'main.tex'}}),'amsart-12');
 assert.equal(await requestedFontProfile(String.raw`\documentclass[10pt]{amsart}`),'amsart-10');
 assert.equal(await requestedFontProfile(String.raw`\documentclass{article}`),null);
 const resolved=await resolveModules(files['header.tex']);assert.deepEqual(resolved.diagnostics,[]);for(const name of ['amsmath','amsfonts','amsthm'])assert.ok(resolved.packages.has(name));
});
