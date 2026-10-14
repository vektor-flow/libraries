import {parseDraft} from './draft-parser.mjs';
const pt=72/72.27;
const limitOperators=new Set('sum prod coprod bigcup bigcap bigvee bigwedge bigsqcup bigoplus bigotimes bigodot lim max min sup inf'.split(' ').map(t=>'\\'+t));
const matrixDelimiters={pmatrix:['(',')'],bmatrix:['[',']'],Bmatrix:['\\lbrace','\\rbrace'],vmatrix:['|','|'],Vmatrix:['\\Vert','\\Vert'],cases:['\\lbrace','.']};
/** Current-source visual draft; recovery never supplies an old operand. */
export function typeset(source,maps,{mode='display'}={}){
 if(!['display','inline'].includes(mode))throw Error('Unknown math mode');
 const draft=parseDraft(source,maps.display);
 const profile=style=>style===0?maps.display:style===1?(maps.text??maps.display):style===2?maps.script:maps.scriptscript;
 const add=(target,box,x,y)=>{for(const p of box.items)target.push({...p,x:p.x+x,y:p.y+y});};
 const empty=()=>({items:[],width:0,height:0,depth:0,class:'ord',italic:0});
 const table={ord:{ord:0,op:3,bin:4,rel:5,open:0,close:0,punct:0,inner:3},op:{ord:3,op:3,bin:0,rel:5,open:0,close:0,punct:0,inner:3},
 bin:{ord:4,op:4,open:4,inner:4,bin:4,close:0,punct:0,rel:0},rel:{ord:5,op:5,open:5,inner:5,rel:0,close:0,punct:0},
 open:{ord:0,op:0,bin:0,rel:0,open:0,close:0,punct:0,inner:0},close:{ord:0,op:3,bin:4,rel:5,open:0,close:0,punct:0,inner:3},
 punct:{ord:3,op:3,bin:0,rel:3,open:3,close:3,punct:3,inner:3},inner:{ord:3,op:3,bin:4,rel:5,open:3,close:0,punct:3,inner:3}};
 function glyph(token,style){const map=profile(style),s=map.symbols[token];
  if(!s)return hole(style);
  return{items:[{kind:'glyph',key:`${map.style}/${token}`,x:0,y:0}],width:s.width,height:s.height,depth:s.depth,class:s.class,italic:s.italic??0,character:s.class!=='op',token};
 }
 function hole(style){const size=profile(style).em*.32;return{items:[{kind:'placeholder',x:0,y:-size,width:size,height:size}],width:size,height:size,depth:0,class:'ord',italic:0};}
 function layout(nodes,style,cramped=false){
  const boxes=[];for(const node of nodes){if(node.type==='style'){style=node.style;continue;}boxes.push({...atom(node,style,cramped),style});}
  const significant=boxes.filter(b=>!b.space);
  for(let i=0;i<significant.length;i++){
   if(significant[i].class==='bin'&&(i===0||['bin','op','rel','open','punct'].includes(significant[i-1].endClass??significant[i-1].class)))significant[i].class='ord';
   if(['rel','close','punct'].includes(significant[i].class)&&i&&significant[i-1].class==='bin')significant[i-1].class='ord';
  }if(significant.at(-1)?.class==='bin')significant.at(-1).class='ord';
  const out=empty();let prior=null;
  for(const b of boxes){
   if(prior&&!b.space){let mu=table[prior.endClass??prior.class]?.[b.class]??0;if(b.style>=2&&!(mu===3&&(prior.class==='op'||b.class==='op')))mu=0;out.width+=mu*profile(b.style).em/18;}
   const before=out.items.length;add(out.items,b,out.width,0);
   for(let j=before;j<out.items.length;j++){out.items[j].flowX=out.width;out.items[j].flowWidth=b.width;}
   out.width+=b.width;out.height=Math.max(out.height,b.height);out.depth=Math.max(out.depth,b.depth);if(!b.space)prior=b;
  }return out;
 }
 function delimiter(token,style,required){
  const map=profile(style),axis=map.parameters.AXISHEIGHT;
  if(token==='.')return{...empty(),width:1.2*pt};
  const keys=[token,...['big','Big','bigg','Bigg'].map(size=>'@'+size+':'+token)].filter(k=>map.symbols[k]);
  if(!keys.length)return hole(style);
  const key=keys.find(k=>map.symbols[k].height+map.symbols[k].depth>=required)??keys.at(-1),s=map.symbols[key],b=glyph(key,style),span=s.height+s.depth;
  if(span>=required)return{...b,class:'ord',character:false};
  const target=Math.max(span,required),top=-axis-target/2,bottom=-axis+target/2;
  // Long stems grow while font-derived caps and brace waist keep their shape.
  if(['(',')','[',']','\\lbrace','\\rbrace','|','\\Vert','\\lfloor','\\rfloor','\\lceil','\\rceil'].includes(token)){
   const bounds=s.inkBounds??[0,-s.height,s.width,s.depth],lo=bounds[1],hi=bounds[3],length=hi-lo;
   const brace=token==='\\lbrace'||token==='\\rbrace';
   const fractions=brace?[0,.2,.4,.6,.8,1]:[0,.25,.75,1];
   const intervals=fractions.slice(0,-1).map((f,i)=>[lo+length*f,lo+length*fractions[i+1]]);
   const flexible=brace?new Set([1,3]):new Set([1]);
   const fixed=intervals.reduce((a,[l,h],i)=>a+(flexible.has(i)?0:h-l),0),flexLength=length-fixed;
   let y=top;const items=[];
   intervals.forEach(([l,h],i)=>{const sy=flexible.has(i)?(target-fixed)/flexLength:1;
    items.push({kind:'glyph',key:`${map.style}/${key}`,x:0,y:y-l*sy,sy,crop:[i===0?null:l,i===intervals.length-1?null:h]});y+=(h-l)*sy;});
   return{...b,items,height:-top,depth:bottom,class:'ord',character:false};
  }
  const sy=target/span;return{...b,items:[{...b.items[0],sy,y:-axis+axis*sy}],height:-top,depth:bottom,class:'ord',character:false};
 }
 function enclose(content,left,right,style,scalable=true){
  const axis=profile(style).parameters.AXISHEIGHT,delta=Math.max(content.height-axis,content.depth+axis);
  const required=scalable?Math.max(1.802*delta,2*delta-5*pt):0;
  const l=delimiter(left,style,required),r=delimiter(right,style,required),b={...empty(),class:'inner'};
  add(b.items,l,0,0);add(b.items,content,l.width,0);add(b.items,r,l.width+content.width,0);
  b.width=l.width+content.width+r.width;b.height=Math.max(l.height,content.height,r.height);b.depth=Math.max(l.depth,content.depth,r.depth);if(!scalable){b.class='open';b.endClass='close';b.character=true;}return b;
 }
 function matrix(node,style){
  const small=node.name==='smallmatrix',aligned=['aligned','align'].includes(node.name),childStyle=small?2:aligned?0:Math.max(1,style);
  const rows=node.rows.length?node.rows:[[[]]],cells=rows.map(row=>row.map((nodes,j)=>nodes.length?layout(aligned&&j%2?[{type:'group',children:[]},...nodes]:nodes,childStyle):hole(childStyle)));
  const columns=Math.max(1,...cells.map(row=>row.length));if(columns>32||rows.length>100)throw Error('Matrix limit: 32 columns and 100 rows');
  const widths=Array.from({length:columns},(_,j)=>Math.max(0,...cells.map(row=>row[j]?.width??0)));
  const cases=node.name==='cases',factor=cases?1.2:small?.6:1;
  const heights=cells.map(row=>Math.max((8.4*factor+(aligned?1.5:0))*pt,...row.map(b=>b.height))),depths=cells.map(row=>Math.max((3.6*factor+(aligned?1.5:0))*pt,...row.map(b=>b.depth)));
  const total=heights.reduce((a,h,i)=>a+h+depths[i],0),axis=profile(style).parameters.AXISHEIGHT;
  const box={...empty(),height:total/2+axis,depth:total/2-axis,class:'inner'};
  const gaps=Array.from({length:columns-1},(_,j)=>aligned?(j%2?20*pt:0):cases?10*pt:small?3*pt:10*pt);
  box.width=widths.reduce((a,w)=>a+w,0)+gaps.reduce((a,g)=>a+g,0);
  let y=-box.height;
  for(let i=0;i<cells.length;i++){y+=heights[i];let x=0;
   for(let j=0;j<columns;j++){const c=cells[i][j]??hole(childStyle),mode=cases?'l':aligned?(j%2?'l':'r'):(node.align[j]??'c');
    const shift=mode==='l'?0:mode==='r'?widths[j]-c.width:(widths[j]-c.width)/2;
    add(box.items,c,x+shift,y);x+=widths[j]+(gaps[j]??0);
   }y+=depths[i];
  }
  const pair=matrixDelimiters[node.name];return pair?enclose(box,pair[0],pair[1],style):box;
 }
 function atom(node,style,cramped=false){const map=profile(style),p=map.parameters;let b;
  if(node.type==='hole')b=hole(style);
  else if(node.type==='glyph')b=glyph(node.token,style);
  else if(node.type==='space')return{...empty(),width:node.mu*map.em/18,space:true};
  else if(node.type==='group')b=layout(node.children,style,cramped);
  else if(node.type==='delimited')b=enclose(layout(node.children,style,cramped),node.left,node.right,style,node.scalable);
  else if(node.type==='matrix')b=matrix(node,style);
  else if(node.type==='text'){
   b=empty();b.class=node.class;
   for(const char of node.text){if(char===' '){b.width+=map.em/3;continue;}const g=glyph(map.symbols['@roman:'+char]?'@roman:'+char:char,style);add(b.items,g,b.width,0);b.width+=g.width;b.height=Math.max(b.height,g.height);b.depth=Math.max(b.depth,g.depth);}
  }else{
   const fractionStyle=node.style??style,q=profile(fractionStyle).parameters,childStyle=fractionStyle===0?1:Math.min(3,fractionStyle+1),n=layout(node.num,childStyle,cramped),d=layout(node.den,childStyle,true);
   const rule=q.RULE,axis=q.AXISHEIGHT,clear=fractionStyle===0?3*rule:rule;
   const up=Math.max(fractionStyle===0?q.NUM1:q.NUM2,n.depth+axis+rule/2+clear),down=Math.max(fractionStyle===0?q.DENOM1:q.DENOM2,d.height-axis+rule/2+clear);
   const pad=1.2*pt,width=Math.max(n.width,d.width)+2*pad;
   b={...empty(),width,height:n.height+up,depth:d.depth+down};add(b.items,n,(width-n.width)/2,-up);add(b.items,d,(width-d.width)/2,down);
   b.items.push({kind:'rule',x:pad,y:-axis-rule/2,width:width-2*pad,height:rule});
  }
  if(node.sup||node.sub){
   const scriptStyle=style<2?2:3,q=profile(scriptStyle).parameters,sup=node.sup?layout(node.sup,scriptStyle,cramped):null,sub=node.sub?layout(node.sub,scriptStyle,true):null;
   const useLimits=node.limits??(style===0&&limitOperators.has(node.token));
   if(b.class==='op'&&useLimits){
    const width=Math.max(b.width,sup?.width??0,sub?.width??0),items=[];add(items,b,(width-b.width)/2,0);
    if(sup){const up=b.height+Math.max(p.BIGOPSPACING1,p.BIGOPSPACING3-sup.depth)+sup.depth;add(items,sup,(width-sup.width+b.italic)/2,-up);b.height=up+sup.height+p.BIGOPSPACING5;}
    if(sub){const down=b.depth+Math.max(p.BIGOPSPACING2,p.BIGOPSPACING4-sub.height)+sub.height;add(items,sub,(width-sub.width-b.italic)/2,down);b.depth=down+sub.depth+p.BIGOPSPACING5;}
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
  }return b;
 }
 const out=source.trim()?layout(draft.nodes,mode==='inline'?1:0):empty();
 return{...out,source,mode,atoms:draft.atoms,diagnostics:draft.diagnostics,complete:draft.diagnostics.length===0};
}
