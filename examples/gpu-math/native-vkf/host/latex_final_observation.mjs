// A306 final-column guard composed at the current producer boundary. State is
// private and keyed by the exact returned full-document bound, never tile keys.
export function createFinalObservationBinding(){
 const observations=new WeakMap();
 return function bindFinalObservation(bound,packet,previous=null){
 const old=previous===null?null:observations.get(previous);
 if(previous!==null&&!old)throw Error('Previous final observation bound required');
 const {metadata:m}=bound;
 if(packet.count!==m.leafIds.length)throw Error('Unsupported final observation row mapping');
 const rows=new Map();
 for(const g of m.groups){
  const values=[];
  for(let i=g.first;i<g.first+g.count;i++){
   values.push(m.leafIds[i]);
   for(const c of packet.columns)values.push(c[i]);
  }
  const prior=old?.get(g.id);
  if(prior&&(prior.values.length!==values.length||values.some((v,i)=>!Object.is(v,prior.values[i])))&&g.layoutVersion<=prior.layoutVersion)
   throw Error('Typed output edit requires layout version');
  rows.set(g.id,{values,layoutVersion:g.layoutVersion});
 }
 // The existing metadata binder has already enforced dependency advancement
 // for every changed owner layoutVersion. Failed calls expose no new bound.
 observations.set(bound,rows);
}
}
