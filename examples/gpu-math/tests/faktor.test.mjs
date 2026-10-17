import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {typeset} from '../typing-layout.mjs';
import * as faktor from '../latex-modules/packages/faktor.mjs';
const fonts=JSON.parse(readFileSync(new URL('./faktor-font-metrics.json',import.meta.url))),native=JSON.parse(readFileSync(new URL('./faktor-native.json',import.meta.url)));
for(const fixture of native)test('faktor native metrics and every constituent: '+fixture.source,()=>{
 const box=typeset(fixture.source,fonts.maps,{mode:'inline',nativeSemantics:true,packages:['faktor','amssymb'],extensions:[faktor]});
 assert.deepEqual(box.diagnostics,[]);
 for(const dimension of ['width','height','depth'])assert.ok(Math.abs(box[dimension]-fixture[dimension])*96/72<=.1,dimension+': '+box[dimension]+' versus '+fixture[dimension]);
 const glyphs=box.items.flatMap(item=>{
  assert.equal(item.kind,'glyph');const slash=item.key.indexOf('/'),symbol=fonts.maps[item.key.slice(0,slash)].symbols[item.key.slice(slash+1)];
  return symbol.glyphParts.map(part=>({...part,x:item.x+part.x,y:item.y+part.y}));
 });
 assert.equal(glyphs.length,fixture.glyphs.length);
 for(const [index,glyph]of glyphs.entries()){
  const expected=fixture.glyphs[index];assert.equal(glyph.fontName,expected.fontName);assert.equal(glyph.fontCode,expected.fontCode);
  for(const key of ['x','y','fontSize'])assert.ok(Math.abs(glyph[key]-expected[key])*96/72<=.1,key+': '+glyph[key]+' versus '+expected[key]);
 }
});
