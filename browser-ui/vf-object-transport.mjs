// Object identity supplies correspondence; each object chooses its own affine fit.
import {createEmbeddingTransport,sampleEmbeddingKinematics} from './vf-embedding-transport.mjs';
const plans=new WeakSet();
export function createObjectTransport(source,target){
  const index=(items,label)=>{
    if(!Array.isArray(items)||!items.length||items.length>128)throw new TypeError(`${label}: expected 1..128 objects`);
    const map=new Map();
    for(const item of items){
      if(!item||typeof item.id!=='string'||!item.id||map.has(item.id))throw new TypeError(`${label}: unique object IDs required`);
      map.set(item.id,item);
    }
    return map;
  };
  const a=index(source,'source'),b=index(target,'target');
  if(a.size!==b.size||[...a.keys()].some(id=>!b.has(id)))throw new TypeError('Object birth/death needs an explicit mapping');
  const objects=[...a].map(([id,start])=>{
    const end=b.get(id);
    const coupling=start.atoms.map(p=>({source:p.id,target:p.id,weight:p.weight}));
    const transport=createEmbeddingTransport(start.atoms,end.atoms,coupling);
    return Object.freeze({id,transport,fit:transport.pose.fit.kind});
  });
  const plan=Object.freeze({objects:Object.freeze(objects)});plans.add(plan);return plan;
}
export function sampleObjectTransport(plan,t,duration=1){
  if(!plans.has(plan))throw new TypeError('Expected an object transport plan');
  return plan.objects.map(({id,fit,transport})=>({id,fit,samples:sampleEmbeddingKinematics(transport,t,duration)}));
}
