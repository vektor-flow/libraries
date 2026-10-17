import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {typesetDocument} from '../document-layout.mjs';
import {typesetDocumentText} from '../document-text.mjs';
import {pdfTextPositions} from '../pdf-text-positions.mjs';
import {graphicDimensions} from '../document-floats.mjs';
const data=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url)));
const reductions=JSON.parse(readFileSync(new URL('./document-native-reductions.json',import.meta.url)));
for(const fixture of reductions)test('independent native glyph positions: '+fixture.name,async()=>{
 const result=await typesetDocument(fixture.source,data,fixture.options??{});
 assert.deepEqual(result.diagnostics,[]);assert.equal(result.pages.length,1);
 const actual=result.pages[0].items.filter(item=>item.kind==='glyph').flatMap(item=>{const [style,token]=item.key.split('/'),parts=data.maps[style]?.symbols[token]?.glyphParts;return parts?parts.map(part=>({...item,x:item.x+part.x*(item.sx??1),y:item.y+part.y*(item.sy??1)})):[item];});
 assert.equal(actual.length,fixture.glyphs.length,'Every native glyph must be present exactly once');
 const remaining=new Set(actual);
 for(const expected of fixture.glyphs){
  const candidates=[...remaining].filter(item=>item.key===expected.key).sort((a,b)=>Math.hypot(a.x-expected.x,a.y-expected.y)-Math.hypot(b.x-expected.x,b.y-expected.y));
  assert.ok(candidates.length,'Missing '+expected.key);
  const nearest=candidates[0],error=Math.hypot(nearest.x-expected.x,nearest.y-expected.y)*96/72;
  assert.ok(error<=(fixture.positionTolerancePixels??1),`${fixture.name}: ${expected.key} at ${expected.x},${expected.y} differs by ${error}px`);remaining.delete(nearest);
 }
 assert.equal(remaining.size,0);
 if(fixture.checkPdfY){
  const metrics=Object.fromEntries(Object.values(data.documentFonts).flatMap(font=>Object.values(font.symbols).map(glyph=>[glyph.key,{size:font.size,advance:glyph.advance,font:glyph.fontName}])));
  const printed=pdfTextPositions(result.pages[0].items,{coverage96Metrics:metrics},{pageHeight:result.pages[0].height});
  for(const expected of fixture.glyphs){
   const actual=printed.filter(item=>item.key===expected.key).sort((a,b)=>Math.hypot(a.x-expected.x,a.y-expected.y)-Math.hypot(b.x-expected.x,b.y-expected.y))[0];
   assert.equal(Math.floor(actual.pdfY*96/72),Math.floor(expected.y*96/72),'Native PDF baseline pixel for '+expected.key);
  }
 }
 if(fixture.links){
  const links=result.pages[0].items.filter(item=>item.kind==='link');
  assert.equal(links.length,fixture.links.length,'Every native link border must be present');
  for(const [index,expected]of fixture.links.entries()){
   assert.deepEqual(links[index].color,expected.color);
   for(const dimension of ['x','y','width','height'])assert.ok(Math.abs(links[index][dimension]-expected[dimension])*96/72<.1,'Native annotation '+dimension);
  }
 }
});
test('verbatim file input preserves leading and trailing blank lines',()=>{
 const text=typesetDocumentText('\nalpha\n\n',data,{literal:true,literalInput:true,font:'mono',justify:false});
 assert.equal(text.lines.length,3);assert.ok(text.items.every(item=>item.flowLine===1));
 const environment=typesetDocumentText('\nalpha\n',data,{literal:true,font:'mono',justify:false});
 assert.equal(environment.lines.length,1);assert.ok(environment.items.every(item=>item.flowLine===0));
});
test('amscd loading is passive and unsupported CD diagrams remain explicit',async()=>{
 const loaded=await typesetDocument(String.raw`\documentclass{article}\usepackage{amscd}\begin{document}Ordinary text.\end{document}`,data);
 assert.deepEqual(loaded.diagnostics,[]);
 const diagram=await typesetDocument(String.raw`\documentclass{article}\usepackage{amscd}\begin{document}\begin{CD}A@>>>B\end{CD}\end{document}`,data);
 assert.ok(diagram.diagnostics.includes('Unsupported document environment: CD'));
});
test('graphicx box dimensions match independent native scaled-point probes',()=>{
 const sp=(72/72.27)/65536;
 // pdfTeX 1.40.28 / graphicx: measured wd0 and ht0, not framebuffer bounds.
 for(const fixture of [
  {asset:{widthBp:369.0686,heightBp:336.59873},scale:.6,width:14566901,height:13285336},
  {asset:{widthBp:1123,heightBp:794},scale:.35,width:25855908,height:18281024},
 ]){
  const box=graphicDimensions(fixture.asset,{scale:fixture.scale},{});
  assert.equal(Math.round(box.width/sp),fixture.width);
  assert.equal(Math.round(box.height/sp),fixture.height);
  assert.equal(box.drawWidth,fixture.asset.widthBp*fixture.scale);
  assert.equal(box.drawHeight,fixture.asset.heightBp*fixture.scale);
 }
});
