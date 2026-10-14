const atoms = positions => positions.map((position,i)=>({id:String(i),position,weight:1/positions.length}));
const match = source => source.map(p=>({source:p.id,target:p.id,weight:p.weight}));

export function fixture(name) {
  if(name==='material'){
    const source=atoms([[-.8,0]]),target=atoms([[.8,0]]);
    return {source,target,coupling:match(source),kind:'material',title:'Position, area and colour',
      note:'Position, geometric area, declared mass and linear RGB share one smooth clock. Mass here is an illustrative attribute, not a physics simulation.'};
  }
  if(name==='affine') {
    const source=atoms([[-.75,-.65],[.75,-.65],[.75,.65],[-.75,.65]]);
    const target=atoms(source.map(({position:[x,y]})=>[1.15*x+.65*y+.15,.15*x+.8*y]));
    return {source,target,coupling:match(source),rings:[4],kind:'polygon',title:'Affine scale and shear',
      note:'One affine map explains the whole object. Parallel edges stay parallel; no non-affine deformation is introduced.'};
  }
  if(name==='annulus') {
    const count=96, start=[],end=[];
    // Concentric star-shaped boundaries. Positive radial scale and fixed 0.48
    // inner/outer ratio give a one-hole annulus throughout the interpolation.
    for(const scale of [1,.48]) for(let i=0;i<count;i++) {
      const theta=2*Math.PI*i/count,c=Math.cos(theta),s=Math.sin(theta);
      const radius=c<-.55 ? -.55/c : 1;
      start.push([scale*c,scale*s]);end.push([scale*radius*c,scale*radius*s]);
    }
    const source=atoms(start),target=atoms(end);
    return {source,target,coupling:match(source),rings:[count,count],kind:'annulus',
      title:'O → D',note:'One hole stays open. Matched outer and inner contours; a constructed example, not automatic font matching.'};
  }
  if(name==='split') {
    return {source:atoms([[-.8,-.6],[0,.6],[.8,-.6]]),target:atoms(Array.from({length:7},(_,i)=>[Math.cos(i*2*Math.PI/7),Math.sin(i*2*Math.PI/7)])),kind:'points',
      title:'Three → seven',note:'A declared ordered coupling splits visual weight. Point transport alone provides no topology guarantee.'};
  }
  const source=atoms([[-.75,-.55],[.85,-.35],[.1,.85]]);
  const angle=name==='translation'?0:2*Math.PI/3,shift=name==='translation'?[.8,.35]:[0,0];
  const target=atoms(source.map(({position:[x,y]})=>[Math.cos(angle)*x-Math.sin(angle)*y+shift[0],Math.sin(angle)*x+Math.cos(angle)*y+shift[1]]));
  return {source,target,coupling:match(source),rings:[3],kind:'polygon',title:name==='translation'?'Translation':'Rotation',
    note:name==='translation'?'Translation is recovered; shape and pairwise distances stay fixed.':'120° rotation is recovered. Gold shows the shrinking point-interpolation baseline.'};
}
