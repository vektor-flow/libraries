// Independent BibTeX data parser and bounded biblatex bibliography formatting.
// Bibliography databases are input data; no Biber process or .bbl is consumed.
import {readGroup} from './latex-modules/core/macros.mjs';
import {projectPath} from './document-project.mjs';
import {maskTexLiterals} from './latex-modules/core/literals.mjs';
function splitNames(text,separator='and'){
 const parts=[];let start=0,depth=0;
 for(let i=0;i<text.length;i++){if(text[i]==='\\'){i++;continue;}if(text[i]==='{')depth++;else if(text[i]==='}')depth--;else if(!depth&&(separator===','?text[i]===',':text.slice(i,i+3)==='and'&&/\s/.test(text[i-1]??'')&&/\s/.test(text[i+3]??''))){parts.push(text.slice(start,i).trim());i+=separator===','?0:2;start=i+1;}}
 parts.push(text.slice(start).trim());return parts.filter(Boolean);
}
function plain(text){return text.replace(/\\["'`^~=.uvHc]\s*\{?([A-Za-z])\}?/g,'$1').replace(/\\[A-Za-z]+\s*/g,'').replace(/[{}]/g,'').replace(/~/g,' ').replace(/\s+/g,' ').trim();}
export function bibtexNames(text){return splitNames(text).map(name=>{
 if(name.startsWith('{')&&readGroup(name,0)?.end===name.length)return{family:plain(name),given:'',corporate:true};
 const parts=splitNames(name,',');if(parts.length>3)throw Error('Invalid BibTeX name: '+name);
 if(parts.length>=2)return{family:parts[0],given:parts.at(-1),suffix:parts.length===3?parts[1]:''};
 const words=name.match(/\{[^{}]*\}|\S+/g)??[];let family=words.length-1;
 for(let i=0;i<words.length-1;i++)if(/^[a-z]/.test(plain(words[i]))){family=i;break;}
 return{family:words.slice(family).join(' '),given:words.slice(0,family).join(' ')};
});}
export function parseBibtex(source,{strings=new Map()}={}){
 if(typeof source!=='string'||source.length>1000000)throw Error('Bibliography input limit: 1000000 characters');
 const entries=new Map(),diagnostics=[];let at=0;
 const macros=new Map(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'].map((m,i)=>[m,String(i+1)]));for(const pair of strings)macros.set(...pair);
 function skip(){for(;;){while(/\s|,/.test(source[at]??'')&&at<source.length)at++;if(source[at]!=='%')break;const end=source.indexOf('\n',at);at=end<0?source.length:end+1;}}
 function atom(){skip();if(source[at]==='{'){const g=readGroup(source,at);if(!g||!source.slice(at,g.end).endsWith('}'))throw Error('Unclosed bibliography field');at=g.end;return g.value;}
  if(source[at]==='"'){let text='',depth=0;at++;for(;at<source.length;at++){const c=source[at];if(c==='\\'){text+=c+(source[++at]??'');continue;}if(c==='{')depth++;if(c==='}')depth--;if(c==='"'&&!depth){at++;return text;}text+=c;}throw Error('Unclosed quoted bibliography field');}
  const m=/^[A-Za-z0-9_:.+\/-]+/.exec(source.slice(at));if(!m)throw Error('Invalid bibliography field');at+=m[0].length;if(/^\d+$/.test(m[0]))return m[0];const value=macros.get(m[0].toLowerCase());if(value===undefined){diagnostics.push('Undefined bibliography string: '+m[0]);return m[0];}return value;
 }
 function value(){let result=atom();for(;;){skip();if(source[at]!=='#')break;at++;result+=atom();}return result.replace(/\s+/g,' ').trim();}
 while(at<source.length){skip();if(at===source.length)break;if(source[at]!=='@'){const next=source.indexOf('@',at);at=next<0?source.length:next;continue;}at++;
  const type=/^[A-Za-z]+/.exec(source.slice(at));if(!type)throw Error('Invalid bibliography entry type');at+=type[0].length;skip();const open=source[at++],close=open==='{'?'}':open==='('?')':null;if(!close)throw Error('Invalid bibliography entry delimiter');const kind=type[0].toLowerCase();
  if(kind==='comment'){let depth=1;while(at<source.length&&depth){if(source[at]==='\\'){at+=2;continue;}if(source[at]===open)depth++;else if(source[at]===close)depth--;at++;}continue;}
  if(kind==='preamble'){value();skip();if(source[at++]!==close)throw Error('Invalid bibliography preamble');continue;}
  if(kind==='string'){skip();const name=/^[A-Za-z][A-Za-z0-9_:.-]*/.exec(source.slice(at));if(!name)throw Error('Invalid bibliography string name');at+=name[0].length;skip();if(source[at++]!=='=')throw Error('Invalid bibliography string definition');macros.set(name[0].toLowerCase(),value());skip();if(source[at++]!==close)throw Error('Invalid bibliography string ending');continue;}
  skip();const key=/^[^\s,{}()]+/.exec(source.slice(at));if(!key)throw Error('Missing bibliography key');at+=key[0].length;const fields={};skip();
  while(at<source.length&&source[at]!==close){const field=/^[A-Za-z][A-Za-z0-9_:-]*/.exec(source.slice(at));if(!field)throw Error('Invalid bibliography field name');at+=field[0].length;skip();if(source[at++]!=='=')throw Error('Missing bibliography field equals');fields[field[0].toLowerCase()]=value();skip();}
  if(source[at++]!==close)throw Error('Unclosed bibliography entry');if(entries.has(key[0]))throw Error('Duplicate bibliography key: '+key[0]);if(entries.size>=10000)throw Error('Bibliography entry limit');entries.set(key[0],{key:key[0],type:kind,fields});
 }
 function inherit(entry,chain=[]){if(chain.includes(entry.key))throw Error('Cyclic bibliography cross-reference');const parent=entry.fields.crossref;if(parent){const other=entries.get(parent);if(!other){diagnostics.push('Missing bibliography cross-reference: '+parent);return entry;}return{...entry,fields:{...inherit(other,[...chain,entry.key]).fields,...entry.fields}};}return entry;}
 return{entries:new Map([...entries].map(([key,e])=>[key,inherit(e)])),strings:macros,diagnostics};
}
const period=text=>/[.!?]$/.test(text)?text:text+'.';
function authorText(names){const values=names.map(n=>[n.given,n.family,n.suffix].filter(Boolean).join(' '));return values.length<3?values.join(' and '):values.slice(0,-1).join(', ')+', and '+values.at(-1);}
export function formatBiblatexEntry(entry){
 const f=entry.fields,names=bibtexNames(f.author??f.editor??''),sentences=[];
 if(names.length)sentences.push(period(authorText(names)));
 const title=f.title??'',year=f.year??f.date?.slice(0,4)??'',pages=f.pages?.replace(/(\d)\s*-\s*(\d)/g,'$1--$2');
 if(entry.type==='article'||entry.type==='incollection'||entry.type==='inproceedings'){
  if(title)sentences.push('``'+title+"''.");
  const venue=f.journaltitle??f.journal??f.booktitle;
  if(venue){let details='In: \\emph{'+venue+'}';if(entry.type==='article'){if(f.volume)details+=' '+f.volume;if(f.number)details+='.'+f.number;if(year)details+=' ('+year+')';if(pages)details+=', '+(/^\d/.test(pages)?'pp.~':'')+pages;sentences.push(period(details));}
   else{sentences.push(period(details));if(f.volume)sentences.push('Vol.~'+f.volume+'.');if(f.series)sentences.push(period(f.series));const publisher=[f.publisher,year].filter(Boolean).join(', ');if(publisher)sentences.push(publisher+(pages?', pp.~'+pages:'')+'.');}}
 }else if(entry.type==='book'||entry.type==='misc'||entry.type==='unpublished'||entry.type==='online'){
  if(title)sentences.push('\\emph{'+title+'}.');
  if(f.edition)sentences.push(period(f.edition));if(f.volume)sentences.push('Vol.~'+f.volume+'.');if(f.series)sentences.push(period(f.series));if(f.note)sentences.push(period(f.note));
  if(entry.type==='book'){const publication=[f.location??f.address,f.publisher,year].filter(Boolean).join(', ');if(publication)sentences.push(period(publication));}else if(year)sentences.push(period(year));
 }else throw Error('Unsupported bibliography entry type: '+entry.type);
 if(f.doi)sentences.push('\\textsc{doi}: \\url{https://doi.org/'+f.doi+'}.');else if(f.url)sentences.push('\\textsc{url}: \\url{'+f.url+'}.');
 return sentences.join(' ');
}
export function prepareBiblatex(source,{files={},entry='',options=[],measureLabel=null}={}){
 const diagnostics=[],entries=new Map(),strings=new Map(),inputs=[],requested={style:'numeric',sorting:'nty',backend:'biber'};
 for(const option of options){const [key,...rest]=option.split('=');requested[key]=rest.join('=');}
 if(!['numeric','alphabetic'].includes(requested.style))diagnostics.push('Unsupported biblatex style: '+requested.style);
 if(!['nyt','nty','anyt','none'].includes(requested.sorting))diagnostics.push('Unsupported biblatex sorting: '+requested.sorting);
 if(!['biber','bibtex'].includes(requested.backend))diagnostics.push('Unsupported biblatex backend: '+requested.backend);
 const declarations=/\\(bibliography|addbibresource)\s*(?:\[([^\]]*)\])?\s*\{([^{}]+)\}/g;
 let executable=maskTexLiterals(source);
 source=source.replace(declarations,(whole,command,resourceOptions,names,offset)=>{
  if(executable[offset]!=='\\')return whole;
  if(resourceOptions)diagnostics.push('Unsupported bibliography resource options: '+resourceOptions);
  for(let name of names.split(',').map(x=>x.trim())){if(!/\.[^/]+$/.test(name))name+='.bib';const path=projectPath(name,entry),raw=typeof files[path]==='string'?files[path]:files[path]?.text;if(typeof raw!=='string'){diagnostics.push('Missing bibliography input: '+path);continue;}const parsed=parseBibtex(raw,{strings});for(const pair of parsed.strings)strings.set(...pair);for(const [key,value]of parsed.entries){if(entries.has(key))throw Error('Duplicate bibliography key: '+key);entries.set(key,value);}diagnostics.push(...parsed.diagnostics);inputs.push(path);}
  return '';
 });
 executable=maskTexLiterals(source);
 const cited=[];for(const match of executable.matchAll(/\\(?:cite|nocite|parencite|textcite|autocite)\*?\s*(?:\[[^\]]*\]\s*){0,2}\{([^{}]+)\}/g))for(const key of match[1].split(',').map(x=>x.trim()))if(!cited.includes(key))cited.push(key);
 const chosen=cited.includes('*')?[...entries.keys()]:cited;let ordered=chosen.flatMap(key=>{if(!entries.has(key)){diagnostics.push('Undefined citation: '+key);return[];}return[entries.get(key)];});
 const collator=new Intl.Collator('en',{sensitivity:'base',ignorePunctuation:true});
 const nameKey=e=>bibtexNames(e.fields.sortname??e.fields.author??e.fields.editor??'').map(n=>plain(n.family)+' '+plain(n.given)).join(' ');
 if(requested.sorting!=='none')ordered.sort((a,b)=>{const names=collator.compare(nameKey(a),nameKey(b));if(names)return names;const year=collator.compare(a.fields.year??'',b.fields.year??''),title=collator.compare(plain(a.fields.sorttitle??a.fields.title??''),plain(b.fields.sorttitle??b.fields.title??''));return requested.sorting==='nty'?title||year:year||title;});
 const labels=new Map(),groups=new Map();for(const [i,e]of ordered.entries()){
  const names=bibtexNames(e.fields.author??e.fields.editor??''),family=names.map(n=>plain(n.family));let label;
  if(requested.style==='numeric')label=String(i+1);else if(e.fields.shorthand)label=e.fields.shorthand;else label=(e.fields.label??(family.length===1?family[0].slice(0,3):family.slice(0,3).map(n=>n.slice(0,1)).join('')+(family.length>3?'+':'')))+(e.fields.year??e.fields.date?.slice(0,4)??'').slice(-2);
  labels.set(e.key,label);const peers=groups.get(label)??[];peers.push(e.key);groups.set(label,peers);
 }
 if(requested.style==='alphabetic')for(const [label,peers]of groups)if(peers.length>1)for(const [i,key]of peers.entries()){if(i>=26)throw Error('Alphabetic citation disambiguation limit');labels.set(key,label+String.fromCharCode(97+i));}
 let bibliography='';for(const e of ordered){try{bibliography+='\\bibitem['+labels.get(e.key)+']{'+e.key+'}'+formatBiblatexEntry(e)+'\n';}catch(error){diagnostics.push(error.message);}}
 source=source.replace(/\\printbibliography\s*(?:\[([^\]]*)\])?/g,(whole,opts,offset)=>{if(executable[offset]!=='\\')return whole;if(opts)diagnostics.push('Unsupported printbibliography options: '+opts);const widest=[...labels.values()].sort((a,b)=>measureLabel?measureLabel(b)-measureLabel(a):b.length-a.length)[0]??'9';return'\\begin{thebibliography}{'+widest+'}\n'+bibliography+'\\end{thebibliography}';});
 executable=maskTexLiterals(source);
 source=source.replace(/\\nocite\s*\{[^{}]*\}/g,(whole,offset)=>executable[offset]==='\\'?'':whole);
 return{source,labels,entries:ordered,inputs,diagnostics,separator:'; ',style:requested.style};
}
