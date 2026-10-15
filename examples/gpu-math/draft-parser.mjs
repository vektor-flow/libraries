import {parseMathCommand as parseAmsmath,mathCommands as amsCommands} from './latex-modules/packages/amsmath.mjs';
import {parseColor} from './colors.mjs';
import {unitOptions,numberNodes,unitNodes} from './units.mjs';
/** Recovery is preview-only: never rewrite the user's source or reuse old values. */
const greekLower='alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega'.split(' ');
const greekUpper='Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda Mu Nu Xi Omicron Pi Rho Sigma Tau Upsilon Phi Chi Psi Omega'.split(' ');
const unicode={};for(let i=0;i<24;i++){unicode['αβγδεζηθικλμνξοπρστυφχψω'[i]]='\\'+greekLower[i];unicode['ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ'[i]]='\\'+greekUpper[i];}
Object.assign(unicode,{'ς':'\\varsigma','ϕ':'\\phi','ϑ':'\\vartheta','ϖ':'\\varpi','ϱ':'\\varrho','ϵ':'\\epsilon','∑':'\\sum','∏':'\\prod','∫':'\\int','∬':'\\iint','∭':'\\iiint','∮':'\\oint','∯':'\\oiint','∞':'\\infty','≤':'\\leq','≥':'\\geq','≠':'\\neq','×':'\\times','·':'\\cdot','→':'\\to','⟨':'\\langle','⟩':'\\rangle'});
const aliases={'\\{':'\\lbrace','\\}':'\\rbrace','\\lparen':'(','\\rparen':')','\\lbrack':'[','\\rbrack':']','\\vert':'|','\\lvert':'|','\\rvert':'|','\\|':'\\Vert','\\lVert':'\\Vert','\\rVert':'\\Vert','\\le':'\\leq','\\ge':'\\geq','\\ne':'\\neq','\\land':'\\wedge','\\lor':'\\vee'};
const environments=new Set(['matrix','pmatrix','bmatrix','Bmatrix','vmatrix','Vmatrix','smallmatrix','cases','aligned','align','align*','array','gathered','split','multline','multline*','gather','gather*','equation','equation*']);
const spaces={'\\,':3,'\\:':4,'\\;':5,'\\!':-3,'\\quad':18,'\\qquad':36,'\\ ':6,'~':6};
export function parseDraft(source,mapping,{packages=null,extensions=[]}={}){
 if(source.length>12000)throw Error('Expression limit: 12,000 characters');
 let at=0,count=0;const diagnostics=[],repair=message=>{if(diagnostics.length<24&&!diagnostics.includes(message))diagnostics.push(message);};
 const skip=()=>{while(at<source.length&&/\s/.test(source[at]))at++;};
 const peek=()=>/^\\[a-zA-Z]+|^\\.|^./s.exec(source.slice(at))?.[0]??'';
 const take=()=>{const t=peek();at+=t.length;return aliases[t]??unicode[t]??t;};
 const hole=()=>({type:'hole'});
 function rawGroup(){skip();if(source[at]!=='{'){repair('Finish the braced argument');return '';}
  at++;let value='',depth=1;while(at<source.length&&depth){const c=source[at++];if(c==='\\'&&at<source.length){value+=c+source[at++];continue;}if(c==='{')depth++;if(c==='}')depth--;if(depth)value+=c;}
  if(depth)repair('Inferred a closing brace');return value;
 }
 function parseText(text,depth=0,font='mathrm'){
  if(depth>32)throw Error('Text nesting limit: 32');let i=0;const nodes=[];
  const escapes={'\\%':'%','\\$':'$','\\#':'#','\\&':'&','\\_':'_','\\{':'{','\\}':'}','\\textbackslash':'\\','\\textasciicircum':'^','\\textasciitilde':'~','\\ ':' '};
  while(i<text.length){
   if(text[i]==='{'||text[i]==='}') {i++;continue;}
   if(text[i]==='\\'){
    const command=/^\\[A-Za-z]+|^\\./.exec(text.slice(i))?.[0]??'\\';i+=command.length;
    if(command in escapes){nodes.push({type:'textchar',char:escapes[command],font});continue;}
    const family={'\\text':'mathrm','\\textrm':'mathrm','\\textnormal':'mathrm','\\textbf':'mathbf','\\textit':'mathit','\\emph':font==='mathit'?'mathrm':'mathit','\\textsf':'mathsf','\\texttt':'mathtt'}[command];
    if(family){while(/\s/.test(text[i]??'')&&i<text.length)i++;if(text[i]==='{'){let level=1,start=++i;while(i<text.length&&level){if(text[i]==='\\'){i+=Math.min(2,text.length-i);continue;}if(text[i]==='{')level++;if(text[i]==='}')level--;i++;}if(level)repair('Inferred a closing text brace');nodes.push(...parseText(text.slice(start,level?i:i-1),depth+1,family));}else repair('Missing text formatting argument');continue;}
    repair('Unsupported text command: '+command);nodes.push({type:'hole'});continue;
   }
   let char=text[i++];if(char==='~'||/\s/.test(char))char=' ';nodes.push({type:'textchar',char,font});
  }return nodes;
 }
 function optionalRaw(){skip();if(source[at]!=='[')return '';at++;let value='',braces=0;while(at<source.length){const c=source[at++];if(c==='{' )braces++;if(c==='}')braces--;if(c===']'&&!braces)return value;value+=c;}repair('Inferred a closing option bracket');return value;}
 function optionalArgument(depth){skip();if(source[at]!=='[')return null;at++;const nodes=list(depth+1,']');if(source[at]===']')at++;else repair('Inferred a closing label bracket');return nodes;}
 function delimiter(){skip();const token=take();if(!token){repair('Inferred an invisible delimiter');return '.';}return token;}
 function argument(depth){skip();if(at===source.length||['}','&'].includes(source[at])||['\\right','\\end','\\\\'].includes(peek())){repair('Empty operand placeholder');return[hole()];}
  if(source[at]==='{'){at++;return list(depth+1,'brace');}
  const node=base(depth+1);return[node??hole()];
 }
 function matrix(name,depth,shorthand=false){
  if(!environments.has(name)){const candidate=[...environments].find(e=>e.startsWith(name));if(candidate){name=candidate;repair('Completed a matrix environment for preview');}else{repair('Unknown environment '+name);name='matrix';}}
  let align='';if(name==='array'){align=rawGroup();if(/[^clr|\s]/.test(align))repair('Unsupported array column specification');}
  if(shorthand){skip();if(source[at]==='{')at++;else repair('Inferred the matrix body');}
  const rows=[[]],rowGaps=[],rules=[];while(at<source.length){skip();if(peek()==='\\end'){take();const end=rawGroup();if(end!==name)repair('Matched the unfinished environment');if(rows.length>1&&rows.at(-1).length===0)rows.pop();return{type:'matrix',name,rows,align,rowGaps,rules};}if(peek()==='\\hline'||peek()==='\\cline'){const command=take();rules.push({row:rows.length-1,columns:command==='\\cline'?rawGroup():null});continue;}rows.at(-1).push(list(depth+1,shorthand?'matrixBrace':'matrix'));
   const t=peek();if(source[at]==='&'){at++;continue;}
   if(t==='\\\\'){at+=2;rowGaps[rows.length-1]=optionalRaw();rows.push([]);continue;}
   if(t==='\\end'){at+=4;const end=rawGroup();if(end!==name)repair('Matched the unfinished environment');return{type:'matrix',name,rows,align,rowGaps,rules};}
   if(shorthand&&source[at]==='}'){at++;return{type:'matrix',name,rows,align,rowGaps,rules};}
   break;
  }
  repair('Inferred \\end{'+name+'}');return{type:'matrix',name,rows,align,rowGaps,rules};
 }
 function base(depth){
  if(depth>32)throw Error('Nesting limit: 32');skip();const raw=peek();if(!raw)return hole();
  if(source[at]==='{'){at++;return{type:'group',children:list(depth+1,'brace')};}
  for(const extension of extensions){if(extension.mathCommands?.includes(raw)&&extension.parseMathCommand){const result=extension.parseMathCommand(raw,{take,argument,rawGroup,optionalRaw,parseText,repair,depth,star:()=>{if(source[at]==='*'){at++;return true;}return false;}});if(result)return result;}}
  if(amsCommands.includes(raw)){if(packages&&!packages.includes('amsmath')){take();repair('Command requires amsmath: '+raw);return hole();}const extension=parseAmsmath(raw,{take,argument,rawGroup,optionalRaw,parseText,repair,depth,star:()=>{if(source[at]==='*'){at++;return true;}return false;}});if(extension)return extension;}
  if(raw==='\\\\'||raw==='\\newline'){take();return{type:'break',gap:optionalRaw()};}
  if(raw==='\\color'||raw==='\\textcolor'){take();const model=optionalRaw(),value=rawGroup(),color=parseColor(value,model);if(!color)repair('Unfinished or unsupported color: '+value);return raw==='\\color'?{type:'color',color}:{type:'paint',color,children:argument(depth)};}
  if(['\\mathrm','\\mathbf','\\mathit','\\mathsf','\\mathtt','\\mathfrak','\\mathcal','\\mathscr','\\mathbb','\\mathbbold','\\mathnormal','\\boldsymbol','\\bm'].includes(raw)){take();return{type:'font',name:raw==='\\bm'?'boldsymbol':raw.slice(1),children:argument(depth)};}
  if(raw==='\\sqrt'){take();return{type:'radical',index:optionalArgument(depth),children:argument(depth)};}
  if(['\\boxed','\\fbox','\\phantom','\\hphantom','\\vphantom','\\smash','\\mathstrut'].includes(raw)){take();const option=raw==='\\smash'?optionalRaw():'';if(option&&!['t','b'].includes(option))repair('Unsupported smash option');return{type:'box',name:raw.slice(1),option,children:raw==='\\mathstrut'?[{type:'glyph',token:'('}]:argument(depth)};}
  if(['\\hspace','\\kern','\\mkern','\\mskip'].includes(raw)){take();if(source[at]==='*')at++;let dimension;if(source[at]==='{')dimension=rawGroup();else{skip();const match=/^[+-]?(?:d+(?:.d*)?|.d+)s*(?:pt|bp|em|ex|mu|mm|cm|in|pc)/.exec(source.slice(at));dimension=match?.[0]??'';at+=dimension.length;}if(!dimension)repair('Empty spacing dimension');return{type:'dimension',dimension};}
  if(raw==='\\not'){take();return{type:'glyph',token:'@not',class:'rel'};}
  if(raw==='\\middle'){take();return{type:'middle',token:delimiter()};}
  if(raw==='\\label'){take();rawGroup();return{type:'space',mu:0};}
  if(raw==='\\frac'||raw==='\\dfrac'||raw==='\\tfrac'){take();return{type:'frac',num:argument(depth),den:argument(depth),style:raw==='\\dfrac'?0:raw==='\\tfrac'?1:null};}
  if(['\\hat','\\widehat','\\tilde','\\widetilde','\\bar','\\vec','\\dot','\\ddot','\\dddot','\\ddddot','\\acute','\\grave','\\breve','\\check','\\mathring','\\overline','\\underline','\\overbrace','\\underbrace','\\overrightarrow','\\overleftarrow','\\overleftrightarrow','\\underrightarrow','\\underleftarrow','\\underleftrightarrow'].includes(raw)){take();return{type:'decoration',name:raw.slice(1),children:argument(depth),...(['\\overbrace','\\underbrace'].includes(raw)?{limits:true}:{})};}
  if(raw==='\\overset'||raw==='\\underset'||raw==='\\stackrel'){take();const label=argument(depth),children=argument(depth);return{type:'stack',children,[raw==='\\underset'?'sub':'sup']:label,limits:true};}
  if(raw==='\\xrightarrow'||raw==='\\xleftarrow'){take();const below=optionalArgument(depth),above=argument(depth);return{type:'arrow',name:raw.slice(1),sup:above,sub:below,limits:true};}
  if(['\\qty','\\SI','\\unit','\\si','\\num','\\ang'].includes(raw)){take();const options=unitOptions(optionalRaw(),repair);let children=[];
   if(raw==='\\num'||raw==='\\qty'||raw==='\\SI')children=numberNodes(rawGroup(),options,repair);
   if(raw==='\\qty'||raw==='\\SI')children.push({type:'space',mu:3});
   if(raw==='\\qty'||raw==='\\SI'||raw==='\\unit'||raw==='\\si')children.push(...unitNodes(rawGroup(),options,repair));
   if(raw==='\\ang'){const parts=rawGroup().split(';');for(let i=0;i<parts.length;i++){if(!parts[i])continue;children.push(...numberNodes(parts[i],options,repair),{type:'glyph',token:i===0?'@unit:degree':i===1?'@unit:arcminute':'@unit:arcsecond'});}}
   return{type:'group',children};
  }
  if(raw==='\\left'){take();const left=delimiter(),children=list(depth+1,'right');let right='.';
   if(peek()==='\\right'){take();right=delimiter();}else repair('Inferred \\right.');return{type:'delimited',left,right,children,scalable:true};}
  if(raw==='\\begin'){take();return matrix(rawGroup(),depth);}
  if(environments.has(raw.slice(1))){take();return matrix(raw.slice(1),depth,true);}
  if(['\\text','\\textrm','\\textbf','\\textit','\\textsf','\\texttt','\\textnormal','\\emph'].includes(raw)){take();return{type:'textflow',children:parseText(rawGroup(),depth,{'\\textbf':'mathbf','\\textit':'mathit','\\emph':'mathit','\\textsf':'mathsf','\\texttt':'mathtt'}[raw]??'mathrm')};}
  if(['\\big','\\Big','\\bigg','\\Bigg','\\bigl','\\bigr','\\Bigl','\\Bigr','\\biggl','\\biggr','\\Biggl','\\Biggr'].includes(raw)){take();const size=raw.slice(1).replace(/[lr]$/,'');const token=delimiter();return{type:'glyph',token:'@'+size+':'+token};}
  if(raw==='('||raw==='['){take();const right=raw==='('?')':']',children=list(depth+1,right);let end='.';if(peek()===right){take();end=right;}else repair('Inferred an invisible closing scope');return{type:'delimited',left:raw,right:end,children,scalable:false};}
  const token=take();if(token in spaces)return{type:'space',mu:spaces[token]};
  if(token==='\\displaystyle'||token==='\\textstyle'||token==='\\scriptstyle'||token==='\\scriptscriptstyle')return{type:'style',style:{'\\displaystyle':0,'\\textstyle':1,'\\scriptstyle':2,'\\scriptscriptstyle':3}[token]};
  if(token==='^'||token==='_'){repair('Empty base placeholder');const n=hole();n[token==='^'?'sup':'sub']=argument(depth);return n;}
  if(mapping.symbols[token])return{type:'glyph',token};
  if(token==='\\right'){repair('Unmatched right delimiter');return{type:'glyph',token:delimiter()};}
  if(token==='\\end'){rawGroup();repair('Unmatched environment end');return hole();}
  if(token==='}') {repair('Ignored an unmatched closing brace');return null;}
  repair((token.startsWith('\\')?'Unfinished or unsupported command: ':'Unsupported symbol: ')+token);return hole();
 }
 function list(depth=0,stop=''){
  const nodes=[];const finish=()=>{const last=nodes.at(-1);if((nodes.length>1||stop===''||stop==='matrix'||stop==='matrixBrace')&&last?.type==='glyph'&&['bin','rel'].includes(mapping.symbols[last.token]?.class)){nodes.push(hole());repair('Empty operand placeholder');}return nodes;};while(at<source.length){skip();if(at===source.length)break;const token=peek();
   if(stop==='brace'&&token==='}'){at++;return nodes.length?finish():[hole()];}
   if((stop==='right'&&token==='\\right')||(token===stop)||((stop==='matrix'||stop==='matrixBrace')&&(token==='&'||token==='\\\\'||token==='\\end'||token==='\\right'||token==='\\hline'||token==='\\cline'||(stop==='matrixBrace'&&token==='}'))))return finish();
   // A script cannot steal the parent's brace or enclosing right/environment.
   if(stop==='brace'&&['\\right','\\end','&','\\\\'].includes(token)){repair('Inferred a closing brace');return nodes.length?finish():[hole()];}
   let node=base(depth);if(!node)continue;
   if(++count>3000)throw Error('Atom limit: 3,000');skip();
   while(['^','_','\\limits','\\nolimits'].includes(peek())){
    const t=take();if(t==='\\limits'||t==='\\nolimits'){node.limits=t==='\\limits';continue;}
    const name=t==='^'?'sup':'sub',arg=argument(depth);let target=node;
    if(target[name]){repair('Grouped repeated scripts for preview');while(target[name]?.[0]?.[name])target=target[name][0];target=target[name]?.[0]??target;}
    target[name]=arg;skip();
   }
   nodes.push(node);
  }
  if(stop==='brace'){repair('Inferred a closing brace');if(!nodes.length)nodes.push(hole());}
  return finish();
 }
 const nodes=list();return{nodes,diagnostics,atoms:count};
}
