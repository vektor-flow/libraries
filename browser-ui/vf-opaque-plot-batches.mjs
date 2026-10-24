// Only contiguous equal opaque triangle paints may be folded into one fill.
// Their nonzero winding must have the same sign. Every original path command,
// order, coordinate, transform and clip is retained, including shared edges.
// Transparent paints and all other path kinds keep their original draw order.
import {validatePlotPath} from './vf-plot-pdf-commands.mjs';
function triangle(item) {
 if(item?.kind!=='plotpath')return null;
 validatePlotPath(item);
 const c=item.commands;
 if(item.stroke!==null||item.fill?.[3]!==1||(item.fillRule??'nonzero')!=='nonzero'||c.length!==4||c[0][0]!=='M'||c[1][0]!=='L'||c[2][0]!=='L'||c[3][0]!=='Z')return null;
 const [a,b,d]=c,area=(b[1]-a[1])*(d[2]-a[2])-(b[2]-a[2])*(d[1]-a[1]);
 if(!Number.isFinite(area)||area===0)return null;
 return JSON.stringify([Math.sign(area),item.x,item.y,item.fill,item.matrix??[1,0,0,1,0,0],item.clips??[]]);
}
export function* opaquePlotPathBatches(items) {
 let held=null,key=null;
 for(const item of items) {
  const next=triangle(item);
  if(held&&next!==null&&next===key&&held.commands.length+item.commands.length<=100000)held.commands.push(...item.commands);
  else {if(held)yield held;held=next===null?item:{...item,commands:item.commands.slice()};key=next;}
 }
 if(held)yield held;
}
