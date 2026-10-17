import {resolveDocumentProject} from './document-project.mjs';
import {resolveDocumentClass} from './latex-modules/registry.mjs';
export async function requestedFontProfile(source,{files={},buildContext={}}={}){
 const project=resolveDocumentProject(source,{files,entry:buildContext.entry,jobName:buildContext.jobName}),modules=await resolveDocumentClass(project.source);
 return modules.classModule?.configure(modules.options).fontProfile??null;
}
export function validateFontProfile(name,mapping,maxDimension=8192){
 if(!/^[A-Za-z][A-Za-z0-9-]*$/.test(name)||mapping.fontProfile!==name)throw Error('Font profile identity differs from its request');
 const [w,h]=mapping.atlasSize??[];
 if(![w,h].every(n=>Number.isInteger(n)&&n>0&&n<=maxDimension)||w*h>33554432)throw Error('Font profile atlas dimensions exceed limits');
 for(const style of ['display','text','script','scriptscript']){
  const map=mapping.maps?.[style];if(!map||map.style!==style||!Number.isFinite(map.em)||map.em<=0||!map.symbols)throw Error('Invalid native font style: '+style);
  for(const [token,symbol]of Object.entries(map.symbols))if(!mapping.tiles[style+'/'+token]||!['width','height','depth'].every(k=>Number.isFinite(symbol[k])))throw Error('Unmeasured font profile symbol: '+token);
 }
 if(!mapping.documentFonts?.roman)throw Error('Font profile document metrics are unavailable');
 return mapping;
}
