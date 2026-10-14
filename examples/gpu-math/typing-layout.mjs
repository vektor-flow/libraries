/** Bounded independent display-math layout over measured optical-size mappings. */
export function typeset(source,maps) {
 if(source.length>12000)throw Error('Expression limit: 12,000 characters');
 let offset=0,count=0;const skip=()=>{while(/\s/.test(source[offset]??'')&&offset<source.length)offset++;};
 function list(depth=0,group=false){
  if(depth>16)throw Error('Nesting limit: 16');const nodes=[];
  while(offset<source.length){skip();if(offset===source.length)break;
   if(source[offset]==='}') {if(!group)throw Error('Unexpected }');offset++;return nodes;}
   let node;
   if(source[offset]==='{'){offset++;node={type:'group',children:list(depth+1,true)};}
   else if(source.startsWith('\\frac',offset)&&!/[A-Za-z]/.test(source[offset+5]??'')){
    offset+=5;const a=argument(depth),b=argument(depth);node={type:'frac',num:a,den:b};
   }else{const token=/^(?:\\[A-Za-z]+|[A-Za-z0-9+\-=<>()[\],])/.exec(source.slice(offset))?.[0];
    if(!token||!maps.display.symbols[token])throw Error(`Finish or correct the symbol at character ${offset+1}`);
    offset+=token.length;node={type:'glyph',token};}
   if(++count>3000)throw Error('Atom limit: 3,000');
   skip();while(source[offset]==='^'||source[offset]==='_'){
    const which=source[offset++]==='^'?'sup':'sub';if(node[which])throw Error('Repeated script');
    node[which]=argument(depth);skip();}
   nodes.push(node);
  }
  if(group)throw Error('Finish the closing brace');return nodes;
 }
 function argument(depth){skip();if(source[offset]!=='{'){
   const token=/^(?:\\[A-Za-z]+|[A-Za-z0-9])/.exec(source.slice(offset))?.[0];
   if(!token||!maps.display.symbols[token])throw Error('Finish the argument, using {…} for several symbols');
   offset+=token.length;return [{type:'glyph',token}];}
  offset++;return list(depth+1,true);
 }
 const ast=list();
 const profile=style=>maps[style<2?'display':style===2?'script':'scriptscript'];
 const add=(target,box,x,y)=>{for(const p of box.items)target.push({...p,x:p.x+x,y:p.y+y});};
 const table={ord:{ord:0,bin:4,rel:5,open:0,close:0,punct:0,inner:3},bin:{ord:4,open:4,inner:4},
 rel:{ord:5,open:5,inner:5,rel:0},open:{ord:0,open:0,close:0,inner:0},
 close:{ord:0,bin:4,rel:5,open:0,close:0,punct:0,inner:3},punct:{ord:3,open:3,close:3,punct:3,inner:3},
 inner:{ord:3,bin:4,rel:5,open:3,close:0,punct:3,inner:3}};
 function layout(nodes,style){
  const boxes=nodes.map(n=>atom(n,style));
  for(let i=0;i<boxes.length;i++){
   if(boxes[i].class==='bin'&&(i===0||['bin','rel','open','punct'].includes(boxes[i-1].class)))boxes[i].class='ord';
   if(['rel','close','punct'].includes(boxes[i].class)&&i&&boxes[i-1].class==='bin')boxes[i-1].class='ord';
  }
  if(boxes.at(-1)?.class==='bin')boxes.at(-1).class='ord';
  const out={items:[],width:0,height:0,depth:0,class:'ord',italic:0};
  for(let i=0;i<boxes.length;i++){
   if(i&&style<2){const mu=table[boxes[i-1].class]?.[boxes[i].class];if(mu===undefined)throw Error('Unsupported symbol adjacency');out.width+=mu*profile(style).em/18;}
   const b=boxes[i],before=out.items.length;add(out.items,b,out.width,0);for(let j=before;j<out.items.length;j++){out.items[j].flowX=out.width;out.items[j].flowWidth=b.width;}out.width+=b.width;out.height=Math.max(out.height,b.height);out.depth=Math.max(out.depth,b.depth);
  }return out;
 }
 function atom(node,style){
  const map=profile(style),p=map.parameters;let b;
  if(node.type==='glyph'){
   const s=map.symbols[node.token];b={items:[{kind:'glyph',key:`${map.style}/${node.token}`,x:0,y:0}],width:s.width,height:s.height,depth:s.depth,class:s.class,italic:s.italic??0,character:true};
  }else if(node.type==='group') b=layout(node.children,style);
  else{
   const childStyle=style===0?1:Math.min(3,style+1),n=layout(node.num,childStyle),d=layout(node.den,childStyle);
   const rule=p.RULE,axis=p.AXISHEIGHT,clear=style===0?3*rule:rule;
   const up=Math.max(style===0?p.NUM1:p.NUM2,n.depth+axis+rule/2+clear);
   const down=Math.max(style===0?p.DENOM1:p.DENOM2,d.height-axis+rule/2+clear);
   const pad=1.2*72/72.27,width=Math.max(n.width,d.width)+2*pad;
   b={items:[],width,height:n.height+up,depth:d.depth+down,class:'ord',italic:0};
   add(b.items,n,(width-n.width)/2,-up);add(b.items,d,(width-d.width)/2,down);
   b.items.push({kind:'rule',x:pad,y:-axis-rule/2,width:width-2*pad,height:rule});
  }
  if(node.sup||node.sub){
   const scriptStyle=style<2?2:3,q=profile(scriptStyle).parameters;
   const sup=node.sup?layout(node.sup,scriptStyle):null,sub=node.sub?layout(node.sub,scriptStyle):null;
   let up=b.character?0:b.height-q.SUPDROP,down=b.character?0:b.depth+q.SUBDROP;
   if(sup)up=Math.max(up,style===0?p.SUP1:p.SUP2,sup.depth+p.XHEIGHT/4);
   if(sub)down=Math.max(down,sup?p.SUB2:p.SUB1,sub.height-.8*p.XHEIGHT);
   if(sup&&sub){down=Math.max(down,4*p.RULE-up+sup.depth+sub.height);const shift=.8*p.XHEIGHT-up+sup.depth;if(shift>0){up+=shift;down-=shift;}}
   const width=b.width,space=.5*72/72.27;
   if(sup){add(b.items,sup,width,-up);b.width=Math.max(b.width,width+sup.width+space);b.height=Math.max(b.height,up+sup.height);}
   if(sub){add(b.items,sub,width-b.italic,down);b.width=Math.max(b.width,width-b.italic+sub.width+space);b.depth=Math.max(b.depth,down+sub.depth);}
  }return b;
 }
 const lines=source.trim()? [layout(ast,0)]:[];
 const out=lines[0]??{items:[],width:0,height:0,depth:0};
 return {...out,source,atoms:count};
}
