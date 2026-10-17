export function fixture(operations=10,parts=10,document=true){
 const text='x',spans=[{sourceId:'s',start:0,end:1}];
 const o={documentId:'lookup',revision:0,resources:[],sources:[{id:'s',version:0,text}],groups:[{id:'g',contentVersion:0,layoutVersion:0,contentKey:'c',layoutKey:'l',edges:[],spans}],scopes:[{id:'scope',sourceId:'s',text,baseByte:0,operations:Array.from({length:operations},(_,i)=>({operation:i*3,start:0,stop:1,groupId:'g',leaves:Array.from({length:parts},(_,j)=>({part:j*7,id:`leaf${i}-${j}`,resources:[]}))}))}]};
 const a={count:operations*parts,kinds:[],a260_scopes:[],a260_texts:[],a260_operations:[],a260_starts:[],a260_stops:[],a260_parts:[]};
 for(const op of o.scopes[0].operations)for(const leaf of op.leaves){a.kinds.push(2);a.a260_scopes.push('scope');a.a260_texts.push(text);a.a260_operations.push(op.operation);a.a260_starts.push(0);a.a260_stops.push(1);a.a260_parts.push(leaf.part);}
 const r={complete:true,diagnostics:'',unresolved_json:'[]',...(document?{document:{arena:a,page_count:1,firsts:[0],counts:[a.count],widths:[100],heights:[100]}}:{scene:{arena:a,width:100,height:100}})};
 return {o,r,a,document};
}
export const bind=(m,f,previous=null,session=m.beginProvenance(f.o))=>m[f.document?'bindOperationDocument':'bindOperationFragment'](f.r,session,previous);
