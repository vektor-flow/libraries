// Development pixel profile: pdfTeX's integer divide_scaled, adv_char_width,
// and unexpanded Td/TJ state. Full-precision layout remains independent.
// https://github.com/TeX-Live/texlive-source/blob/trunk/texk/web2c/pdftexdir/pdftex.web
const sp=(72/72.27)/65536,bp100=6578176;
const integer=x=>x<0?-Math.round(-x):Math.round(x);
function divide(s,m,digits){const sign=Math.sign(s)*Math.sign(m)||1;s=Math.abs(s);m=Math.abs(m);const power=10**digits,q=Math.floor(s*power/m+.5),remainder=s*power-q*m;return{value:sign*q,out:sign*(s-Math.trunc(remainder/power))};}
export function pdfTextPositions(items,data,{pageHeight=0,fontWidthDigits=4}={}){
 let startX=0,pdfY=0,printedX=0,printedY=0,delta=0,cursor=0,rasterLineX=0,rasterLineY=0,rasterCursor=0,active=false;
 return items.map(item=>{
  // PDF annotations do not interrupt the page's text operators.
  if(item.kind==='link')return item;
  if(item.sourceAsset){const a=item.sourceAsset,x=item.x-a.x*a.scaleX,top=item.y-a.y*a.scaleY,bottom=top+a.drawHeight,physicalHeight=Math.floor(pageHeight/sp+1e-7)*sp;active=false;return{...item,pdfX:integer(x*1000)/1000+a.x*a.scaleX,pdfY:integer(pageHeight*1000)/1000-integer((physicalHeight-bottom)*1000)/1000-a.drawHeight+a.y*a.scaleY};}
  const m=data.coverage96Metrics?.[item.key];
  if(item.kind!=='glyph'||!m||m.rawPositions||(item.sx??1)!==1||(item.sy??1)!==1){active=false;return item;}
  if(!active){startX=0;pdfY=Math.floor(pageHeight/sp+1e-7);printedX=0;printedY=integer(pageHeight*1000);delta=0;cursor=0;rasterLineX=0;rasterLineY=0;rasterCursor=0;}
  const font=divide(integer(m.size/sp),bp100,6),size=font.out;
  const desiredX=integer(item.x/sp),desiredY=integer(item.y/sp);
  let shift=divide(desiredX-startX-delta,size,3),vertical=Math.abs(desiredY-pdfY)>=66?divide(desiredY-pdfY,bp100,5):{value:0,out:0};
  if(!active||vertical.value!==0||Math.abs(shift.value)>=32768){
   const horizontal=divide(desiredX-startX,bp100,5);startX+=horizontal.out;printedX+=horizontal.value;
   pdfY+=vertical.out;printedY+=vertical.value;cursor=printedX*100000000;rasterLineX=Math.fround(rasterLineX+Math.fround(horizontal.value/1000));rasterLineY=Math.fround(rasterLineY-Math.fround(vertical.value/1000));rasterCursor=rasterLineX;delta=0;shift={value:0,out:0};active=true;
  }
  delta+=shift.out;cursor+=shift.value*font.value*10000;rasterCursor=Math.fround(rasterCursor+Math.fround(shift.value*Math.fround(font.value/10000)/1000));
  const out={...item,pdfX:cursor/100000000000,pdfY:printedY/1000,...(fontWidthDigits===3?{pdfPixelX:Math.fround(rasterCursor*Math.fround(96/72)),pdfPixelY:Math.fround(Math.fround(pageHeight*(96/72))-Math.fround(rasterLineY*Math.fround(96/72)))}:{})},widthSp=Math.floor(m.advance/sp+1e-7);
  if(m.bitmap){
   const pkFactor=divide(72,m.pkDpi??600,8).value,pkScale=divide(pkFactor,divide(size,bp100,5).value,0).value;
   const pkWidth=divide(divide(widthSp,size,7).value,pkScale,0).value;
   delta+=Math.trunc(pkScale/100000*(pkWidth/100)*size);cursor+=pkScale*pkWidth*font.value;rasterCursor=Math.fround(rasterCursor+Math.fround(pkScale*pkWidth*font.value/100000000000));
  }else{const advance=divide(widthSp,size,4);delta+=advance.out;cursor+=advance.value*font.value*1000;rasterCursor=Math.fround(rasterCursor+Math.fround(Math.fround(Math.round(advance.value/10)/1000)*Math.fround(font.value/10000)));}
  return out;
 });
}
