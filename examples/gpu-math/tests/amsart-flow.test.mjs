import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {typesetDocument} from '../document-layout.mjs';
const fonts=JSON.parse(readFileSync(new URL('./amsart-flow-font-metrics.json',import.meta.url))),native=JSON.parse(readFileSync(new URL('./amsart-flow-native.json',import.meta.url)));
for(const fixture of native)test('independent native AMS flow: '+fixture.name,async()=>{
 const result=await typesetDocument(fixture.source,fonts);
 assert.deepEqual(result.diagnostics.filter(d=>d!=='AMS article layout validation pending'),[]);
 const glyphs=result.pages.flatMap((p,page)=>p.items.flatMap(item=>{
  if(item.kind!=='glyph')return[];
  const slash=item.key.indexOf('/'),style=item.key.slice(0,slash),token=item.key.slice(slash+1);let symbol=fonts.maps[style]?.symbols[token],fontSize;
  if(token.startsWith('@document:')){const [,role,code]=token.split(':');symbol=fonts.documentFonts[role].symbols[code];fontSize=fonts.documentFonts[role].size;}
  const parts=symbol.glyphParts??[{fontName:symbol.fontName,fontCode:symbol.fontCode,fontSize,x:0,y:0}];
  return parts.map(part=>({...part,page,x:item.x+part.x*(item.sx??1),y:item.y+part.y*(item.sy??1),fontSize:part.fontSize*(item.sx??1)}));
 }));
 assert.equal(glyphs.length,fixture.glyphs.length);
 const identity=g=>[g.page,g.fontName,g.fontCode].join('/'),expected=[...fixture.glyphs],actual=[...glyphs];
 for(const glyph of actual){const matches=expected.map((other,i)=>({other,i})).filter(({other})=>identity(other)===identity(glyph)).sort((a,b)=>Math.hypot(a.other.x-glyph.x,a.other.y-glyph.y)-Math.hypot(b.other.x-glyph.x,b.other.y-glyph.y));assert.ok(matches.length,'Missing native glyph '+identity(glyph));const match=matches[0];expected.splice(match.i,1);for(const key of ['x','y','fontSize'])assert.ok(Math.abs(glyph[key]-match.other[key])*96/72<=.1,key+': '+glyph[key]+' versus '+match.other[key]);}
 assert.equal(expected.length,0);
});
