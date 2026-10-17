import {contractFromTikzPacket} from './vf-analytic-curves.mjs';
// Project authentic float32 instance controls, preserving the exact cubic packet.
// The existing shader and PDF exporter remain the curve/raster authorities.
export function prepareTikzConsumer(values,{scale,zoom,origin,width,height}) {
 if(!(values instanceof Float32Array)||values.length%16)throw TypeError('16-column float32 instances required');
 if(![scale,zoom,width,height,...origin].every(Number.isFinite)||origin.length!==2||scale<=0||zoom<=0||width<=0||height<=0)throw RangeError('finite positive viewport required');
 const factor=scale*zoom;
 if(!Number.isFinite(factor)||factor<=0)throw RangeError('finite viewport scale required');
 const matrix=[factor,0,0,-origin[0]*factor,0,factor,0,-origin[1]*factor];
 const curves=new Map();
 for(let i=0;i<values.length/16;i++){
  const packet=Array.from(values.subarray(i*16,(i+1)*16));
  if(packet[12]!==6)continue;
  if(packet[13]<0)throw RangeError('nonnegative cubic stroke width required');
  const contract=contractFromTikzPacket(packet,`instance-${i}`);
  // Validate the same affine numeric domain without building unused polylines.
  if(!matrix.every(Number.isFinite))throw TypeError('finite affine projection/budget required');
  for(const [x,y,z] of contract.branches[0].controls){
   const projected=[matrix[0]*x+matrix[1]*y+matrix[2]*z+matrix[3],matrix[4]*x+matrix[5]*y+matrix[6]*z+matrix[7]];
   if(!projected.every(v=>Number.isFinite(v)&&Math.abs(v)<=1e12))throw RangeError('projection outside finite supported range');
  }
  // Use the original control hull to cull, not the approximate polyline:
  // this preserves all fragments of the unchanged shader's padded quad,
  // including its finite-precision closest-point and antialiasing behavior.
  const controls=contract.branches[0].controls.map(([x,y])=>[(x-origin[0])*factor,(y-origin[1])*factor]);
  const pad=(packet[13]/2+1)*factor;
  // Extra device margin avoids float32 viewport rounding at clip boundaries.
  const rounding=32*2**-23*Math.max(1,width,height,...controls.flat().map(Math.abs),Math.abs(origin[0]*factor),Math.abs(origin[1]*factor));
  const margin=pad+rounding;
  const bounds=[Math.min(...controls.map(p=>p[0]))-margin,Math.min(...controls.map(p=>p[1]))-margin,Math.max(...controls.map(p=>p[0]))+margin,Math.max(...controls.map(p=>p[1]))+margin];
  if(!bounds.every(Number.isFinite))throw RangeError('finite cubic bounds required');
  curves.set(i,{bounds,visible:bounds[2]>=0&&bounds[3]>=0&&bounds[0]<=width&&bounds[1]<=height});
 }
 return curves;
}
