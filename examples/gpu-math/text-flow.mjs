import {typeset} from './typing-layout.mjs';
/** Browser-independent word flow. Prose and math share the mapped CM font family. */
export function typesetText(source,maps,{width=300}={}){
 if(source.length>12000)throw Error('Expression limit: 12,000 characters');
 width=Math.max(1,width);const map=maps.text??maps.display,pt=72/72.27,tokens=[],diagnostics=[];let at=0,atoms=0;
 const empty=()=>({items:[],width:0,height:0,depth:0});
 function word(text){const b=empty();let prior=null;
  for(let i=0;i<text.length;){let chars=text[i++],key='@text:'+chars;
   if(chars==='f'){for(const tail of ['fl','fi','f','l','i']){const candidate='f'+tail;if(text.slice(i-1,i-1+candidate.length)===candidate&&map.symbols['@text:'+candidate]){chars=candidate;i+=candidate.length-1;key='@text:'+candidate;break;}}}
   if(!map.symbols[key])key='@roman:'+chars;const s=map.symbols[key];
   if(!s){b.items.push({kind:'placeholder',x:b.width,y:-map.em*.32,width:map.em*.32,height:map.em*.32});b.width+=map.em*.32;b.height=Math.max(b.height,map.em*.32);diagnostics.push('Unsupported text character: '+chars);continue;}
   if(prior&&prior.fontName===s.fontName)b.width+=prior.kerns?.[String(s.fontCode)]??0;
   b.items.push({kind:'glyph',key:`${map.style}/${key}`,x:b.width,y:0});b.width+=s.advance??s.width;b.height=Math.max(b.height,s.height);b.depth=Math.max(b.depth,s.depth);prior=s;atoms++;
  }let sf=1000;for(const c of text){const n=/[A-Z]/.test(c)?999:/[.!?]/.test(c)?3000:c===':'?2000:/[\"'’”\)\]]/.test(c)?0:1000;if(n)sf=n>1000&&sf<1000?1000:n;}b.spaceFactor=sf;return b;
 }
 function math(delimiter,closing,display){at+=delimiter.length;const start=at,end=source.indexOf(closing,at),body=end<0?source.slice(at):source.slice(at,end);at=end<0?source.length:end+closing.length;
  if(end<0)diagnostics.push('Inferred a closing '+closing);const box=typeset(body,maps,{mode:display?'display':'inline'});diagnostics.push(...box.diagnostics);atoms+=box.atoms;tokens.push({type:display?'display':'word',box});
 }
 while(at<source.length){
  if(source.startsWith('$$',at)){math('$$','$$',true);continue;}
  if(source[at]==='$'){math('$','$',false);continue;}
  if(source.startsWith('\\[',at)){math('\\[','\\]',true);continue;}
  if(source.startsWith('\\(',at)){math('\\(','\\)',false);continue;}
  if(source.startsWith('\\\\',at)){at+=2;tokens.push({type:'break'});continue;}
  if(source[at]==='\\'&&source[at+1]==='$'){tokens.push({type:'word',box:word('$')});at+=2;continue;}
  if(/\s/.test(source[at])){const run=/^\s+/.exec(source.slice(at))[0];at+=run.length;tokens.push({type:/\n\s*\n/.test(run)?'paragraph':'space'});continue;}
  const start=at;while(at<source.length&&!/\s/.test(source[at])&&source[at]!=='$'&&!source.startsWith('\\\\',at)&&!source.startsWith('\\(',at)&&!source.startsWith('\\[',at))at++;
  if(start===at)at++;tokens.push({type:'word',box:word(source.slice(start,at))});
 }
 const lines=[];let line={parts:[],width:0,height:8.4*pt,depth:3.6*pt},space=false;
 const flush=(gap=0)=>{lines.push({...line,gap});line={parts:[],width:0,height:8.4*pt,depth:3.6*pt};space=false;};
 function append(box,center=false){line.parts.push({box,x:center?(width-box.width)/2:line.width});line.width+=box.width;line.height=Math.max(line.height,box.height);line.depth=Math.max(line.depth,box.depth);}
 for(const token of tokens){
  if(token.type==='space'){space=!!line.parts.length;continue;}
  if(token.type==='break'||token.type==='paragraph'){flush(token.type==='paragraph'?6*pt:0);continue;}
  if(token.type==='display'){if(line.parts.length)flush(3*pt);append(token.box,true);flush(3*pt);continue;}
  const box=token.box,gap=space&&line.parts.length?(map.textSpace??map.em/3)+((line.parts.at(-1)?.box.spaceFactor??1000)>=2000?(map.textExtraSpace??map.em/9):0):0;
  if(line.parts.length&&line.width+gap+box.width>width)flush();else line.width+=gap;
  // Long literal words can break between glyphs; math stays a single expression.
  if(box.width>width&&box.items.every(i=>i.kind==='glyph')&&box.items.every(i=>i.key.startsWith('text/@'))){
   for(const item of box.items){const s=map.symbols[item.key.slice(5)],piece={items:[{...item,x:0}],width:s.advance??s.width,height:s.height,depth:s.depth};if(line.parts.length&&line.width+piece.width>width)flush();append(piece);}
  }else append(box);space=false;
 }
 if(line.parts.length||!lines.length)flush();
 const out={...empty(),document:true,source,mode:'text',atoms,diagnostics:[...new Set(diagnostics)].slice(0,24),lines:[]};let baseline=0;
 for(let i=0;i<lines.length;i++){const l=lines[i];if(i)baseline+=lines[i-1].depth+l.height+3*pt+(lines[i-1].gap??0);
  for(const {box,x}of l.parts)for(const item of box.items)out.items.push({...item,x:item.x+x,y:item.y+baseline,flowX:x,flowWidth:box.width,flowLine:i});out.lines.push({height:l.height,depth:l.depth,baseline});out.width=Math.max(out.width,l.width);}
 out.height=lines[0].height;out.depth=baseline+lines.at(-1).depth;out.complete=!out.diagnostics.length;return out;
}
