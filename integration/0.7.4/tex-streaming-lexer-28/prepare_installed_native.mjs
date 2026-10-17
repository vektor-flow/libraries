// Preparation only: caller may marshal these values after a NEW native grant.
// This file invokes no compiler, runner, TeX engine, service or filesystem write.
import {readFileSync} from 'node:fs';
import {createPackageSourceBundle} from '../../../examples/gpu-math/native-vkf/host/latex_package_sources.mjs';
import {mouthOriginTable} from './candidate/examples/gpu-math/native-vkf/host/latex_mouth_origins.mjs';
export function prepareInstalledNative() {
  const manifest=JSON.parse(readFileSync(new URL('./installed-sources.json',import.meta.url)));
  const bundle=createPackageSourceBundle({engineIdentity:'vkf.tex.mouth/ascii-1; unqualified',initialStateIdentity:'formatted-ascii-defaults; NOT INITEX',
    files:manifest.files.map(row=>({id:row.id,version:0,kind:row.id.endsWith('.ltx')?'kernel':'package',sha256:row.sha256,bytes:readFileSync(row.path)}))});
  const context=bundle.context();
  const occurrences=manifest.files.map(row=>context.enter(row.id));
  const names=['ifnum','NeedsTeXFormat','ProvidesPackage'];
  const calls=manifest.files.map((row,i)=>({entry:'tex_streaming_mouth_tests.installed_first_boundary',
    args:[bundle.sourceTable,mouthOriginTable(context),i,names[i],row.first_boundary.startByte,row.first_boundary.startByte+1+names[i].length],
    sourceId:row.id,sha256:row.sha256,expected:true,executed:false}));
  return {bundle,context,occurrences,calls};
}
