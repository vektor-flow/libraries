import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pdfTextPositions} from '../pdf-text-positions.mjs';
const data=JSON.parse(readFileSync(new URL('../typing-demo/typing-data.json',import.meta.url)));
const fixture=JSON.parse(readFileSync(new URL('./pdf-text-positions-native.json',import.meta.url)));
test('PDF text positioning agrees with native savepos and Type3 font operators',()=>{
 const sp=(72/72.27)/65536,metrics={};
 for(const font of Object.values(data.documentFonts))for(const glyph of Object.values(font.symbols))metrics[glyph.key]={size:font.size,advance:glyph.advance,font:glyph.fontName};
 const bullet=data.maps.text.symbols['@text:bullet'];metrics['text/@text:bullet']={size:bullet.glyphParts[0].fontSize,advance:bullet.advance,font:bullet.fontName,bitmap:true,pkDpi:600};
 const items=fixture.glyphs.map(g=>({kind:'glyph',key:g.key,x:g.inputSp[0]*sp,y:(fixture.paperHeightSp-g.inputSp[1])*sp}));
 const printed=pdfTextPositions(items,{coverage96Metrics:metrics},{pageHeight:fixture.paperHeightBp});
 for(const [index,g]of fixture.glyphs.entries()){
  assert.ok(Math.abs(printed[index].pdfX-g.expected[0])<1e-7,'Native PDF x for '+g.key);
  assert.ok(Math.abs(printed[index].pdfY-g.expected[1])<1e-7,'Native PDF y for '+g.key);
 }
});
