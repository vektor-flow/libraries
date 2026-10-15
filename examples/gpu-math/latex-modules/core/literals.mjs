// URL arguments are verbatim-like: percent, hash and backslash are literal.
export function readUrl(source,start){
 const command=/^\\(?:url|nolinkurl)\b\s*/.exec(source.slice(start));if(!command)return null;
 const at=start+command[0].length,open=source[at];if(!open)return{value:'',end:at,closed:false};
 if(open!=='{'){const end=source.indexOf(open,at+1);return{value:source.slice(at+1,end<0?source.length:end),end:end<0?source.length:end+1,closed:end>=0};}
 let depth=1,end=at+1;for(;end<source.length;end++){if(source[end]==='{')depth++;if(source[end]==='}'&&!--depth)break;}
 return{value:source.slice(at+1,end),end:Math.min(source.length,end+1),closed:depth===0};
}
