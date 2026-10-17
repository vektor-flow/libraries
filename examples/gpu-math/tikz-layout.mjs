// Native, bounded TikZ geometry. No TeX engine, reference PDF, or page raster.
// Distances are bp; TeX dimensions are rounded to scaled points at assignment.
import {readGroup} from './latex-modules/core/macros.mjs';
import {parseColor} from './colors.mjs';
import {maskTexLiterals} from './latex-modules/core/literals.mjs';
const pt=72/72.27,sp=pt/65536;
const units={bp:1,pt,cm:72/2.54,mm:72/25.4,in:72,pc:12*pt};
const scaled=value=>Math.round(value/sp)*sp;
function pgfControlDistance(a,b){
 // tikzlibrarytopaths.code.tex: normalised direction -> /255 integer divisor,
 // two 16x dimension multiplications, then the native .3915 fixed-point factor.
 const dx=Math.abs(Math.round((b.x-a.x)/sp)),dy=Math.abs(Math.round((b.y-a.y)/sp));
 if(!dx&&!dy)return 0;
 const norm=Math.max(dx,dy)/Math.hypot(dx,dy),divisor=Math.trunc(Math.round(norm*65536)/255);
 return Math.round(Math.trunc(Math.max(dx,dy)*16/divisor)*16*25657/65536)*sp;
}
export function splitTikzArguments(text,delimiter=','){
 const parts=[];let start=0,depth=0;
 for(let i=0;i<text.length;i++){if(text[i]==='\\'){i++;continue;}if('{[('.includes(text[i]))depth++;else if('}])'.includes(text[i]))depth--;else if(text[i]===delimiter&&!depth){parts.push(text.slice(start,i).trim());start=i+1;}if(depth<0)throw Error('Unbalanced TikZ argument');}
 if(depth)throw Error('Unbalanced TikZ argument');parts.push(text.slice(start).trim());return parts.filter(Boolean);
}
// Deliberately parse arithmetic instead of evaluating author text as JavaScript.
export function tikzNumber(source,{dimensions={},em=10*pt,ex=4.30554*pt}={}){
 let at=0,dimensioned=false;const skip=()=>{while(/\s/.test(source[at]??'')&&at<source.length)at++;};
 function primary(){skip();let sign=1;while(source[at]==='+'||source[at]==='-'){if(source[at++]==='-')sign=-sign;skip();}let value;
  if(source[at]==='('||source[at]==='{'){const close=source[at++]==='('?')':'}';value=sum();skip();if(source[at++]!==close)throw Error('Unbalanced TikZ arithmetic');}
  else if(source[at]==='\\'){const m=/^\\([A-Za-z]+)/.exec(source.slice(at));if(!m||!Object.hasOwn(dimensions,m[1]))throw Error('Unknown TikZ dimension: '+(m?.[0]??source.slice(at)));at+=m[0].length;value=dimensions[m[1]];dimensioned=true;}
  else{const m=/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/.exec(source.slice(at));if(!m)throw Error('Unsupported TikZ arithmetic: '+source.slice(at));at+=m[0].length;value=Number(m[0]);}
  skip();const unit=/^(bp|pt|cm|mm|in|pc|em|ex)\b/.exec(source.slice(at));if(unit){at+=unit[0].length;value*=unit[0]==='em'?em:unit[0]==='ex'?ex:units[unit[0]];dimensioned=true;}return sign*value;
 }
 function product(){let value=primary();for(;;){skip();const op=source[at];if(op!=='*'&&op!=='/')break;at++;const rhs=primary();if(op==='/'&&!rhs)throw Error('TikZ division by zero');value=op==='*'?value*rhs:value/rhs;}return value;}
 function sum(){let value=product();for(;;){skip();const op=source[at];if(op!=='+'&&op!=='-')break;at++;const rhs=product();value=op==='+'?value+rhs:value-rhs;}return value;}
 const value=sum();skip();if(at!==source.length||!Number.isFinite(value)||Math.abs(value)>1000000)throw Error('Invalid or excessive TikZ coordinate: '+source);return{value,dimensioned};
}
function optionList(text){return splitTikzArguments(text).map(raw=>{const eq=raw.indexOf('=');return eq<0?[raw,true]:[raw.slice(0,eq).trim(),raw.slice(eq+1).trim()];});}
function tikzColor(text){const parts=text.split('!');let color=parseColor(parts.shift());if(!color)return null;while(parts.length){const amount=parts.shift();if(!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(amount)||Number(amount)>100)return null;const other=parseColor(parts.shift()??'white');if(!other)return null;const t=Number(amount)/100;color=color.map((v,i)=>i===3?1:v*t+other[i]*(1-t));}return color;}
function stylesFrom(source){const styles=new Map();let at=0;
 while((at=source.indexOf('\\tikzset',at))>=0){const group=readGroup(source,at+8);if(!group)break;at=group.end;
  for(const [name,value]of optionList(group.value)){if(!name.endsWith('/.style')||typeof value!=='string'||!value.startsWith('{'))throw Error('Unsupported TikZ style declaration: '+name);styles.set(name.slice(0,-7),readGroup(value,0).value);}
 }return styles;
}
export function compileTikzPicture(content,{styles=new Map(),dimensions={},fontSize=10*pt,fontQuad=fontSize,labelBox=null,nodeRegistry=new Map()}={}){
 const items=[],nodes=nodeRegistry,dims={...dimensions};let at=0,operations=0;
 const defaults={x:units.cm,y:units.cm,scale:1,lineWidth:.4*pt,draw:false,fill:false,color:[0,0,0,1],shape:'rectangle',minimum:0,innerSep:scaled(fontQuad*.3333),outerSep:null};
 function number(value){return tikzNumber(value,{dimensions:dims,em:fontQuad,ex:fontSize*.430554});}
 function length(value){const n=number(value);return scaled(n.value*(n.dimensioned?1:pt));}
 function options(raw,base=defaults,chain=[]){const result={...base};for(const [name,value]of optionList(raw)){
   if(styles.has(name)){if(chain.includes(name)||chain.length>=16)throw Error('Recursive TikZ style: '+name);Object.assign(result,options(styles.get(name),result,[...chain,name]));continue;}
   if(['x','y','baseline','line width','minimum size','inner sep','outer sep'].includes(name)){const key={baseline:'baseline','line width':'lineWidth','minimum size':'minimum','inner sep':'innerSep','outer sep':'outerSep'}[name]??name;result[key]=length(String(value));continue;}
   if(name==='scale'){const n=number(String(value));if(n.dimensioned||n.value<=0)throw Error('Invalid TikZ scale');result.scale*=n.value;continue;}
   if(name==='circle'||name==='rectangle'){result.shape=name;continue;}
   if(name==='regular polygon'){result.shape='polygon';continue;}
   if(name==='regular polygon sides'){if(value!=='4')throw Error('Unsupported TikZ polygon side count: '+value);result.sides=4;continue;}
   if(name==='fill'||name==='draw'){result[name]=value!=='none'&&value!=='false';if(value!==true&&result[name]){const c=tikzColor(value);if(!c)throw Error('Unsupported TikZ color: '+value);result[name+'Color']=c;}continue;}
   const widths={'ultra thin':.1,'very thin':.2,thin:.4,semithick:.6,thick:.8,'very thick':1.2,'ultra thick':1.6};if(Object.hasOwn(widths,name)){result.lineWidth=widths[name]*pt;continue;}
   if(['dotted','densely dotted','loosely dotted','dashed','solid'].includes(name)){result.dash=name;continue;}
   if(name==='left'||name==='right'||name==='above'||name==='below'){result.position=name;result.separation=value===true?0:length(value);continue;}
   if(name==='out'||name==='in'||name==='looseness'){const n=number(String(value));if(n.dimensioned)throw Error('Invalid TikZ angle/looseness');result[name]=n.value;continue;}
   const c=value===true?tikzColor(name):null;if(c){result.color=c;continue;}
   throw Error('Unsupported TikZ option: '+name);
  }return result;
 }
 const skip=()=>{while(/\s/.test(content[at]??'')&&at<content.length)at++;};
 function bracket(){skip();const g=readGroup(content,at,'[',']');if(g){at=g.end;return g.value;}return '';}
 skip();const picture=options(bracket(),styles.has('every picture')?options(styles.get('every picture')):defaults);if(picture.shape==='polygon'&&picture.sides!==4)throw Error('TikZ polygon needs a supported side count');
 function coordinate(transform=picture){skip();const g=readGroup(content,at,'(',')');if(!g)throw Error('Expected TikZ coordinate');at=g.end;const parts=splitTikzArguments(g.value);
  if(parts.length===1){const n=nodes.get(parts[0]);if(!n)throw Error('Unknown TikZ node: '+parts[0]);return{x:n.x,y:n.y,node:n};}
  if(parts.length!==2)throw Error('Unsupported TikZ coordinate system: '+g.value);const x=number(parts[0]),y=number(parts[1]);return{x:scaled(x.value*(x.dimensioned?1:transform.x)*transform.scale),y:scaled(-y.value*(y.dimensioned?1:transform.y)*transform.scale)};
 }
 function add(item){if(items.length>=20000)throw Error('TikZ primitive limit');items.push({...item,tikz:true});}
 function node(point,style,name,text){const box=text?(labelBox?.(text)??null):{items:[],width:0,height:0,depth:0};if(!box)throw Error('TikZ text requires a label typesetter');
  let width=Math.max(style.minimum,box.width+2*style.innerSep),height=Math.max(style.minimum,box.height+box.depth+2*style.innerSep);
  if(style.shape==='circle'){const diameter=Math.max(style.minimum,Math.hypot(box.width+2*style.innerSep,box.height+box.depth+2*style.innerSep));width=height=diameter;}
  if(style.shape==='polygon'){
   if(style.sides!==4)throw Error('Unsupported TikZ regular polygon');
   const inner=scaled(Math.max(box.width/2+style.innerSep,(box.height+box.depth)/2+style.innerSep)*1.41421);
   const radius=Math.max(scaled(inner*1.41421),style.minimum/2);
   width=height=2*scaled(radius*.7071);
  }
  const outer=style.outerSep??style.lineWidth/2;let x=point.x,y=point.y;
  if(style.position){const amount=(style.separation??0)+outer;if(style.position==='left')x-=width/2+amount;if(style.position==='right')x+=width/2+amount;if(style.position==='above')y-=height/2+amount;if(style.position==='below')y+=height/2+amount;}
  const n={x,y,width,height,outer,shape:style.shape};if(name)nodes.set(name,n);
  // Invisible nodes still participate in the native picture's bounding box.
  add({kind:'bounds',x:x-width/2,y:y-height/2,width,height});
  if(style.draw||style.fill){if(style.shape==='circle')add({kind:'circle',x:x-width/2,y:y-height/2,width,height,radius:width/2,lineWidth:style.draw?style.lineWidth:0,fill:style.fill,color:style.color,fillColor:style.fillColor,strokeColor:style.drawColor});
   else if(style.shape==='rectangle'||style.shape==='polygon'&&style.sides===4)add({kind:'vectorrect',x:x-width/2,y:y-height/2,width,height,lineWidth:style.draw?style.lineWidth:0,fill:style.fill,color:style.color,fillColor:style.fillColor,strokeColor:style.drawColor});else throw Error('Unsupported TikZ shape: '+style.shape);}
  const baseline=y+(box.height-box.depth)/2;for(const item of box.items)add({...item,x:x-box.width/2+item.x,y:baseline+item.y});return n;
 }
 function nodeTail(point,base){let opt=styles.has('every node')?options(styles.get('every node'),base):{...base},name='';for(let count=0;count<8;count++){skip();if(content[at]==='['){opt=options(bracket(),opt);continue;}if(content[at]==='('){const g=readGroup(content,at,'(',')');name=g.value;at=g.end;continue;}if(content.slice(at,at+2)==='at'&&!/[A-Za-z]/.test(content[at+2]??'')){at+=2;point=coordinate(opt);continue;}break;}skip();const g=readGroup(content,at);if(!g)throw Error('Expected TikZ node text');at=g.end;node(point,opt,name,g.value);}
 function anchor(point,angle){if(!point.node)return{x:point.x,y:point.y};const n=point.node,radians=angle*Math.PI/180,dx=Math.cos(radians),dy=-Math.sin(radians),rx=n.width/2+n.outer,ry=n.height/2+n.outer;
  const distance=n.shape==='circle'?rx:Math.min(Math.abs(dx)>1e-12?rx/Math.abs(dx):Infinity,Math.abs(dy)>1e-12?ry/Math.abs(dy):Infinity);return{x:n.x+dx*distance,y:n.y+dy*distance};}
 function path(style){let point=coordinate(style);skip();const fill=style.fill,lineWidth=style.draw?style.lineWidth:0;
  if(content.slice(at,at+4)==='node'){at+=4;nodeTail(point,{...defaults,draw:false,fill:false});return;}
  if(content.slice(at,at+6)==='circle'){at+=6;const radius=coordinateRadius(style);add({kind:fill||lineWidth?'circle':'bounds',x:point.x-radius,y:point.y-radius,width:2*radius,height:2*radius,radius,lineWidth,fill,color:style.color,fillColor:style.fillColor,strokeColor:style.drawColor});skip();if(content.slice(at,at+4)==='node'){at+=4;nodeTail(point,{...defaults,draw:false,fill:false});}return;}
  if(content.slice(at,at+9)==='rectangle'){at+=9;const end=coordinate(style);add({kind:fill||lineWidth?'vectorrect':'bounds',x:Math.min(point.x,end.x),y:Math.min(point.y,end.y),width:Math.abs(end.x-point.x),height:Math.abs(end.y-point.y),lineWidth,fill,color:style.color,fillColor:style.fillColor,strokeColor:style.drawColor,dash:style.dash});return;}
  if(fill)throw Error('Filled multi-segment TikZ paths are not implemented');
  let edges=0;while(true){skip();const straight=content.startsWith('--',at),to=content.startsWith('to',at),cubic=content.startsWith('..',at);if(!straight&&!to&&!cubic)break;at+=2;const route=to?options(bracket(),style):style;let startPoint,endPoint,controls;
   if(cubic){
    skip();if(!/^controls\b/.test(content.slice(at)))throw Error('Expected TikZ controls');at+=8;
    const first=coordinate(route);skip();if(!/^and\b/.test(content.slice(at)))throw Error('Expected TikZ control separator and');at+=3;
    const second=coordinate(route);skip();if(!content.startsWith('..',at))throw Error('Expected TikZ cubic endpoint separator');at+=2;controls=[first,second];
   }
   const end=coordinate(route);
   if(cubic){startPoint=anchor(point,Math.atan2(point.y-controls[0].y,controls[0].x-point.x)*180/Math.PI);endPoint=anchor(end,Math.atan2(end.y-controls[1].y,controls[1].x-end.x)*180/Math.PI);}
   else if(to&&(route.out!==undefined||route.in!==undefined)){const out=route.out??0,into=route.in??180;startPoint=anchor(point,out);endPoint=anchor(end,into);const distance=pgfControlDistance(startPoint,endPoint)*(route.looseness??1),a=out*Math.PI/180,b=into*Math.PI/180;controls=[{x:scaled(startPoint.x+Math.cos(a)*distance),y:scaled(startPoint.y-Math.sin(a)*distance)},{x:scaled(endPoint.x+Math.cos(b)*distance),y:scaled(endPoint.y-Math.sin(b)*distance)}];}
   else{const angle=Math.atan2(point.y-end.y,end.x-point.x)*180/Math.PI;startPoint=anchor(point,angle);endPoint=anchor(end,angle+180);}
   if(style.draw)add({kind:controls?'bezier':'segment',x:startPoint.x,y:startPoint.y,endX:endPoint.x,endY:endPoint.y,...(controls?{controls}:{}),lineWidth,color:style.drawColor??style.color,dash:style.dash});
   else add({kind:'bounds',x:Math.min(startPoint.x,endPoint.x),y:Math.min(startPoint.y,endPoint.y),width:Math.abs(endPoint.x-startPoint.x),height:Math.abs(endPoint.y-startPoint.y)});point=end;edges++;
  }if(!edges)throw Error('Unsupported TikZ path operation: '+content.slice(at,at+35));
 }
 function coordinateRadius(style){skip();const g=readGroup(content,at,'(',')');if(!g)throw Error('Expected TikZ circle radius');at=g.end;const n=number(g.value);if(!n.dimensioned&&Math.abs(style.x)!==Math.abs(style.y))throw Error('Anisotropic TikZ circle radii are not implemented');const radius=n.value*(n.dimensioned?1:Math.abs(style.x))*style.scale;if(!(radius>0))throw Error('Invalid TikZ circle radius');return scaled(radius);}
 while(at<content.length){skip();if(at===content.length)break;if(++operations>5000)throw Error('TikZ command limit');const command=/^\\([A-Za-z]+)/.exec(content.slice(at));if(!command)throw Error('Unsupported TikZ syntax: '+content.slice(at,at+35));at+=command[0].length;
  if(command[1]==='multiply'||command[1]==='divide'){skip();const variable=/^\\([A-Za-z]+)\s*(?:by\s*)?([+-]?\d+)/.exec(content.slice(at));if(!variable||!Object.hasOwn(dims,variable[1]))throw Error('Unsupported TikZ dimension assignment');const factor=Number(variable[2]);if(command[1]==='divide'&&!factor)throw Error('TikZ division by zero');const value=command[1]==='multiply'?dims[variable[1]]*factor:Math.trunc(dims[variable[1]]/sp/factor)*sp;dims[variable[1]]=scaled(value);at+=variable[0].length;continue;}
  if(command[1]==='node')nodeTail({x:0,y:0},picture);
  else if(command[1]==='draw'||command[1]==='fill'){let base={...picture,draw:command[1]==='draw',fill:command[1]==='fill'};if(styles.has('every path'))base=options(styles.get('every path'),base);const style=options(bracket(),base);path(style);}
  else throw Error('Unsupported TikZ command: \\'+command[1]);skip();if(content[at++]!==';')throw Error('Expected TikZ path terminator');
 }
 let left=Infinity,top=Infinity,right=-Infinity,bottom=-Infinity;
 for(const item of items){if(item.kind==='segment'||item.kind==='bezier'){const points=[{x:item.x,y:item.y},{x:item.endX,y:item.endY},...(item.controls??[])];const pad=item.lineWidth/2;for(const p of points){left=Math.min(left,p.x-pad);right=Math.max(right,p.x+pad);top=Math.min(top,p.y-pad);bottom=Math.max(bottom,p.y+pad);}}else{const pad=item.lineWidth?item.lineWidth/2:0;left=Math.min(left,item.x-pad);right=Math.max(right,item.x+(item.width??0)+pad);top=Math.min(top,item.y-(item.height===undefined?0:pad));bottom=Math.max(bottom,item.y+(item.height??0)+pad);}}
 if(!items.length)return{items:[],width:0,height:0,depth:0,diagnostics:[],class:'ord'};
 const baseline=picture.baseline===undefined?bottom:-picture.baseline;
 // Curve points stay local to their primitive origin, so ordinary text/math
 // box translations and instance scales preserve the complete path.
 return{items:items.filter(i=>i.kind!=='bounds').map(item=>({...item,x:item.x-left,y:item.y-baseline,...(item.endX===undefined?{}:{delta:[item.endX-item.x,item.endY-item.y],endX:undefined,endY:undefined}),...(item.controls?{controls:item.controls.map(p=>({x:p.x-item.x,y:p.y-item.y}))}:{})})),width:right-left,height:Math.max(0,baseline-top),depth:Math.max(0,bottom-baseline),diagnostics:[],class:'ord'};
}

export function prepareTikzPictures(source,{fontSize=10*pt,fontQuad=fontSize,labelBox=null}={}){
 const styles=new Map(),dimensions={},boxes=[],nodeRegistry=new Map();let at=0,out='';
 const executable=maskTexLiterals(source);
 const token=/\\begin\{(?:tikzpicture|verbatim\*?)\}|\\verb\*?(?![A-Za-z])|\\(?:newlength|setlength|tikzset)\b/g;let match;
 function consume(end){out+=source.slice(at,match.index);at=end;token.lastIndex=end;}
 function dimensionName(index){return readGroup(source,index)??(()=>{const m=/^\s*(\\[A-Za-z]+)/.exec(source.slice(index));return m?{value:m[1],end:index+m[0].length}:null;})();}
 while((match=token.exec(source))){
  if(executable[match.index]!=='\\')continue;
  if(match[0].startsWith('\\begin{verbatim')){const endToken=match[0].replace('begin','end'),end=source.indexOf(endToken,token.lastIndex);token.lastIndex=end<0?source.length:end+endToken.length;continue;}
  if(match[0].startsWith('\\verb')){const delimiter=source[token.lastIndex],end=source.indexOf(delimiter,token.lastIndex+1);token.lastIndex=end<0?source.length:end+1;continue;}
  if(match[0]==='\\newlength'){const name=dimensionName(token.lastIndex);if(name){dimensions[name.value.replace(/^\\/,'')]=0;consume(name.end);}continue;}
  if(match[0]==='\\tikzset'){const value=readGroup(source,token.lastIndex);if(!value)throw Error('Unfinished TikZ style declaration');for(const [name,style]of stylesFrom(source.slice(match.index,value.end)))styles.set(name,style);consume(value.end);continue;}
  if(match[0]==='\\setlength'){const name=dimensionName(token.lastIndex),value=name&&readGroup(source,name.end);if(value){const key=name.value.replace(/^\\/,'');if(Object.hasOwn(dimensions,key)){dimensions[key]=scaled(tikzNumber(value.value,{dimensions,em:fontQuad}).value);consume(value.end);}else token.lastIndex=value.end;}continue;}
  const end=source.indexOf('\\end{tikzpicture}',token.lastIndex);if(end<0)throw Error('Unclosed TikZ picture');if(boxes.length>=256)throw Error('TikZ picture limit');let box;try{box=compileTikzPicture(source.slice(token.lastIndex,end),{styles,dimensions,fontSize,fontQuad,labelBox,nodeRegistry});}catch(error){throw Error('TikZ picture '+(boxes.length+1)+': '+error.message);}boxes.push(box);out+=source.slice(at,match.index)+'\\vkftikzbox{'+(boxes.length-1)+'}';at=end+17;token.lastIndex=at;
 }out+=source.slice(at);return{source:out,boxes,extension:{mathCommands:['\\vkftikzbox'],parseMathCommand(raw,{take,rawGroup}){take();const index=rawGroup();if(!/^\d+$/.test(index)||!boxes[Number(index)])throw Error('Invalid TikZ picture reference');return{type:'nativebox',box:boxes[Number(index)]};}}};
}
