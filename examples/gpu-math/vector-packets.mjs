// Instance packets for source-generated vector primitives. All path points are
// local to the item's origin; layout never needs to rewrite their topology.
const pt=72/72.27;
export function isVectorPrimitive(item){return['segment','bezier','circle','vectorrect'].includes(item.kind);}
export function vectorPaintItems(items){return items.flatMap(item=>{
 if(!['circle','vectorrect'].includes(item.kind)||!item.fill)return[item];
 const fill={...item,color:item.fillColor??item.color,lineWidth:0};
 return item.lineWidth?[fill,{...item,fill:false,color:item.strokeColor??item.color}]:[fill];
}).flatMap(item=>{
 if(item.kind!=='vectorrect'||!item.lineWidth||!item.dash||item.dash==='solid')return[item];
 const corners=[[0,0],[item.width,0],[item.width,item.height],[0,item.height],[0,0]];
 return corners.slice(0,-1).flatMap((p,i)=>{const q=corners[i+1];if(p[0]===q[0]&&p[1]===q[1])return[];return[{...item,kind:'segment',x:item.x+p[0]*(item.sx??1),y:item.y+p[1]*(item.sy??1),delta:[q[0]-p[0],q[1]-p[1]]}];});
});}
export function vectorPacket(item,color){
 const sx=item.sx??1,sy=item.sy??1;
 if(Math.abs(sx-sy)>1e-8||sx<=0)throw Error('Nonuniform native vector scaling is not implemented');
 const width=(item.lineWidth??0)*sx;
 if(item.kind==='segment'||item.kind==='bezier'){
  const delta=item.delta.map((v,i)=>v*(i?sy:sx)),controls=item.controls?.flatMap(p=>[p.x*sx,p.y*sy])??[0,0,0,0];
  let on=0,off=0;
  if(item.dash&&item.dash!=='solid'){
   if(item.kind==='bezier')throw Error('Dashed Bezier arc-length rendering is not implemented');
   if(item.dash==='dashed'){on=3*pt*sx;off=on;}else{on=width;off=(item.dash==='densely dotted'?1:item.dash==='loosely dotted'?4:2)*pt*sx;}
  }
  return[item.x,item.y,...delta,...controls,...color,item.kind==='bezier'?6:4,width,on,off];
 }
 return[item.x,item.y,item.width*sx,item.height*sy,0,0,0,0,...color,item.kind==='circle'?5:7,width,item.fill?1:0,0];
}
export function vectorBounds(item){
 const sx=item.sx??1,sy=item.sy??1,pad=(item.lineWidth??0)*sx/2;
 const points=item.delta?[[0,0],item.delta,...(item.controls??[]).map(p=>[p.x,p.y])]:[[0,0],[item.width,item.height]];
 return[item.x+Math.min(...points.map(p=>p[0]*sx))-pad,item.y+Math.min(...points.map(p=>p[1]*sy))-pad,item.x+Math.max(...points.map(p=>p[0]*sx))+pad,item.y+Math.max(...points.map(p=>p[1]*sy))+pad];
}
