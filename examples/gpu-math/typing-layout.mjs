import {parseDraft} from './draft-parser.mjs';
const pt=72/72.27;
const limitOperators=new Set('sum prod coprod bigcup bigcap bigvee bigwedge bigsqcup bigoplus bigotimes bigodot lim max min sup inf'.split(' ').map(t=>'\\'+t));
const matrixDelimiters={pmatrix:['(',')'],bmatrix:['[',']'],Bmatrix:['\\lbrace','\\rbrace'],vmatrix:['|','|'],Vmatrix:['\\Vert','\\Vert'],cases:['\\lbrace','.']};
/** Current-source visual draft; recovery never supplies an old operand. */
export function typeset(source,maps,{mode='display',equationStart=1,packages=null,extensions=[],displayEnvironment=false}={}){
 if(!['display','inline'].includes(mode))throw Error('Unknown math mode');
 const displayContext=displayEnvironment||/\\begin\{(?:align|equation|gather|multline)\*?\}/.test(source);
 const draft=parseDraft(source,maps.display,{packages,extensions});let activeFont='',activeColor=null,middleRequired=0,equationNumber=equationStart;
 const profile=style=>{const m=style===0?maps.display:style===1?(maps.text??maps.display):style===2?maps.script:maps.scriptscript;return activeFont==='boldsymbol'&&m.boldParameters?{...m,parameters:m.boldParameters}:m;};
 const add=(target,box,x,y)=>{for(const p of box.items)target.push({...p,x:p.x+x,y:p.y+y});};
 const empty=()=>({items:[],width:0,height:0,depth:0,class:'ord',italic:0});
 const table={ord:{ord:0,op:3,bin:4,rel:5,open:0,close:0,punct:0,inner:3},op:{ord:3,op:3,bin:0,rel:5,open:0,close:0,punct:0,inner:3},
 bin:{ord:4,op:4,open:4,inner:4,bin:4,close:0,punct:0,rel:0},rel:{ord:5,op:5,open:5,inner:5,rel:0,close:0,punct:0},
 open:{ord:0,op:0,bin:0,rel:0,open:0,close:0,punct:0,inner:0},close:{ord:0,op:3,bin:4,rel:5,open:0,close:0,punct:0,inner:3},
 punct:{ord:3,op:3,bin:0,rel:3,open:3,close:3,punct:3,inner:3},inner:{ord:3,op:3,bin:4,rel:5,open:3,close:0,punct:3,inner:3}};
 function glyph(token,style){const map=profile(style);
  if(activeFont&&!token.startsWith('@')){const key='@font:'+activeFont+':'+token;if(map.symbols[key])token=key;else if(/^[A-Za-z0-9]$/.test(token)){const message='Unsupported '+activeFont+' character: '+token;if(!draft.diagnostics.includes(message))draft.diagnostics.push(message);return hole(style);}}
  const s=map.symbols[token];
  if(!s)return hole(style);
  return{items:[{kind:'glyph',color:activeColor,key:`${map.style}/${token}`,x:0,y:0}],width:s.width,height:s.height,depth:s.depth,class:s.class,italic:s.italic??0,character:s.class!=='op',token,nucleus:{key:token,italic:s.italic??0,skew:s.skew??0,fontName:s.fontName,fontCode:s.fontCode,kerns:s.kerns}};
 }
 function hole(style){const size=profile(style).em*.32;return{items:[{kind:'placeholder',color:activeColor,x:0,y:-size,width:size,height:size}],width:size,height:size,depth:0,class:'ord',italic:0};}
 function layout(nodes,style,cramped=false){
  if(nodes.some(n=>n.type==='break'))return multiline(nodes,style,cramped);
  const restoreColor=activeColor;
  const boxes=[],tags=[];for(const node of nodes){if(node.type==='style'){style=node.style;continue;}if(node.type==='color'){activeColor=node.color;continue;}const box={...atom(node,style,cramped),style};if(box.tag)tags.push(box);else boxes.push(box);}
  const significant=boxes.filter(b=>!b.space);
  for(let i=0;i<significant.length;i++){
   if(significant[i].class==='bin'&&(i===0||['bin','op','rel','open','punct'].includes(significant[i-1].endClass??significant[i-1].class)))significant[i].class='ord';
   if(['rel','close','punct'].includes(significant[i].class)&&i&&significant[i-1].class==='bin')significant[i-1].class='ord';
  }if(significant.at(-1)?.class==='bin')significant.at(-1).class='ord';
  const out=empty();let prior=null;
  for(const b of boxes){
   if(prior&&!b.space){let mu=table[prior.endClass??prior.class]?.[b.class]??0;if(b.style>=2&&!(mu===3&&(prior.class==='op'||b.class==='op')))mu=0;out.width+=mu*profile(b.style).parameters.QUAD/18;}
   if(prior?.class==='ord'&&b.class==='ord'&&prior.nucleus&&b.nucleus&&prior.nucleus.fontName===b.nucleus.fontName&&/^(cmr|cmbx|cmti|cmbxti|cmss|cmssi|cmtt|cmmi|cmmib)\d/.test(prior.nucleus.fontName))out.width+=(prior.nucleus.kerns?.[String(b.nucleus.fontCode)]??0)-prior.nucleus.italic;
   const before=out.items.length;add(out.items,b,out.width,0);
   for(let j=before;j<out.items.length;j++){out.items[j].flowX=out.width;out.items[j].flowWidth=b.width;}
   out.width+=b.width;out.height=Math.max(out.height,b.height);out.depth=Math.max(out.depth,b.depth);if(!b.space)prior=b;
  }for(const tag of tags){add(out.items,tag,out.width+10*pt,0);out.width+=10*pt+tag.width;out.height=Math.max(out.height,tag.height);out.depth=Math.max(out.depth,tag.depth);}if(boxes.length===1)out.nucleus=boxes[0].nucleus;out.finalStyle=style;out.finalColor=activeColor;activeColor=restoreColor;return out;
 }
 function multiline(nodes,style,cramped){
  const restoreColor=activeColor,rows=[[]],gaps=[];for(const node of nodes){if(node.type==='break'){gaps.push(node.gap?dimension(node.gap,style):0);rows.push([]);}else rows.at(-1).push(node);}
  const boxes=[];for(const row of rows){const box=layout(row,style,cramped);box.height=Math.max(box.height,8.4*pt);box.depth=Math.max(box.depth,3.6*pt);boxes.push(box);style=box.finalStyle??style;activeColor=box.finalColor??activeColor;}
  const out=empty();out.lines=[];let baseline=0;
  for(let i=0;i<boxes.length;i++){const b=boxes[i];if(i)baseline+=boxes[i-1].depth+b.height+3*pt+(gaps[i-1]??0);
   for(const item of b.items)out.items.push({...item,y:item.y+baseline,flowLine:i});out.lines.push({height:b.height,depth:b.depth,baseline});out.width=Math.max(out.width,b.width);}
  out.height=boxes[0].height;out.depth=baseline+boxes.at(-1).depth;out.finalStyle=style;out.finalColor=activeColor;activeColor=restoreColor;return out;
 }
 function dimension(raw,style){
  const match=/^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(pt|bp|em|ex|mu|mm|cm|in|pc)\s*$/.exec(raw??'');
  if(!match){const message='Unfinished or unsupported dimension: '+raw;if(!draft.diagnostics.includes(message))draft.diagnostics.push(message);return 0;}
  const p=profile(style),factors={pt,bp:1,em:p.em,ex:p.parameters.XHEIGHT,mu:p.parameters.QUAD/18,mm:72/25.4,cm:72/2.54,in:72,pc:12*pt};return Math.max(-10000,Math.min(10000,Number(match[1])*factors[match[2]]));
 }
 function assemble(key,style,required){
  let s=profile(style).symbols[key],seen=new Set();
  while(s?.nextLarger!==null&&s?.nextLarger!==undefined&&!seen.has(key)&&s.height+s.depth<required){seen.add(key);key='@ext:'+s.nextLarger;s=profile(style).symbols[key];}
  if(!s)return hole(style);
  if(s.height+s.depth>=required||!s.extension)return glyph(key,style);
  const recipe=s.extension,part=code=>glyph('@ext:'+code,style),repeat=part(recipe.rep),span=b=>b.height+b.depth;
  const top=recipe.top?part(recipe.top):null,mid=recipe.mid?part(recipe.mid):null,bot=recipe.bot?part(recipe.bot):null;
  const fixed=[top,mid,bot].reduce((n,b)=>n+(b?span(b):0),0),count=Math.max(0,Math.ceil((required-fixed)/(span(repeat)*(mid?2:1))));
  const pieces=[...(top?[top]:[]),...Array(count).fill(repeat),...(mid?[mid,...Array(count).fill(repeat)]:[]),...(bot?[bot]:[])];
  const out=empty();out.width=repeat.width;out.height=pieces[0]?.height??0;let y=-out.height;
  for(const piece of pieces){y+=piece.height;add(out.items,piece,0,y);y+=piece.depth;}out.depth=y;return out;
 }
 function radical(node,style,cramped){
  const p=profile(style).parameters,body=layout(node.children,style,true);let clear=p.RULE+(style===0?Math.abs(p.XHEIGHT):p.RULE)/4;
  const required=body.height+body.depth+clear+p.RULE;let mark=glyph('@sqrt',style);for(const larger of style===3?[2,1]:style===2?[1]:[]){if(mark.height+mark.depth>=required)break;mark=glyph('@sqrt',larger);}if(mark.height+mark.depth<required)mark=assemble('@ext:112',style,required);const delta=mark.depth-(body.height+body.depth+clear);if(delta>0)clear+=delta/2;
  const out={...empty(),width:mark.width+body.width,height:body.height+clear+2*mark.height,depth:Math.max(body.depth,mark.depth-body.height-clear),character:false};
  add(out.items,mark,0,-body.height-clear);add(out.items,body,mark.width,0);
  out.items.push({kind:'rule',color:activeColor,x:mark.width,y:-body.height-clear-mark.height,width:body.width,height:mark.height});
  if(node.index){const index=layout(node.index,3,false),mu=p.QUAD/18,offset=5*mu+index.width-10*mu,shift=-.6*(out.height-out.depth);for(const item of out.items)item.x+=offset;add(out.items,index,5*mu,shift);out.width+=offset;out.height=Math.max(out.height,index.height-shift);out.depth=Math.max(out.depth,index.depth+shift);}
  return out;
 }
 function textBox(nodes,style){
  const out=empty();let prior=null;
  for(let i=0;i<nodes.length;i++){
   const node=nodes[i];if(node.type==='hole'){const b=hole(style);add(out.items,b,out.width,0);out.width+=b.width;out.height=Math.max(out.height,b.height);prior=null;continue;}
   if(prior&&prior.fontName?.startsWith('cmti')&&(node.char===' '||node.font!=='mathit')){out.width+=prior.italic??0;prior=null;}
   if(node.char===' '){out.width+=profile(style).textFontSpaces?.[node.font]?.space??profile(style).textSpace??profile(style).em/3;prior=null;continue;}
   let chars=node.char;
   if(node.font==='mathrm')for(const ligature of ['ffi','ffl','ff','fi','fl']){if(nodes.slice(i,i+ligature.length).length===ligature.length&&nodes.slice(i,i+ligature.length).every((n,j)=>n.char===ligature[j]&&n.font==='mathrm')&&profile(style).symbols['@text:'+ligature]){chars=ligature;i+=ligature.length-1;break;}}
   const token=node.font==='mathrm'?(profile(style).symbols['@text:'+chars]?'@text:'+chars:'@roman:'+chars):profile(style).symbols['@font:'+node.font+':'+chars]?'@font:'+node.font+':'+chars:profile(style).symbols['@text:'+chars]?'@text:'+chars:'@roman:'+chars;
   const g=glyph(token,style),metric=profile(style).symbols[token];
   if(!metric){draft.diagnostics.push('Unsupported text character: '+chars);add(out.items,g,out.width,0);out.width+=g.width;prior=null;continue;}
   if(prior&&prior.fontName===metric.fontName)out.width+=prior.kerns?.[String(metric.fontCode)]??0;
   add(out.items,g,out.width,0);out.width+=metric.advance??g.width;out.height=Math.max(out.height,g.height);out.depth=Math.max(out.depth,g.depth);prior=metric;
  }return out;
 }
 function boxed(node,style,cramped){
  const body=layout(node.children,node.name==='boxed'?0:style,cramped),out={...body,class:'ord',character:false,nucleus:null};
  if(['phantom','hphantom','vphantom','mathstrut'].includes(node.name)){out.items=[];if(node.name==='vphantom'||node.name==='mathstrut')out.width=0;if(node.name==='hphantom')out.height=out.depth=0;}
  else if(node.name==='smash'){if(node.option!=='b')out.height=0;if(node.option!=='t')out.depth=0;}
  else{const rule=.4*pt,pad=3*pt+rule;out.items=[];out.width=body.width+2*pad;out.height=body.height+pad;out.depth=body.depth+pad;add(out.items,body,pad,0);for(const [x,y,width,height]of [[0,-out.height,out.width,rule],[0,out.depth-rule,out.width,rule],[0,-out.height+rule,rule,out.height+out.depth-2*rule],[out.width-rule,-out.height+rule,rule,out.height+out.depth-2*rule]])out.items.push({kind:'rule',color:activeColor,x,y,width,height});}
  return out;
 }
 function modulo(node,style,cramped){
  const mu=profile(style).parameters.QUAD/18,word=textBox([...node.name==='pod'?'':'mod'].map(char=>({type:'textchar',char,font:'mathrm'})),style),body=layout(node.children,style,cramped),out={...empty(),space:node.name!=='bmod',class:node.name==='bmod'?'bin':'ord'};
  const lead=node.name==='bmod'?(style<2?1:5):displayContext?18:node.name==='mod'?12:8;out.width=lead*mu;
  const nodes=[];if(node.name!=='mod'&&node.name!=='bmod')nodes.push(glyph('(',style));if(node.name!=='pod')nodes.push(word);
  for(const box of nodes){add(out.items,box,out.width,0);out.width+=box.width;out.height=Math.max(out.height,box.height);out.depth=Math.max(out.depth,box.depth);}
  if(node.name==='pmod'||node.name==='mod')out.width+=6*mu;
  add(out.items,body,out.width,0);out.width+=body.width;out.height=Math.max(out.height,body.height);out.depth=Math.max(out.depth,body.depth);
  if(node.name==='pmod'||node.name==='pod'){const r=glyph(')',style);add(out.items,r,out.width,0);out.width+=r.width;out.height=Math.max(out.height,r.height);out.depth=Math.max(out.depth,r.depth);}if(node.name==='bmod')out.width+=(style<2?1:5)*mu;return out;
 }
 function delimiter(token,style,required){
  const aliases={'\\{':'\\lbrace','\\}':'\\rbrace','\\vert':'|','\\lvert':'|','\\rvert':'|','\\|':'\\Vert'},initial={'(':0,')':1,'[':2,']':3,'\\lfloor':4,'\\rfloor':5,'\\lceil':6,'\\rceil':7,'\\lbrace':8,'\\rbrace':9,'\\langle':10,'\\rangle':11,'|':12,'\\Vert':13,'/':14,'\\backslash':15,'\\uparrow':120,'\\downarrow':121,'\\updownarrow':63,'\\Uparrow':126,'\\Downarrow':127,'\\Updownarrow':119};
  token=aliases[token]??token;const map=profile(style),axis=map.parameters.AXISHEIGHT;
  if(token==='.')return{...empty(),width:1.2*pt};
  let chosen=glyph(token,style);for(const larger of style===3?[2,1]:style===2?[1]:[]){if(chosen.height+chosen.depth>=required)break;chosen=glyph(token,larger);}
  if(chosen.height+chosen.depth<required){
   if(initial[token]!==undefined&&map.symbols['@ext:'+initial[token]])chosen=assemble('@ext:'+initial[token],style,required);
   else{const message='Unsupported extensible delimiter: '+token;if(!draft.diagnostics.includes(message))draft.diagnostics.push(message);return hole(style);}
  }
  const shift=(chosen.height-chosen.depth)/2-axis;return{...chosen,items:chosen.items.map(i=>({...i,y:i.y+shift})),height:chosen.height-shift,depth:chosen.depth+shift,class:'ord',character:false};
 }
 function enclose(content,left,right,style,scalable=true){
  const axis=profile(style).parameters.AXISHEIGHT,delta=Math.max(content.height-axis,content.depth+axis);
  const required=scalable?Math.max(1.802*delta,2*delta-5*pt):0;
  const l=delimiter(left,style,required),r=delimiter(right,style,required),b={...empty(),class:'inner'};
  add(b.items,l,0,0);add(b.items,content,l.width,0);add(b.items,r,l.width+content.width,0);
  b.width=l.width+content.width+r.width;b.height=Math.max(l.height,content.height,r.height);b.depth=Math.max(l.depth,content.depth,r.depth);if(!scalable){b.class='open';b.endClass='close';b.character=true;}return b;
 }
 function matrix(node,style){
  const name=node.name.replace(/\*$/,''),small=name==='smallmatrix',aligned=['aligned','align','split'].includes(name),display=['align','split','equation','multline','gather','gathered'].includes(name),childStyle=small?2:display?0:Math.max(1,style);
  if(name==='equation'){const body=layout(node.rows.flat(2),childStyle);if(!node.name.endsWith('*')&&!node.rows.flat(2).some(n=>n.noNumber||n.type==='tag')){const tag=atom({type:'tag',children:[...String(equationNumber++)].map(char=>({type:'textchar',char,font:'mathrm'}))},style);for(const item of tag.items)body.items.push({...item,x:body.width+10*pt+item.x,equationTag:true,tagWidth:tag.width});}return body;}
  const rows=node.rows.length?node.rows:[[[]]],cells=rows.map(row=>row.map((nodes,j)=>nodes.length?layout(aligned&&j%2?[{type:'group',children:[]},...nodes.filter(n=>n.type!=='tag')]:nodes.filter(n=>n.type!=='tag'),childStyle):hole(childStyle)));
  const columns=Math.max(1,...cells.map(row=>row.length));if(columns>32||rows.length>100)throw Error('Matrix limit: 32 columns and 100 rows');
  const widths=Array.from({length:columns},(_,j)=>Math.max(0,...cells.map(row=>row[j]?.width??0))),cases=name==='cases',factor=cases?1.2:small?.6:1;
  const heights=cells.map(row=>Math.max((8.4*factor+(aligned?1.5:0))*pt,...row.map(b=>b.height))),depths=cells.map(row=>Math.max((3.6*factor+(aligned?1.5:0))*pt,...row.map(b=>b.depth)));
  const rowGaps=rows.map((_,i)=>node.rowGaps?.[i]?dimension(node.rowGaps[i],style):0),rule=profile(style).parameters.RULE,hrules=node.rules??[];
  const total=heights.reduce((a,h,i)=>a+h+depths[i]+(i<rows.length-1?rowGaps[i]:0),0)+hrules.length*rule,axis=profile(style).parameters.AXISHEIGHT;
  const box={...empty(),height:total/2+axis,depth:total/2-axis,class:'inner'},array=name==='array',padding=array?5*pt:0,align=(node.align??'').replace(/[^clr]/g,'');
  const gaps=Array.from({length:columns-1},(_,j)=>aligned?(j%2?20*pt:0):cases?10*pt:small?3*pt:10*pt);
  const vcount=Array(columns+1).fill(0);if(array){let c=0;for(const char of node.align){if(/[clr]/.test(char))c++;else if(char==='|')vcount[Math.min(c,columns)]++;}}
  const vspace=vcount.map(c=>c*rule+Math.max(0,c-1)*2*pt);box.width=widths.reduce((a,w)=>a+w,0)+gaps.reduce((a,g)=>a+g,0)+2*padding+vspace.reduce((n,w)=>n+w,0);
  let y=-box.height;const boundaries=[0];for(let j=0,x=padding+vspace[0];j<columns;j++){x+=widths[j];boundaries.push(j===columns-1?box.width-vspace[columns]:x+(gaps[j]??0)/2);x+=(gaps[j]??0)+vspace[j+1];}
  const drawRule=(r,top)=>{let left=0,right=box.width;if(r.columns){const match=/^(\d+)-(\d+)$/.exec(r.columns);if(!match||Number(match[1])<1||Number(match[2])>columns){draft.diagnostics.push('Unsupported cline range');return;}left=Number(match[1])===1?0:boundaries[Number(match[1])-1];right=Number(match[2])===columns?box.width:boundaries[Number(match[2])];}box.items.push({kind:'rule',color:activeColor,x:left,y:top,width:right-left,height:rule});};
  for(let i=0;i<cells.length;i++){
   for(const r of hrules.filter(r=>r.row===i)){drawRule(r,y);y+=rule;}y+=heights[i];let x=padding+vspace[0];
   for(let j=0;j<columns;j++){const c=cells[i][j]??hole(childStyle),mode=cases?'l':aligned?(j%2?'l':'r'):name==='multline'?(i===0?'l':i===cells.length-1?'r':'c'):(align[j]??'c');
    const shift=mode==='l'?0:mode==='r'?widths[j]-c.width:(widths[j]-c.width)/2;add(box.items,c,x+shift,y);x+=widths[j]+(gaps[j]??0)+vspace[j+1];
   }
   const custom=rows[i].flat().find(n=>n.type==='tag'),numbered=['equation','align','gather','multline'].includes(name)&&!node.name.endsWith('*')&&!rows[i].flat().some(n=>n.noNumber),showNumber=name!=='multline'||i===cells.length-1;
   if(custom||numbered&&showNumber){const number=custom??{type:'tag',children:[...String(equationNumber++)].map(char=>({type:'textchar',char,font:'mathrm'}))},tag=atom(number,style);for(const item of tag.items)box.items.push({...item,x:box.width+10*pt+item.x,y:y+item.y,equationTag:true,tagWidth:tag.width});}
   y+=depths[i]+(i<rows.length-1?rowGaps[i]:0);
  }
  for(const r of hrules.filter(r=>r.row>=cells.length))drawRule(r,box.depth-rule);
  if(array)for(let column=0;column<=columns;column++)for(let k=0;k<vcount[column];k++)box.items.push({kind:'rule',color:activeColor,x:boundaries[column]+k*(rule+2*pt),y:-box.height,width:rule,height:box.height+box.depth});
  const pair=matrixDelimiters[name];return pair?enclose(box,pair[0],pair[1],style):box;
 }
 function accent(node,style,cramped){
  const map=profile(style),p=map.parameters,body=layout(node.children,style,true);let mark,skew=0;
  const single=!!body.nucleus;if(single)skew=body.nucleus.skew;
  if(node.name==='dddot'||node.name==='ddddot'){
   mark=empty();const dot=glyph('@accent:dot',style),count=node.name==='dddot'?3:4;mark.width=dot.width+(count-1)*map.em*.2;mark.height=dot.height;mark.depth=dot.depth;
   for(let i=0;i<count;i++)add(mark.items,dot,i*map.em*.2,0);
  }else{
   let key='@accent:'+node.name;
   if(node.name==='widehat'||node.name==='widetilde'){const useAMS=layout(node.children,1,true).width>2*profile(1).em;key+=useAMS?'AMS0':'0';for(let i=1;i<(useAMS?2:3);i++){const candidate='@accent:'+node.name+(useAMS?'AMS':'')+i;if(map.symbols[candidate]?.width<=body.width)key=candidate;}}
   mark=glyph(key,style);
  }
  const delta=Math.min(body.height,map.symbols[mark.token]?.fontXHeight??p.XHEIGHT),y=-body.height+delta,b={...body,class:'ord',italic:0,character:single};
  add(b.items,mark,(body.width-mark.width)/2+skew,y);b.height=Math.max(body.height,mark.height-y);b.depth=Math.max(body.depth,mark.depth+y);return b;
 }
 function arrow(direction,width,style){
  const map=profile(style),first=glyph(direction==='right'?'-':'\\leftarrow',style),last=glyph(direction==='left'?'-':'\\rightarrow',style);
  if(direction==='right'){first.height=0;first.depth=0;}if(direction==='left'){last.height=0;last.depth=0;}
  const target=Math.max(width,first.width+last.width-14*map.parameters.QUAD/18),b={...empty(),width:target,height:Math.max(first.height,last.height),depth:Math.max(first.depth,last.depth),class:'ord',character:false};
  add(b.items,first,0,0);add(b.items,last,target-last.width,0);
  // TeX's overlapping relbar leaders form one continuous shaft.
  const lo=first.width-7*map.parameters.QUAD/18,hi=target-last.width+7*map.parameters.QUAD/18;
  if(hi>lo)b.items.push({kind:'rule',color:activeColor,x:lo,y:map.symbols['-'].inkBounds[1],width:hi-lo,height:map.symbols['-'].inkBounds[3]-map.symbols['-'].inkBounds[1]});
  return b;
 }
 function brace(body,under){
  // TeX's four fixed font pieces joined by two extensible horizontal rules.
  const names=under?['bracelu','bracerd','braceld','braceru']:['braceld','braceru','bracelu','bracerd'];
  const pieces=names.map(n=>glyph('@'+n,1)),width=Math.max(body.width,pieces.reduce((sum,g)=>sum+g.width,0));
  const gap=(width-pieces.reduce((sum,g)=>sum+g.width,0))/2;
  const mark=empty();mark.width=width;mark.height=Math.max(...pieces.map(g=>g.height));mark.depth=Math.max(...pieces.map(g=>g.depth));
  let x=0;for(let i=0;i<4;i++){add(mark.items,pieces[i],x,0);x+=pieces[i].width;if(i===0||i===2){if(gap>0)mark.items.push({kind:'rule',color:activeColor,x,y:-mark.height,width:gap,height:mark.height});x+=gap;}}
  const b={...empty(),width,height:body.height,depth:body.depth,class:'op',character:false,italic:0};add(b.items,body,(width-body.width)/2,0);
  const y=under?body.depth+3*pt+mark.height:-body.height-3*pt-mark.depth;add(b.items,mark,0,y);
  if(under)b.depth=y+mark.depth+3*pt;else b.height=-y+mark.height+3*pt;return b;
 }
 function decorate(node,style,cramped){
  const p=profile(style).parameters;
  if(!['overline','underline','overbrace','underbrace'].includes(node.name)&&!node.name.includes('arrow'))return accent(node,style,cramped);
  if(node.name==='overbrace'||node.name==='underbrace')return brace(layout(node.children,0,cramped),node.name==='underbrace');
  const under=node.name.startsWith('under'),body=layout(node.children,style,node.name==='overline'?true:cramped),b={...body,class:'ord',italic:0,character:false};
  if(node.name==='overline'||node.name==='underline'){
   b.items.push({kind:'rule',color:activeColor,x:0,y:under?body.depth+3*p.RULE:-body.height-4*p.RULE,width:body.width,height:p.RULE});
   if(under)b.depth+=5*p.RULE;else b.height+=5*p.RULE;return b;
  }
  const direction=node.name.includes('leftright')?'both':node.name.includes('left')?'left':'right',mark=arrow(direction,body.width,style),width=Math.max(body.width,mark.width);
  b.items=[];add(b.items,body,(width-body.width)/2,0);const y=under?body.depth+1.3*pt+mark.height:-body.height-mark.depth;
  add(b.items,mark,0,y);b.width=width;b.height=Math.max(body.height,mark.height-y);b.depth=Math.max(body.depth,y+mark.depth);return b;
 }

 function atom(node,style,cramped=false){const map=profile(style),p=map.parameters;let b;
  if(node.type==='hole')b=hole(style);
  else if(node.type==='glyph'){b=glyph(node.token,style);if(node.class)b.class=node.class;}
  else if(node.type==='space')return{...empty(),width:node.mu*map.parameters.QUAD/18,space:true};
  else if(node.type==='font'){const previous=activeFont;activeFont=node.name;b=layout(node.children,style,cramped);b.character=!!b.nucleus;b.italic=b.nucleus?.italic??0;activeFont=previous;}
  else if(node.type==='paint'){const previous=activeColor;activeColor=node.color;b=layout(node.children,style,cramped);activeColor=previous;}
  else if(node.type==='group'){b=layout(node.children,style,cramped);if(node.unit)b.character=true;}
  else if(node.type==='delimited'){const previous=middleRequired;let body=layout(node.children,style,cramped);if(node.children.some(n=>n.type==='middle')){const delta=Math.max(body.height-p.AXISHEIGHT,body.depth+p.AXISHEIGHT);middleRequired=Math.max(1.802*delta,2*delta-5*pt);body=layout(node.children,style,cramped);}b=enclose(body,node.left,node.right,style,node.scalable);middleRequired=previous;}
  else if(node.type==='matrix')b=matrix(node,style);
  else if(node.type==='decoration')b=decorate(node,style,cramped);
  else if(node.type==='stack'){b=layout(node.children,style,cramped);b.class=node.children.length===1&&node.children[0].type==='glyph'?(map.symbols[node.children[0].token]?.class??'ord'):'ord';b.stacked=true;}
  else if(node.type==='arrow'){const labelStyle=style<2?2:3,sup=node.sup?layout(node.sup,labelStyle):empty(),sub=node.sub?layout(node.sub,labelStyle):empty(),pad=14*profile(labelStyle).parameters.QUAD/18;b=arrow(node.name==='xleftarrow'?'left':'right',Math.max(sup.width,sub.width)+pad,0);b.class='rel';b.stacked=true;b.arrowLabel=true;}
  else if(node.type==='dimension')b={...empty(),width:dimension(node.dimension,style),space:true};
  else if(node.type==='radical')b=radical(node,style,cramped);
  else if(node.type==='box')b=boxed(node,style,cramped);
  else if(node.type==='mod')b=modulo(node,style,cramped);
  else if(node.type==='middle')b=delimiter(node.token,style,middleRequired);
  else if(node.type==='tag'){const body=textBox(node.children,style);b=node.star?body:enclose(body,'(',')',style,false);b.tag=true;}
  else if(node.type==='textflow'){b=textBox(node.children,style);b.class=node.class??'ord';b.operatorLimits=node.operatorLimits;}
  else if(node.type==='text'){
   b=empty();b.class=node.class;
   for(const char of node.text){if(char===' '){b.width+=map.em/3;continue;}const g=glyph(map.symbols['@text:'+char]?'@text:'+char:map.symbols['@roman:'+char]?'@roman:'+char:char,style);add(b.items,g,b.width,0);b.width+=g.width;b.height=Math.max(b.height,g.height);b.depth=Math.max(b.depth,g.depth);}
  }else{
   const fractionStyle=node.style??style,q=profile(fractionStyle).parameters,childStyle=fractionStyle===0?1:Math.min(3,fractionStyle+1),n=layout(node.num,childStyle,cramped),d=layout(node.den,childStyle,true);
   const rule=node.thickness===undefined||node.thickness===''?q.RULE:Math.max(0,dimension(node.thickness,fractionStyle)),axis=q.AXISHEIGHT,clear=rule?(fractionStyle===0?3*rule:rule):(fractionStyle===0?7:3)*q.RULE;
   let up=fractionStyle===0?q.NUM1:rule?q.NUM2:q.NUM3,down=fractionStyle===0?q.DENOM1:q.DENOM2;if(rule){up=Math.max(up,n.depth+axis+rule/2+clear);down=Math.max(down,d.height-axis+rule/2+clear);}else{const delta=(clear-(up-n.depth-(d.height-down)))/2;if(delta>0){up+=delta;down+=delta;}}
   const pad=node.left||node.right?0:1.2*pt,width=Math.max(n.width,d.width)+2*pad;
   b={...empty(),width,height:n.height+up,depth:d.depth+down};add(b.items,n,(width-n.width)/2,-up);add(b.items,d,(width-d.width)/2,down);
   if(rule)b.items.push({kind:'rule',color:activeColor,x:pad,y:-axis-rule/2,width:width-2*pad,height:rule});
   if(node.left||node.right){const required=fractionStyle===0?q.DELIM1:q.DELIM2,left=delimiter(node.left??'.',fractionStyle,required),right=delimiter(node.right??'.',fractionStyle,required),body=b;b={...empty(),class:'inner',width:left.width+body.width+right.width,height:Math.max(left.height,body.height,right.height),depth:Math.max(left.depth,body.depth,right.depth)};add(b.items,left,0,0);add(b.items,body,left.width,0);add(b.items,right,left.width+body.width,0);}
  }
  if(node.sup||node.sub){
   const scriptStyle=style<2?2:3,q=profile(scriptStyle).parameters,sup=node.sup?layout(node.sup,scriptStyle,cramped):null,sub=node.sub?layout(node.sub,scriptStyle,true):null;
   const useLimits=node.limits??(style===0&&(node.operatorLimits||limitOperators.has(node.token)));
   if((b.class==='op'||b.stacked)&&useLimits){
    const labelPad=b.arrowLabel?3*profile(scriptStyle).parameters.QUAD/18:0,labelShift=b.arrowLabel?(node.name==='xleftarrow'?labelPad/2:-labelPad/2):0;
    const width=Math.max(b.width,(sup?.width??0)+labelPad,(sub?.width??0)+labelPad),items=[];add(items,b,(width-b.width)/2,0);
    if(sup){const up=b.height+Math.max(p.BIGOPSPACING1,p.BIGOPSPACING3-sup.depth)+sup.depth;add(items,sup,(width-sup.width+b.italic)/2+labelShift,-up);b.height=up+sup.height+p.BIGOPSPACING5;}
    if(sub){const down=b.depth+Math.max(p.BIGOPSPACING2,p.BIGOPSPACING4-sub.height)+sub.height;add(items,sub,(width-sub.width-b.italic)/2+labelShift,down);b.depth=down+sub.depth+p.BIGOPSPACING5;}
    b.items=items;b.width=width;
   }else{
    let up=b.character?0:b.height-q.SUPDROP,down=b.character?0:b.depth+q.SUBDROP;
    if(sup)up=Math.max(up,cramped?p.SUP3:style===0?p.SUP1:p.SUP2,sup.depth+p.XHEIGHT/4);
    if(sub)down=Math.max(down,sup?p.SUB2:p.SUB1,sub.height-.8*p.XHEIGHT);
    if(sup&&sub){down=Math.max(down,4*p.RULE-up+sup.depth+sub.height);const shift=.8*p.XHEIGHT-up+sup.depth;if(shift>0){up+=shift;down-=shift;}}
    const width=b.width,space=.5*pt;
    if(sup){add(b.items,sup,width,-up);b.width=Math.max(b.width,width+sup.width+space);b.height=Math.max(b.height,up+sup.height);}
    if(sub){add(b.items,sub,width-b.italic,down);b.width=Math.max(b.width,width-b.italic+sub.width+space);b.depth=Math.max(b.depth,down+sub.depth);}
   }
  }if(node.sup||node.sub)b.nucleus=null;return b;
 }
 const out=source.trim()?layout(draft.nodes,mode==='inline'?1:0):empty();
 return{...out,source,mode,atoms:draft.atoms,diagnostics:draft.diagnostics,complete:draft.diagnostics.length===0,nextEquationNumber:equationNumber};
}
