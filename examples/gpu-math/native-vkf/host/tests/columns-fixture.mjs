import {readFileSync} from 'node:fs';
const schema=JSON.parse(readFileSync(new URL('./fixtures/schema314.json',import.meta.url)));
export function fixture(pages,allEmpty=false){
 const a=Object.fromEntries(schema.Arena.map(k=>[k,[]]));Object.assign(a,{count:0,paint_count:0,payload_count:1,paint_table:[],payload_table:[{target:'https://example.test',border_width:1}]});
 const d=Object.fromEntries(schema.PageDocument.map(k=>[k,[]]));Object.assign(d,{arena:a,page_count:pages,destination_count:0});
 const o={documentId:'index-test',revision:0,sources:[{id:'s',version:0,text:'x'}],scopes:[{id:'parse',sourceId:'s',text:'x',baseByte:0,operations:[]}],groups:[],resources:[]};
 const tiles=new Map(),resources=[];
 for(let p=0;p<pages;p++){
  const count=allEmpty||pages>1&&p%3===0?0:3;d.firsts.push(a.count);d.counts.push(count);d.widths.push(100+p);d.heights.push(200+p);
  if(!count)continue;
  const rid='resource-'+p,key='glyph-'+p;
  o.resources.push({id:rid,version:0,binding:'binding-'+p});resources.unshift({id:rid,version:0,bytes:new Uint8Array([p,0,0,255]),image:{format:'rgba8unorm',alphaMode:'straight',width:1,height:1,bytesPerRow:4}});
  tiles.set(key,{resourceId:rid,plane:new Float64Array([0,0,1,1]),uv:new Float64Array([0,0,1,1])});
  for(let k=0;k<count;k++){
   const i=a.count++,kind=[0,2,3][k],g='group-'+i;
   const values={keys:k===0?key:'',kinds:kind,xs:i,ys:p,sxs:1,sys:1,widths:3,heights:4,draws:true,paints:-1,payloads:k===2?0:-1,a260_scopes:'parse',a260_texts:'x',a260_operations:i,a260_starts:0,a260_stops:1,a260_parts:0};
   for(const [key,value] of Object.entries(values))a[key].push(value);
   const leaf={part:0,id:'leaf-'+i,resources:[rid]};if(k===2)leaf.link='https://example.test';
   o.scopes[0].operations.push({operation:i,start:0,stop:1,groupId:g,leaves:[leaf]});
   o.groups.push({id:g,contentVersion:0,layoutVersion:0,contentKey:g,layoutKey:g,edges:i?[{kind:'flow',target:'group-'+(i-1)}]:[],spans:[{sourceId:'s',start:0,end:1}]});
  }
 }
 for(const op of o.scopes[0].operations)if(op.operation%3===1)op.leaves[0].resources=o.resources.map(r=>r.id);
 return {result:{document:d,complete:true,diagnostics:'',unresolved_json:'[]'},owner:o,options:{page:0,tiles,resources}};
}
