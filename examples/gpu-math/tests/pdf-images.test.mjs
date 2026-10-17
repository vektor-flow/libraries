import test from 'node:test';
import assert from 'node:assert/strict';
import {deflateSync,inflateSync} from 'node:zlib';
import {pdfPngImage} from '../pdf-images.mjs';
import {exportVectorPdf} from '../vector-pdf.mjs';

function crc(bytes) {
  let value=0xffffffff;
  for(const byte of bytes){value^=byte;for(let bit=0;bit<8;bit++)value=(value>>>1)^((value&1)?0xedb88320:0);}
  return (value^0xffffffff)>>>0;
}
function chunk(type,bytes) {
  const kind=Buffer.from(type),size=Buffer.alloc(4),check=Buffer.alloc(4);
  size.writeUInt32BE(bytes.length);check.writeUInt32BE(crc(Buffer.concat([kind,bytes])));
  return Buffer.concat([size,kind,bytes,check]);
}
export function pngFixture({kind=2,depth=8,interlace=0,extra=[]}={}) {
  const header=Buffer.alloc(13);header.writeUInt32BE(2);header.writeUInt32BE(2,4);header[8]=depth;header[9]=kind;header[12]=interlace;
  // Two independent PNG row filters: Sub for red/green, Up for blue/white.
  const rows=Buffer.from(kind===0?[0,0,255,0,255,0]:[1,255,0,0,1,255,0,2,1,0,255,255,0,255]),idat=deflateSync(rows),mid=Math.floor(idat.length/2);
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),...extra.map(([name,body])=>chunk(name,Buffer.from(body))),chunk('IDAT',idat.subarray(0,mid)),chunk('IDAT',idat.subarray(mid)),chunk('IEND',Buffer.alloc(0))]);
}
const vectors={schema:'vkf.pdf-vectors/1',keys:{},paths:{}};
const layout={pages:[{width:20,height:20,items:[{kind:'image',asset:'test.png',x:0,y:0,width:20,height:20}]}]};

test('opaque PNG retains IDAT bytes and PDF predictors, including split IDAT chunks',async()=>{
  const png=pngFixture(),prepared=pdfPngImage(png);
  assert.deepEqual([prepared.width,prepared.height,prepared.colors],[2,2,3]);
  assert.deepEqual([...inflateSync(prepared.idat)],[1,255,0,0,1,255,0,2,1,0,255,255,0,255]);
  const metrics={},pdf=await exportVectorPdf(layout,vectors,{images:{'test.png':{png}},metrics});
  assert.ok(Buffer.from(pdf).includes(Buffer.from('/Predictor 15 /Colors 3')));
  assert.ok(Buffer.from(pdf).includes(Buffer.from(prepared.idat)));
  assert.equal(metrics.preservedPngCount,1);assert.equal(metrics.imageChannelMs,0);
});

test('8-bit grayscale PNG uses one predictor colour channel',async()=>{
  const png=pngFixture({kind:0});assert.equal(pdfPngImage(png).colors,1);
  const pdf=await exportVectorPdf(layout,vectors,{images:{'test.png':{png}}});
  assert.ok(Buffer.from(pdf).includes(Buffer.from('/ColorSpace /DeviceGray')));
  assert.ok(Buffer.from(pdf).includes(Buffer.from('/Predictor 15 /Colors 1')));
});

test('alpha, palettes, interlacing, colour profiles and animation require normal decoding',()=>{
  for(const options of [{kind:6},{kind:4},{kind:3},{depth:16},{interlace:1},
    ...['tRNS','iCCP','sRGB','gAMA','cHRM','cICP','acTL'].map(name=>({extra:[[name,[0]]]}))])assert.equal(pdfPngImage(pngFixture(options)),null);
});

test('truncated PNG and invalid dimensions/chunk sizes never enter the predictor path',()=>{
  const original=pngFixture();
  for(const length of [0,8,20,original.length-1])assert.equal(pdfPngImage(original.subarray(0,length)),null);
  const oversized=Buffer.from(original);oversized.writeUInt32BE(0xffffffff,16);assert.equal(pdfPngImage(oversized),null);
  const chunkSize=Buffer.from(original);chunkSize.writeUInt32BE(0xffffffff,8);assert.equal(pdfPngImage(chunkSize),null);
});

test('RGBA fallback preserves exact separate colour and alpha planes',async()=>{
  const rgba=new Uint8Array([255,0,0,255,0,0,255,128]);
  const pdf=Buffer.from(await exportVectorPdf(layout,vectors,{images:{'test.png':{width:1,height:2,rgba}}}));
  const planes=[];let at=0;
  while((at=pdf.indexOf('stream\n',at))>=0){const start=at+7,end=pdf.indexOf('\nendstream',start);planes.push(inflateSync(pdf.subarray(start,end)));at=end+10;}
  assert.deepEqual([...planes[0]],[255,128]);assert.deepEqual([...planes[1]],[255,0,0,0,0,255]);
});
