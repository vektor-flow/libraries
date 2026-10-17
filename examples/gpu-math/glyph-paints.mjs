// Prepared bitmap-font geometry. Source glyph identity/metrics stay in layout;
// rendering expands only font pixels, without document/reference coordinates.
export function glyphPaintItems(items,data,{bitmap=true}={}){
 if(!bitmap||!data.bitmapGlyphRects)return items;
 return items.flatMap(item=>{
  const rectangles=item.kind==='glyph'?data.bitmapGlyphRects[item.key]:null;
  if(!rectangles)return[item];
  const sx=item.sx??1,sy=item.sy??1;
  if(!Number.isFinite(sx+sy)||sx<=0||sy<=0)throw Error('Unsupported bitmap glyph scale');
  return rectangles.map(([x,y,width,height])=>({kind:'rule',x:item.x+x*sx,y:item.y+y*sy,width:width*sx,height:height*sy,...(item.color?{color:item.color}:{}),nativeBitmapGlyph:item.key}));
 });
}
