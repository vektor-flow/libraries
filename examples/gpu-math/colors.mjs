// xcolor's base palette, including exact fractional channels rather than CSS
// palette approximations. These are package definitions, not author styles.
const names={black:[0,0,0,1],white:[1,1,1,1],red:[1,0,0,1],green:[0,1,0,1],blue:[0,0,1,1],cyan:[0,1,1,1],magenta:[1,0,1,1],yellow:[1,1,0,1],gray:[.5,.5,.5,1],grey:[.5,.5,.5,1],darkgray:[.25,.25,.25,1],lightgray:[.75,.75,.75,1],orange:[1,.5,0,1],purple:[.75,0,.25,1],teal:[0,.5,.5,1],brown:[.75,.5,.25,1],lime:[.75,1,0,1],olive:[.5,.5,0,1],pink:[1,.75,.75,1],violet:[.5,0,.5,1]};
export function parseColor(value,model=''){
 let text=value.trim();if(model==='HTML')text='#'+text;if(Object.hasOwn(names,text.toLowerCase()))return[...names[text.toLowerCase()]];
 if(/^#[\da-f]{3}$/i.test(text))text='#'+[...text.slice(1)].map(c=>c+c).join('');
 if(/^#[\da-f]{6}$/i.test(text))return[1,3,5].map(i=>parseInt(text.slice(i,i+2),16)/255).concat(1);
 if(model==='rgb'||model==='RGB'){const parts=text.split(',').map(Number),scale=model==='RGB'?255:1;if(parts.length===3&&parts.every(n=>Number.isFinite(n)&&n>=0&&n<=scale))return parts.map(n=>n/scale).concat(1);}
 return null;
}
