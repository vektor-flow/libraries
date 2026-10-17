import {markDestination} from './document-links.mjs';
import {typesetDocumentText} from './document-text.mjs';
const pt=72/72.27;
const sp=pt/65536;
// pdftex.def converts image dimensions through Gin@defaultbp (.99626), then
// reparses those dimensions as bp. Keep that TeX box separate from its drawing.
const nativeImageDimension=bp=>Math.floor(Math.floor(Math.round(bp/sp)*65291/65536)*7227/7200);
export function graphicDimensions(asset,options,config){
 const naturalWidth=asset.widthBp??asset.width*72/96,naturalHeight=asset.heightBp??asset.height*72/96;
 function length(raw,fallback){if(raw===undefined)return fallback;const relative=/^([\d.]*)\\(textwidth|linewidth|textheight)$/.exec(raw);if(relative)return Number(relative[1]||1)*(relative[2]==='textheight'?config.textHeight:config.textWidth);const m=/^\s*([+-]?[\d.]+)\s*(pt|bp|cm|mm|in|em|ex)\s*$/.exec(raw);return m?Number(m[1])*({pt,bp:1,cm:72/2.54,mm:72/25.4,in:72,em:config.fontSize,ex:.43*config.fontSize}[m[2]]):fallback;}
 let width=length(options.width,naturalWidth),height=length(options.height,naturalHeight);
 if(options.width&&!options.height)height=width*naturalHeight/naturalWidth;if(options.height&&!options.width)width=height*naturalWidth/naturalHeight;
 if(options.keepaspectratio&&options.width&&options.height){const ratio=Math.min(width/naturalWidth,height/naturalHeight);width=naturalWidth*ratio;height=naturalHeight*ratio;}
 if(options.scale){width*=Number(options.scale);height*=Number(options.scale);}
 const drawWidth=width,drawHeight=height;
 if(!options.width&&!options.height){const factor=Math.round(Number(options.scale??1)*65536);width=Math.floor(nativeImageDimension(naturalWidth)*factor/65536)*sp;height=Math.floor(nativeImageDimension(naturalHeight)*factor/65536)*sp;}
 if(!Number.isFinite(width+height)||width<=0||height<=0)throw Error('Invalid image dimensions');return{width,height,drawWidth,drawHeight,naturalWidth,naturalHeight};
}
export function graphicItems(asset,name,x,y,dimensions){
 const {width,height,drawWidth=width,drawHeight=height,naturalWidth,naturalHeight}=dimensions;y+=height-drawHeight;
 if(!asset.items)return[{kind:'image',asset:name,x,y,width:drawWidth,height:drawHeight}];
 const sx=drawWidth/naturalWidth,sy=drawHeight/naturalHeight;return asset.items.map(item=>({...item,x:x+item.x*sx,y:y+item.y*sy,sx:(item.sx??1)*sx,sy:(item.sy??1)*sy,sourceAsset:{x:item.x,y:item.y,scaleX:sx,scaleY:sy,drawHeight}}));
}
export function measureDocumentFloat(block,{config,data,assets,resolveText,packages,extensions}){
 const items=[],diagnostics=[];let y=0,overwide=false;
 const children=block.style==='plain'?[...block.blocks.filter(b=>b.kind!=='caption'),...block.blocks.filter(b=>b.kind==='caption')]:block.blocks;
 for(const child of children){
  if(child.kind==='vspace'){y+=child.amount+(child.trailingLine&&overwide?12*pt:0);continue;}
  if(child.kind==='image'){
   const asset=assets[child.asset]??assets[child.asset.replace(/\.[^.]+$/,'')];if(!asset){diagnostics.push('Missing image asset: '+child.asset);continue;}
   let dims;try{dims=graphicDimensions(asset,child.options,config);}catch(error){diagnostics.push(error.message);continue;}
   overwide=block.center&&dims.width>config.textWidth;if(overwide)y+=pt;
   items.push(...graphicItems(asset,child.asset,Math.max(0,(config.textWidth-dims.width)/2),y,dims));y+=dims.height+10*pt;continue;
  }
  const literal=child.kind==='verbatim',font=literal?(child.context?.font==='footnote'?'footnotemono':'mono'):'roman';
  const childData={...data,documentLinks:child.context?.linkAppearance??data.documentLinks};
  const source=literal?child.source:resolveText(child.source),single=child.kind==='caption'?typesetDocumentText(source,childData,{font,width:1000000,justify:false,hyphens:false,preserveTrailingSpace:true,packages,extensions}):null,box=single&&single.width<=config.textWidth?single:typesetDocumentText(source,childData,{font,width:config.textWidth,justify:!literal,literal,literalInput:child.fileInput??false,packages,extensions,tolerance:9999,emergencyStretch:3*data.documentFonts[font].spaces.quad});markDestination(box.items,child.destinationIds);diagnostics.push(...box.diagnostics);
  if(child.kind==='caption'&&block.style==='plain')y+=20*pt;
  const leading=literal?(child.context?.lineHeight??12*pt):12*pt;
  for(const [index,line]of box.lines.entries()){
   const adjacent=index?box.lines[index-1].depth+line.height:0,step=index?(adjacent>leading?adjacent+pt:leading):literal||block.style==='plain'?line.height:12*pt;
   const baseline=y+step,shift=child.kind==='caption'&&box.lines.length===1?(config.textWidth-box.width)/2:0;
   for(const item of box.items)if(item.flowLine===index)items.push(item.kind==='link'?{...item,x:item.x+shift-pt,y:baseline-line.height-pt,width:item.width+2*pt,height:line.height+line.depth+2*pt}:{...item,x:item.x+shift,y:baseline+item.y-line.baseline});
   y=baseline+(index===box.lines.length-1?line.depth:0);
  }
  if(child.kind==='caption'&&block.style!=='plain')y+=10*pt;
 }
 return{items,height:Math.max(0,y),diagnostics,placement:block.placement??'tbp'};
}
