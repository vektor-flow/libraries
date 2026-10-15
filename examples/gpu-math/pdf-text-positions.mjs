// Emulate pdfTeX's documented text-position rounding for the fixed PDF pixel
// profile. Geometry itself stays in full precision for MTSDF and arbitrary zoom.
const pt=72/72.27,sp=pt/65536;
const integer=x=>x<0?-Math.round(-x):Math.round(x),quantize=(x,unit)=>integer(x/unit)*unit;
export function pdfTextPositions(items,data){let originX=0,originY=0,delta=0,cursor=0,active=false;return items.map(item=>{
 const m=data.coverage96Metrics?.[item.key];if(item.kind!=='glyph'||!m||(item.sx??1)!==1||(item.sy??1)!==1){active=false;return item;}
 const size=quantize(m.size,1e-6),printed=quantize(size,1e-4),width=integer(m.advance/size*10000)/10000,desiredX=quantize(item.x,sp),desiredY=quantize(item.y,sp);
 if(!active||Math.abs(desiredY-originY)>=.0005){const move=quantize(desiredX-originX,.001);originX+=move;originY+=quantize(desiredY-originY,.001);cursor=originX;delta=0;active=true;}
 const shift=integer((desiredX-originX-delta)/size*1000);delta+=quantize(shift*size/1000,sp);cursor+=shift*printed/1000;const out={...item,pdfX:cursor,pdfY:originY};delta+=quantize(width*size,sp);cursor+=width*printed;return out;
 });}
