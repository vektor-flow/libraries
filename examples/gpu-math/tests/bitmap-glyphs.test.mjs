import test from 'node:test';import assert from 'node:assert/strict';import{readFileSync}from'node:fs';import{glyphPaintItems}from'../glyph-paints.mjs';
const native=JSON.parse(readFileSync(new URL('./bitmap-glyph-native.json',import.meta.url)));
test('native bitmap glyph keeps its exact pixel area through arbitrary placement and scale',()=>{
 const source={kind:'glyph',key:native.key,x:27.3,y:54.7,sx:1.8,sy:2.1,color:[.2,.4,.6,1]},data={bitmapGlyphRects:{[native.key]:native.rectangles}},paints=glyphPaintItems([source],data),area=paints.reduce((n,r)=>n+r.width*r.height,0);
 assert.ok(Math.abs(area-native.nativeInkPixels*native.pixelSizeBp**2*source.sx*source.sy)<1e-10);
 assert.ok(paints.every(r=>r.kind==='rule'&&r.nativeBitmapGlyph===source.key&&r.color===source.color));assert.equal(source.kind,'glyph');assert.deepEqual(glyphPaintItems([source],data,{bitmap:false}),[source]);
});
