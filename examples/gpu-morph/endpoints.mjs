// Endpoint authoring only. No pairing, deformation or animation is done here.
export function packScenes(a,b,data,budget){
 const rows=[a,b].map(box=>box.items.filter(i=>i.kind!=='placeholder'));
 if(!a.complete||!b.complete||a.diagnostics.length||b.diagnostics.length)throw Error('Both equations must be complete and supported.');
 const per=Math.max(...rows.map(x=>x.length))+1,copies=Math.max(1,Math.floor(budget/per));
 if(per>1024)throw Error('This equation exceeds the1024-body test limit.');
 const cols=Math.ceil(Math.sqrt(copies*1200/760)),lines=Math.ceil(copies/cols),cw=1160/cols,ch=720/lines;
 const scale=Math.min((cw-18)/Math.max(a.width,b.width),(ch*.7)/Math.max(a.height+a.depth,b.height+b.depth));
 const result=[[],[]];const colors=[[.25,.85,.96,1],[.98,.4,.67,1],[.55,.9,.4,1],[.75,.52,.99,1]];
 for(let side=0;side<2;side++){
  const box=side?b:a;
  for(let c=0;c<copies;c++){
   // Independent endpoint layouts, not an object correspondence table.
   const cell=side?copies-1-c:c,x=20+(cell%cols)*cw+(cw-box.width*scale)/2,y=20+Math.floor(cell/cols)*ch+(ch*.7-(box.height+box.depth)*scale)/2+box.height*scale;
   for(const item of rows[side]){
    const color=item.color??colors[(c+side)%colors.length],rgba=[...color.slice(0,3),color[3]??1];
    if(item.kind==='glyph'){
     const tile=data.tiles[item.key];if(!tile)throw Error('Missing glyph field');const p=tile.plane,sx=item.sx??1,sy=item.sy??1;
     const l=Math.max(p[0],item.cropX?.[0]??p[0]),r=Math.min(p[2],item.cropX?.[1]??p[2]),lo=Math.max(p[1],item.crop?.[0]??p[1]),hi=Math.min(p[3],item.crop?.[1]??p[3]);
     const uv=[tile.uv[0]+(l-p[0])/(p[2]-p[0])*(tile.uv[2]-tile.uv[0]),tile.uv[1]+(lo-p[1])/(p[3]-p[1])*(tile.uv[3]-tile.uv[1]),tile.uv[0]+(r-p[0])/(p[2]-p[0])*(tile.uv[2]-tile.uv[0]),tile.uv[1]+(hi-p[1])/(p[3]-p[1])*(tile.uv[3]-tile.uv[1])];
     result[side].push(x+(item.x+l*sx)*scale,y+(item.y+lo*sy)*scale,(r-l)*sx*scale,(hi-lo)*sy*scale,...uv,...rgba,0,0,0,0);
    }else result[side].push(x+item.x*scale,y+item.y*scale,item.width*scale,item.height*scale,0,0,0,0,...rgba,1,0,0,0);
   }
   const radius=Math.min(cw*.13,ch*.22);result[side].push(20+(cell%cols)*cw+cw*.5-radius/2,20+Math.floor(cell/cols)*ch+ch*.78,radius,radius,0,0,0,0,...colors[(c+side+2)%4],side?5:4,0,0,0);
  }
 }
 const count=Math.max(...result.map(x=>x.length))/16;
 for(const list of result)while(list.length<count*16)list.push(600,380,20,20,0,0,0,0,1,1,1,1,2,0,0,0);
 return {a:new Float32Array(result[0]),b:new Float32Array(result[1]),count,copies};
}
