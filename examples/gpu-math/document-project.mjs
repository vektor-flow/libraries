import {readUrl,readHrefTarget} from './latex-modules/core/literals.mjs';
// Project inputs are data, never host paths or executable package modules.
export function projectPath(name,from=''){
 if(typeof name!=='string'||/[\\\0]|^[a-z]+:|^\//i.test(name))throw Error('Invalid project path: '+name);
 const parts=from.split('/').slice(0,-1);
 for(const part of name.split('/')){if(!part||part==='.')continue;if(part==='..'){if(!parts.length)throw Error('Project path escapes root: '+name);parts.pop();}else parts.push(part);}
 return parts.join('/');
}
export function resolveDocumentProject(source,{files={},jobName='document',entry=''}={}){
 const biblatex=[...source.matchAll(/\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}/g)].some(m=>m[1].split(',').map(s=>s.trim()).includes('biblatex'));
 const diagnostics=[],inputs=[],active=new Set(),sourceFiles=new Map();let total=source.length,occurrence=0;
 const text=name=>typeof files[name]==='string'?files[name]:files[name]?.text;
 function read(name,from,extension){let path;try{path=projectPath(name,from);}catch(error){diagnostics.push(error.message);return null;}if(text(path)===undefined&&extension&&!/\.[^/]+$/.test(path))path+=extension;const value=text(path);if(typeof value!=='string'){diagnostics.push('Missing project input: '+path);return null;}if(active.has(path)){diagnostics.push('Cyclic project input: '+path);return null;}if(active.size>=32)throw Error('Project input nesting limit: 32');total+=value.length;if(total>1000000)throw Error('Document project limit: 1000000 characters');inputs.push(path);active.add(path);const out=expand(value,path);active.delete(path);return out;}
 function expand(input,from){
 const fileId=projectPath(from||'document.tex'),occurrenceId=++occurrence;
 if(sourceFiles.has(fileId)&&sourceFiles.get(fileId)!==input)throw Error('Conflicting project source identity: '+fileId);
 sourceFiles.set(fileId,input);
 let out='',at=0;const sourceSpans=[];
 const append=(start,end)=>{if(end<=start)return;const previous=sourceSpans.at(-1),outputStart=out.length;out+=input.slice(start,end);
  if(previous?.kind==='literal'&&previous.fileId===fileId&&previous.occurrenceId===occurrenceId&&previous.end===start&&previous.outputEnd===outputStart){previous.end=end;previous.outputEnd=out.length;}
  else sourceSpans.push({outputStart,outputEnd:out.length,fileId,occurrenceId,start,end,kind:'literal'});
 };
 const generated=text=>{const outputStart=out.length;out+=text;sourceSpans.push({outputStart,outputEnd:out.length,kind:'generated'});};
 while(at<input.length){
  const literalTarget=readUrl(input,at)??readHrefTarget(input,at);if(literalTarget){append(at,literalTarget.end);at=literalTarget.end;continue;}
  if(input[at]==='%'){const end=input.indexOf('\n',at);if(end<0){append(at,input.length);break;}append(at,end+1);at=end+1;continue;}
  if(input[at]!=='\\'){append(at,at+1);at++;continue;}
  const token=/^\\([A-Za-z]+\*?|.)/.exec(input.slice(at));if(!token){append(at,at+1);at++;continue;}
  const command=token[1],end=at+token[0].length;
  // Literal environments and commands must not resolve apparent inputs inside code.
  const literal=/^\\begin\{(verbatim\*?|lstlisting|comment)\}/.exec(input.slice(at));
  if(literal){const close='\\end{'+literal[1]+'}',stop=input.indexOf(close,at+literal[0].length),next=stop<0?input.length:stop+close.length;append(at,next);at=next;continue;}
  if(command==='verb'||command==='verb*'){const delimiter=input[end],stop=input.indexOf(delimiter,end+1),next=stop<0?input.length:stop+1;append(at,next);at=next;continue;}
  if(!['input','include','bibliography','bibliographystyle'].includes(command)){append(at,end);at=end;continue;}
  let start=end;while(/\s/.test(input[start]??'')&&start<input.length)start++;
  const argument=input[start]==='{'?/^\{([^{}]*)\}/.exec(input.slice(start)):/^(\S+)/.exec(input.slice(start));
  if(!argument){append(at,end);at=end;continue;}
  const name=argument[1],next=start+argument[0].length;
  if(command==='bibliographystyle'){at=next;continue;}
  if(command==='bibliography'&&biblatex){append(at,next);at=next;continue;}
  // LaTeX reads <jobname>.bbl here; bibliography's argument names BibTeX databases.
  const value=command==='bibliography'?read(jobName+'.bbl','',null):read(name,from,'.tex');
  if(value===null)append(at,next);else{generated('\n');const offset=out.length;out+=value.source;sourceSpans.push(...value.sourceSpans.map(span=>({...span,outputStart:span.outputStart+offset,outputEnd:span.outputEnd+offset})));generated('\n');}at=next;
 }return {source:out,sourceSpans};}
 if(entry)active.add(projectPath(entry));
 const resolved=expand(source,entry);return{...resolved,sourceFiles:[...sourceFiles].map(([fileId,text])=>({fileId,text})),diagnostics,inputs:[...new Set(inputs)]};
}

// pdfTeX uses PNG pHYs resolution, or \pdfimageresolution (72 dpi by default).
// Keep intrinsic physical size separate from decoded texture pixel dimensions.
export function pngPhysicalSize(bytes,width,height,{defaultDpi=72}={}){
 let dpiX=defaultDpi,dpiY=defaultDpi;
 const signature=[137,80,78,71,13,10,26,10];
 if(bytes.length>=8&&signature.every((n,i)=>bytes[i]===n)){
  const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
  for(let at=8;at+12<=bytes.length;){const size=view.getUint32(at);if(size>bytes.length-at-12)throw Error('Truncated PNG chunk');const type=String.fromCharCode(...bytes.subarray(at+4,at+8));
   if(type==='pHYs'&&size===9&&bytes[at+16]===1){const x=view.getUint32(at+8),y=view.getUint32(at+12);if(x&&y){dpiX=Math.round(x*.0254);dpiY=Math.round(y*.0254);}}
   if(type==='IEND')break;at+=size+12;
  }
 }
 if(![width,height,dpiX,dpiY].every(n=>Number.isFinite(n)&&n>0))throw Error('Invalid intrinsic image dimensions');
 return{widthBp:width*72/dpiX,heightBp:height*72/dpiY,dpiX,dpiY};
}
