export function mountSelectionMarquee(canvas,{color='#00ffff'}={}) {
  const doc=canvas.ownerDocument,box=doc.createElement('div');
  box.setAttribute('aria-hidden','true');box.setAttribute('data-vf-selection-marquee','1');box.setAttribute('data-vf-frame-chrome','1');
  box.style.cssText='position:fixed;pointer-events:none;box-sizing:border-box;border:1px dashed;z-index:2;background:transparent;';
  box.style.borderColor=color;box.hidden=true;(doc.body??canvas.parentNode)?.append(box);
  // append fallback is for DOM implementations with only parentElement.
  if(!box.parentNode)canvas.parentElement?.append(box);
  return Object.freeze({show(rectangle){if(!rectangle){box.hidden=true;return;}const r=canvas.getBoundingClientRect();
    const clamp=(v,max)=>Math.max(0,Math.min(max,v));
    const [ax,ay,bx,by]=rectangle,x0=clamp(Math.min(ax,bx),r.width),x1=clamp(Math.max(ax,bx),r.width),y0=clamp(Math.min(ay,by),r.height),y1=clamp(Math.max(ay,by),r.height);
    Object.assign(box.style,{left:r.left+x0+'px',top:r.top+y0+'px',width:x1-x0+'px',height:y1-y0+'px'});box.hidden=false;
  },close(){box.remove()},element:box});
}
