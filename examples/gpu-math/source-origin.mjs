// Compose producer spans; never infer identity by searching rendered text.
export function projectOrigin(project,start,end){
 if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<=start||end>project.source.length)return null;
 const parts=project.sourceSpans.filter(s=>s.outputEnd>start&&s.outputStart<end);
 let cursor=start,first=null,lastEnd=null;
 for(const s of parts){
  if(s.kind!=='literal'||s.outputStart>cursor)return null;
  const a=Math.max(start,s.outputStart),b=Math.min(end,s.outputEnd),originStart=s.start+a-s.outputStart,originEnd=s.start+b-s.outputStart;
  if(first&&(s.fileId!==first.fileId||s.occurrenceId!==first.occurrenceId||originStart!==lastEnd))return null;
  first??={fileId:s.fileId,occurrenceId:s.occurrenceId,start:originStart};lastEnd=originEnd;cursor=b;
 }
 if(!first||cursor!==end)return null;
 const text=project.sourceFiles.find(f=>f.fileId===first.fileId)?.text;
 if(typeof text!=='string')return null;
 const boundary=n=>!(n>0&&n<text.length&&/[\uD800-\uDBFF]/.test(text[n-1])&&/[\uDC00-\uDFFF]/.test(text[n]));
 if(!boundary(first.start)||!boundary(lastEnd))return null;
 const bytes=s=>new TextEncoder().encode(s).length;
 return {...first,end:lastEnd,byteStart:bytes(text.slice(0,first.start)),byteEnd:bytes(text.slice(0,lastEnd))};
}
export function composeMacroOrigins(project,expanded){
 return expanded.sourceSpans.map(s=>({...s,origin:projectOrigin(project,s.start,s.end)}));
}
