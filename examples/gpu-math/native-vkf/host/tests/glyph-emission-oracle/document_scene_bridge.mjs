import {prepareTypedPacket} from './document_typed_bridge.mjs';
// Host projection of document_scene.Arena, retaining row order. Explicitly
// supports glyph/field/rule/link/segment/bezier/circle/vectorrect/image; other kinds must use their own qualified adapter.
export function sceneColumns(scene, metadata, tiles){
 const a=scene.arena,n=a?.count;
 if(!Number.isSafeInteger(n)||n<0||!(tiles instanceof Map))throw Error('Invalid Scene');
 for(const name of ['xs','ys','sxs','sys','widths','heights']){
  const v=a[name];if(!(v instanceof Float64Array)||v.length!==n)throw Error('Invalid Scene numeric column '+name);
  for(const x of v)if(!Number.isFinite(x)||Math.abs(x)>1e20)throw Error('Invalid Scene geometry');
 }
 for(const name of ['kinds','paints','payloads'])if(!(a[name] instanceof Int32Array)||a[name].length!==n)throw Error('Invalid Scene index column');
 if(!Array.isArray(a.keys)||a.keys.length!==n||!Array.isArray(a.paint_table)||!Array.isArray(a.payload_table)||!(a.draws instanceof Uint8Array)||a.draws.length!==n)throw Error('Invalid Scene tables');
 // Only these kinds are guaranteed to emit exactly one row. Classification
 // does not replace the per-leaf validation below; all other scenes retain
 // the variable-row path and its emission order.
 const singleRow=a.kinds.every(k=>k>=0&&k<=3);
 const directColumns=singleRow?Array.from({length:16},()=>new Float64Array(n)):null;
 const rows=singleRow?null:[],drawSources=[],glyphs=[];
 let emitted=0;
 const emit=(row,source)=>{
  if(singleRow){for(let j=0;j<16;j++)directColumns[j][emitted]=row[j];}
  else rows.push(row);
  emitted++;drawSources.push(source);
 };
 for(let i=0;i<n;i++){
  const k=a.kinds[i],pi=a.paints[i],qi=a.payloads[i];
  if((![0,1,2,3,4,5,6,7,8].includes(k))||pi< -1||pi>=a.paint_table.length||qi< -1||qi>=a.payload_table.length||a.draws[i]!==1)throw Error('Unsupported Scene leaf or table reference');
  const paint=pi<0?{red:0,green:0,blue:0,alpha:1}:a.paint_table[pi],color=[paint.red,paint.green,paint.blue,paint.alpha];
  if(color.some(x=>!Number.isFinite(x)||x<0||x>1))throw Error('Invalid paint');
  const x=a.xs[i],y=a.ys[i],w=a.widths[i],h=a.heights[i],p=qi<0?null:a.payload_table[qi];let row;
  if(k<2){
   const t=tiles.get(a.keys[i]);if(!t||!metadata?.leafResources?.[emitted]?.includes(t.resourceId))throw Error('Missing explicit glyph resource');
   glyphs.push({leaf:emitted,resourceId:t.resourceId});
   const b=t.plane,u=t.uv;
   if(!(b instanceof Float64Array)||!(u instanceof Float64Array)||b.length!==4||u.length!==4||![...b,...u].every(Number.isFinite)||b[2]<=b[0]||b[3]<=b[1]||u.some(v=>v<0||v>1))throw Error('Invalid glyph tile');
   // Scene payload endpoints carry independent presence bits. An absent
   // endpoint contains a numeric default, not a clipping bound.
   const bound=(axis,present,value,fallback,clamp)=>{
    if(!p||!p[axis])return fallback;
    if(typeof p[present]!=='boolean')throw Error('Missing crop endpoint presence');
    if(!p[present])return fallback;
    if(!Number.isFinite(p[value]))throw Error('Invalid crop endpoint');
    return clamp(fallback,p[value]);
   };
   const left=bound('crop_x','crop_left','left',b[0],Math.max),right=bound('crop_x','crop_right','right',b[2],Math.min),top=bound('crop_y','crop_top','top',b[1],Math.max),bottom=bound('crop_y','crop_bottom','bottom',b[3],Math.min);
   if(right<left||bottom<top)throw Error('Empty glyph crop');
   row=[x+left*a.sxs[i],y+top*a.sys[i],(right-left)*a.sxs[i],(bottom-top)*a.sys[i],u[0]+(left-b[0])/(b[2]-b[0])*(u[2]-u[0]),u[1]+(top-b[1])/(b[3]-b[1])*(u[3]-u[1]),u[0]+(right-b[0])/(b[2]-b[0])*(u[2]-u[0]),u[1]+(bottom-b[1])/(b[3]-b[1])*(u[3]-u[1]),...color,0,0,0,0];
  }else if(k===4){
   const binding=metadata?.images?.find(t=>t.leaf===emitted);
   if(!p||typeof p.asset!=='string'||!p.asset||!binding||binding.asset!==p.asset||!metadata.leafResources?.[emitted]?.includes(binding.resourceId)||w<0||h<0)throw Error('Missing explicit image resource or invalid dimensions');
   // Image width/height are final document dimensions in the renderer ABI.
   // Texture selection is explicit metadata; numeric geometry cannot identify it.
   row=[x,y,w,h,0,0,1,1,1,1,1,1,2,0,0,0];
  }else if(k===7||k===8){
   if(!p||typeof p.fill!=='boolean'||!Number.isFinite(p.line_width)||p.line_width<0||!Number.isInteger(p.dash)||p.dash<0||p.dash>4||w<0||h<0)throw Error('Invalid closed vector payload');
   const sx=a.sxs[i],sy=a.sys[i];
   if(Math.abs(sx-sy)>1e-8||sx<=0)throw Error('Unsupported vector scaling');
   const paintColor=index=>{
    if(!Number.isInteger(index)||index< -1||index>=a.paint_table.length)throw Error('Invalid closed vector paint reference');
    if(index===-1)return color;
    const t=a.paint_table[index],c=[t.red,t.green,t.blue,t.alpha];
    if(c.some(v=>!Number.isFinite(v)||v<0||v>1))throw Error('Invalid closed vector paint');
    return c;
   };
   const fillColor=paintColor(p.fill_paint),strokeColor=paintColor(p.stroke_paint);
   const closed=(c,width,fill)=>{
    if(k===8&&width&&p.dash){
     const pt=72/72.27,on=p.dash===1?3*pt*sx:width;
     const off=p.dash===1?on:(p.dash===3?1:p.dash===4?4:2)*pt*sx;
     const corners=[[0,0],[w,0],[w,h],[0,h],[0,0]];
     for(let edge=0;edge<4;edge++){
      const [ax,ay]=corners[edge],[bx,by]=corners[edge+1];
      if(ax===bx&&ay===by)continue;
      emit([x+ax*sx,y+ay*sy,(bx-ax)*sx,(by-ay)*sy,0,0,0,0,...c,4,width,on,off],i);
     }
    }else emit([x,y,w*sx,h*sy,0,0,0,0,...c,k===7?5:7,width,fill,0],i);
   };
   if(p.fill){closed(fillColor,0,1);if(p.line_width)closed(strokeColor,p.line_width*sx,0);}
   else closed(color,p.line_width*sx,0);
   continue;
  }else if(k===5||k===6){
   if(!p||!['dx','dy','line_width'].every(key=>Number.isFinite(p[key]))||p.line_width<0||!Number.isInteger(p.dash)||p.dash<0||p.dash>4)throw Error('Invalid vector payload');
   const sx=a.sxs[i],sy=a.sys[i];
   if(Math.abs(sx-sy)>1e-8||sx<=0)throw Error('Unsupported vector scaling');
   if(k===6&&(!['c1x','c1y','c2x','c2y'].every(key=>Number.isFinite(p[key]))||p.dash!==0))throw Error('Invalid or dashed Bezier');
   const width=p.line_width*sx,pt=72/72.27;
   const on=p.dash===0?0:p.dash===1?3*pt*sx:width;
   const off=p.dash===0?0:p.dash===1?on:(p.dash===3?1:p.dash===4?4:2)*pt*sx;
   const controls=k===6?[p.c1x*sx,p.c1y*sy,p.c2x*sx,p.c2y*sy]:[0,0,0,0];
   row=[x,y,p.dx*sx,p.dy*sy,...controls,...color,k===6?6:4,width,on,off];
  }else if(k===3){
   if(!p||!Number.isFinite(p.border_width)||p.border_width<0||!metadata?.links?.some(l=>l.leaf===emitted&&l.target===p.target))throw Error('Missing explicit link');
   row=p.border_width===0?[0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0]:[x-1.5,y-1.5,w+3,h+3,0,0,0,0,...color,1,w+1,h+1,1];
  }else row=[x-1,y-1,w+2,h+2,0,0,0,0,...color,1,w,h,0];
  emit(row,i);
 }
 if(a.kinds.includes(7)||a.kinds.includes(8)||metadata?.drawSources!==undefined){
  if(!Array.isArray(metadata?.sourceLeafIds)||metadata.sourceLeafIds.length!==n||metadata.sourceLeafIds.some(x=>typeof x!=='string'||!x)||new Set(metadata.sourceLeafIds).size!==n||!Array.isArray(metadata.drawSources)||metadata.drawSources.length!==emitted||metadata.drawSources.some((x,i)=>x!==drawSources[i]))throw Error('Missing explicit source-to-draw mapping');
 }
 const columns=directColumns??Array.from({length:16},(_,j)=>Float64Array.from(rows,row=>row[j]));
 const packet={count:emitted,columns,metadata:{...metadata,glyphs}};
 prepareTypedPacket(packet); // Validate semantic coverage before any device call.
 return packet;
}
