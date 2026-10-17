// URL arguments are verbatim-like: percent, hash and backslash are literal.
// Preserve offsets so preparsers can ignore examples and comments without
// replacing their contents or interpreting a quoted command as an input file.
export function maskTexLiterals(source){
 const parts=[];let copied=0;
 function mask(start,end){parts.push(source.slice(copied,start),source.slice(start,end).replace(/[^\n]/g,' '));copied=end;}
 for(let at=0;at<source.length;){
  if(source[at]==='%'){const end=source.indexOf('\n',at);mask(at,end<0?source.length:end);at=end<0?source.length:end;continue;}
  if(source[at]!=='\\'){at++;continue;}
  const command=/^\\([A-Za-z]+|.)/.exec(source.slice(at));if(!command){at++;continue;}
  const end=at+command[0].length,name=command[1];
  if(name==='\\'){mask(at,end);at=end;continue;}
  if(name==='verb'){
   const start=end+(source[end]==='*'?1:0),delimiter=source[start],close=delimiter?source.indexOf(delimiter,start+1):-1,next=close<0?source.length:close+1;
   mask(at,next);at=next;continue;
  }
  const environment=name==='begin'&&/^\{verbatim\*?\}/.exec(source.slice(end));
  if(environment){const close=source.indexOf('\\end'+environment[0],end+environment[0].length),next=close<0?source.length:close+4+environment[0].length;mask(at,next);at=next;continue;}
  const literal=name==='url'||name==='nolinkurl'?readUrl(source,at):name==='href'?readHrefTarget(source,at):null;
  if(literal){mask(at,literal.end);at=literal.end;continue;}
  at=end;
 }
 return copied?parts.join('')+source.slice(copied):source;
}
export function readHrefTarget(source,start){
 if(source[start]!=='\\'||source[start+1]!=='h')return null;
 const command=/^\\href\s*/.exec(source.slice(start));if(!command)return null;
 const at=start+command[0].length;if(source[at]!=='{')return null;
 let depth=1,end=at+1;for(;end<source.length;end++){if(source[end]==='\\'&&/[{}]/.test(source[end+1]??'')){end++;continue;}if(source[end]==='{')depth++;if(source[end]==='}'&&!--depth)break;}
 return{value:source.slice(at+1,end),end:Math.min(source.length,end+1),closed:depth===0};
}
export function readUrl(source,start){
 if(source[start]!=='\\'||(source[start+1]!=='u'&&source[start+1]!=='n'))return null;
 const command=/^\\(?:url|nolinkurl)\b\s*/.exec(source.slice(start));if(!command)return null;
 const at=start+command[0].length,open=source[at];if(!open)return{value:'',end:at,closed:false};
 if(open!=='{'){const end=source.indexOf(open,at+1);return{value:source.slice(at+1,end<0?source.length:end),end:end<0?source.length:end+1,closed:end>=0};}
 let depth=1,end=at+1;for(;end<source.length;end++){if(source[end]==='{')depth++;if(source[end]==='}'&&!--depth)break;}
 return{value:source.slice(at+1,end),end:Math.min(source.length,end+1),closed:depth===0};
}
