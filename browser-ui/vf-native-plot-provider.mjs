import {createNativePlotTypography} from './vf-native-plot-labels.mjs';
export const NATIVE_PLOT_VECTOR_PIN=Object.freeze({"bytes": 803191, "sha256": "6cd42f5cc13c9ea2e93ce8ab8860aab0615c880d0a5595db6510dad0759032f4", "mappingSha256": "79177038cb6d9df251254f90438de305b6a9fd167f96795f76d6602ec043ca1b"});
/** Privileged application bootstrap. The genuine completed926 bridge validates
 * original engine identity, frames, exact catalogue/atlas queries and lifetimes.
 * Only this constructor receives the broker capability and vector asset URL.
 * Label requests never receive either, and never open processes themselves.
 */
export async function openBrowserNativePlotTypography({openBrowserNative075,connection,vectorUrl,fetchAsset=fetch,maxEntries=128}={}) {
 if(typeof openBrowserNative075!=='function')throw Object.assign(Error('PLOT_NATIVE075_BRIDGE_MISSING'),{status:'BLOCKED'});
 let consumer,typography;
 try{
  const response=await fetchAsset(vectorUrl,{credentials:'omit',redirect:'error',cache:'force-cache'});
  if(!response.ok)throw Object.assign(Error('PLOT_NATIVE_VECTOR_ASSET_MISSING'),{status:'BLOCKED'});
  const bytes=await response.arrayBuffer();if(bytes.byteLength!==NATIVE_PLOT_VECTOR_PIN.bytes)throw Error('PLOT_NATIVE_VECTOR_SIZE');
  const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
  if(sha!==NATIVE_PLOT_VECTOR_PIN.sha256||connection?.presentationIdentity?.mappingSha256!==NATIVE_PLOT_VECTOR_PIN.mappingSha256)throw Error('PLOT_NATIVE_VECTOR_BINDING');
  const vectors=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  if(vectors.mappingSha256!==NATIVE_PLOT_VECTOR_PIN.mappingSha256)throw Error('PLOT_NATIVE_VECTOR_MAPPING');
  consumer=await openBrowserNative075(connection);
  typography=createNativePlotTypography({provider:consumer.provider,vectors,engineIdentity:connection.engineIdentity,maxEntries});
  let closing;return Object.freeze({...typography,close(){return closing??=(async()=>{const errors=[];try{await typography.close();}catch(e){errors.push(e);}let joined;try{joined=await consumer.close();}catch(e){errors.push(e);}if(errors.length)throw new AggregateError(errors,'Native plot typography cleanup failed');return joined;})();}});
 }catch(e){await consumer?.close();throw e;}
}
