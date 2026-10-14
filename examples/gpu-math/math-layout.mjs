/** Independent bounded math typesetter. Generated LaTeX mapping is data only. */
export function layoutMath(source,mapping) {
  if (mapping.schema!=='vkf.latex-symbol-mapping/1') throw Error('Unsupported symbol mapping');
  const atoms=[];
  for (let offset=0;offset<source.length;) {
    const rest=source.slice(offset);
    const token=/^(?:\\[A-Za-z]+|[A-Za-z0-9+\-=<>()[\],])/.exec(rest)?.[0];
    if (/^\s/.test(rest)) {offset++;continue;}
    if (!token || !mapping.symbols[token]) throw Error(`Unsupported LaTeX syntax at ${offset}: ${rest.slice(0,16)}`);
    atoms.push({token,...mapping.symbols[token]});offset+=token.length;
  }
  if (!atoms.length) throw Error('Empty math expression');
  // TeX binary-atom correction: unary signs and trailing binaries become ord.
  for (let i=0;i<atoms.length;i++) {
    if (atoms[i].class==='bin' && (i===0 || ['bin','op','rel','open','punct'].includes(atoms[i-1].class))) atoms[i].class='ord';
    if (['rel','close','punct'].includes(atoms[i].class) && i && atoms[i-1].class==='bin') atoms[i-1].class='ord';
  }
  if (atoms.at(-1).class==='bin') atoms.at(-1).class='ord';
  const spacing={ord:{ord:0,bin:4,rel:5,open:0,close:0,punct:0},
    bin:{ord:4,open:4},rel:{ord:5,open:5},open:{ord:0,open:0,close:0},
    close:{ord:0,bin:4,rel:5,open:0,close:0,punct:0},punct:{ord:3,open:3,close:3}};
  let cursor=0;
  const outlines={},primitives=[];
  const baseline=Math.max(...atoms.map(a=>a.height));
  for (let i=0;i<atoms.length;i++) {
    const atom=atoms[i];
    if (i) {
      const mu=spacing[atoms[i-1].class]?.[atom.class];
      if (mu===undefined) throw Error(`Unsupported atom adjacency: ${atoms[i-1].class}/${atom.class}`);
      cursor+=mu*mapping.em/18;
    }
    outlines[atom.outlineHash]=atom.outline;
    primitives.push({id:`atom-${i}`,kind:'path',outline:atom.outlineHash,
      transform:[1,0,0,1,cursor,baseline],sourceId:null});
    cursor+=atom.width;
  }
  return {schema:'vkf.latex-path-packet/1',units:'SVG pt (1/72 inch), top-down',
    bounds:[0,0,cursor,baseline+Math.max(...atoms.map(a=>a.depth))],
    outlines,primitives,fillRule:'nonzero',source,
    limits:['Bounded independent atom typesetting; unsupported syntax rejected.']};
}
