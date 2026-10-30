// Vector writer command contract. Pure: no PDF encoding, font lookup or layout.
export const need=(ok,code,status='FAIL')=>{if(!ok)throw Object.assign(new Error(code),{code,status});};
export const finite=n=>typeof n==='number'&&Number.isFinite(n)&&Math.abs(n)<=1e9;
export function freeze(value){if(value&&typeof value==='object'){for(const v of Object.values(value))freeze(v);Object.freeze(value);}return value;}
const arity={M:2,L:2,C:6,Z:0};
export function pathCommands(commands){
 need(Array.isArray(commands)&&commands.length>0&&commands.length<=100000,'PLOT_PATH_COMMANDS');
 let open=false;
 for(const c of commands){need(Array.isArray(c)&&Object.hasOwn(arity,c[0])&&c.length===arity[c[0]]+1&&c.slice(1).every(finite),'PLOT_PATH_COMMAND');
  if(c[0]==='M')open=true;else need(open,'PLOT_PATH_START');}
 return commands;
}
export function matrix(m){need(Array.isArray(m)&&m.length===6&&m.every(finite),'PLOT_MATRIX');return m;}
export function color(c){need(Array.isArray(c)&&c.length===4&&c.every(n=>finite(n)&&n>=0&&n<=1),'PLOT_COLOR');return c;}
export const identity=Object.freeze([1,0,0,1,0,0]);
export function multiply(a,b){matrix(a);matrix(b);return [a[0]*b[0]+a[2]*b[1],a[1]*b[0]+a[3]*b[1],a[0]*b[2]+a[2]*b[3],a[1]*b[2]+a[3]*b[3],a[0]*b[4]+a[2]*b[5]+a[4],a[1]*b[4]+a[3]*b[5]+a[5]];}
export function transform(commands,m){pathCommands(commands);matrix(m);return commands.map(c=>{const out=[c[0]];for(let i=1;i<c.length;i+=2){out.push(m[0]*c[i]+m[2]*c[i+1]+m[4],m[1]*c[i]+m[3]*c[i+1]+m[5]);}return out;});}
function num(n){need(finite(n),'PLOT_NUMBER');if(Object.is(n,-0))return '0';const s=String(n);if(!/[eE]/.test(s))return s;
 // Decimal expansion preserves the number rather than rounding it to pixels.
 const [mantissa,exp]=s.toLowerCase().split('e'),negative=mantissa[0]==='-',digits=mantissa.replace('-','').replace('.',''),point=(mantissa.replace('-','').split('.')[0].length)+Number(exp);
 return (negative?'-':'')+(point<=0?'0.'+'0'.repeat(-point)+digits:point>=digits.length?digits+'0'.repeat(point-digits.length):digits.slice(0,point)+'.'+digits.slice(point));}
const nums=a=>a.map(num).join(' ');
function ops(commands){return pathCommands(commands).map(c=>c[0]==='Z'?'h':nums(c.slice(1))+' '+({M:'m',L:'l',C:'c'}[c[0]])).join('\n');}
export function validatePlotPath(item){
 need(item?.kind==='plotpath','PLOT_PRIMITIVE_UNSUPPORTED');pathCommands(item.commands);matrix(item.matrix??identity);
 need(['nonzero','evenodd'].includes(item.fillRule??'nonzero'),'PLOT_FILL_RULE');
 need(Array.isArray(item.clips??[])&&(item.clips??[]).length<=64,'PLOT_CLIPS');
 for(const clip of item.clips??[]){pathCommands(clip.commands);matrix(clip.matrix??identity);need(['nonzero','evenodd'].includes(clip.rule??'nonzero'),'PLOT_CLIP_RULE');}
 need(item.fill!==undefined&&item.stroke!==undefined&&(item.fill!==null||item.stroke!==null),'PLOT_PAINT_MISSING');
 if(item.fill!==null)color(item.fill);
 if(item.stroke!==null){const s=item.stroke;color(s.color);need(finite(s.width)&&s.width>0,'PLOT_STROKE_WIDTH');need(['butt','round','square'].includes(s.cap)&&['miter','round','bevel'].includes(s.join),'PLOT_STROKE_STYLE');
  need(finite(s.miterLimit)&&s.miterLimit>0&&finite(s.dashOffset)&&Array.isArray(s.dash)&&s.dash.length<=256&&s.dash.every(n=>finite(n)&&n>=0)&&(!s.dash.length||s.dash.some(n=>n>0)),'PLOT_DASH');}
 return item;
}
/** colorCommands is the existing PDF writer's alpha/resource allocator. */
export function plotPathPdfCommands(item,colorCommands){
 validatePlotPath(item);const commands=['q'];
 for(const clip of item.clips??[])commands.push(ops(transform(clip.commands,clip.matrix??identity)),clip.rule==='evenodd'?'W* n':'W n');
 commands.push(nums(item.matrix??identity)+' cm');
 if(item.fill!==null)commands.push(colorCommands(item.fill),ops(item.commands),item.fillRule==='evenodd'?'f*':'f');
 if(item.stroke!==null){const s=item.stroke;commands.push(colorCommands(s.color),num(s.width)+' w',({butt:0,round:1,square:2}[s.cap])+' J',({miter:0,round:1,bevel:2}[s.join])+' j',num(s.miterLimit)+' M','['+nums(s.dash)+'] '+num(s.dashOffset)+' d',ops(item.commands),'S');}
 commands.push('Q');return commands.join('\n');
}
/** Decode authenticated native outline path operators, never text or glyph codes. */
export function nativeOutlineCommands(operators){
 need(typeof operators==='string'&&operators.length<=2000000,'PLOT_NATIVE_OUTLINE');
 const tokens=operators.trim().split(/\s+/),out=[],stack=[];
 for(const token of tokens){if(/^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$/.test(token)){const n=Number(token);need(finite(n),'PLOT_NATIVE_COORDINATE');stack.push(n);need(stack.length<=6,'PLOT_NATIVE_OPERANDS');continue;}
  const count={m:2,l:2,c:6,h:0,re:4}[token];need(count!==undefined&&stack.length===count,'PLOT_NATIVE_OPERATOR');
  if(token==='re'){const [x,y,w,h]=stack;out.push(['M',x,y],['L',x+w,y],['L',x+w,y+h],['L',x,y+h],['Z']);}
  else out.push([{m:'M',l:'L',c:'C',h:'Z'}[token],...stack]);stack.length=0;
 }
 need(stack.length===0,'PLOT_NATIVE_TRAILING');return pathCommands(out);
}
