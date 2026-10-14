const names={black:'#000000',white:'#ffffff',red:'#ff0000',green:'#00ff00',blue:'#0000ff',cyan:'#00ffff',magenta:'#ff00ff',yellow:'#ffff00',gray:'#808080',grey:'#808080',orange:'#ea580c',purple:'#9333ea',teal:'#0d9488'};
export function parseColor(value,model=''){
 let text=value.trim();if(model==='HTML')text='#'+text;if(names[text.toLowerCase()])text=names[text.toLowerCase()];
 if(/^#[\da-f]{3}$/i.test(text))text='#'+[...text.slice(1)].map(c=>c+c).join('');
 if(/^#[\da-f]{6}$/i.test(text))return[1,3,5].map(i=>parseInt(text.slice(i,i+2),16)/255).concat(1);
 if(model==='rgb'||model==='RGB'){const parts=text.split(',').map(Number),scale=model==='RGB'?255:1;if(parts.length===3&&parts.every(n=>Number.isFinite(n)&&n>=0&&n<=scale))return parts.map(n=>n/scale).concat(1);}
 return null;
}
