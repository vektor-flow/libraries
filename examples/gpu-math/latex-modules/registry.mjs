// Each class/package has a separate module. No user TeX is executed as code.
const classes={amsart:()=>import('./classes/amsart.mjs'),article:()=>import('./classes/article.mjs')};
const packages={enumitem:()=>import('./packages/enumitem.mjs'),bbm:()=>import('./packages/bbm.mjs'),'tikz-cd':()=>import('./packages/tikz-cd.mjs'),hyperref:()=>import('./packages/hyperref.mjs'),biblatex:()=>import('./packages/biblatex.mjs'),faktor:()=>import('./packages/faktor.mjs'),tikz:()=>import('./packages/tikz.mjs'),latexsym:()=>import('./packages/latexsym.mjs'),amscd:()=>import('./packages/amscd.mjs'),verbatim:()=>import('./packages/verbatim.mjs'),graphics:()=>import('./packages/graphics.mjs'),float:()=>import('./packages/float.mjs'),url:()=>import('./packages/url.mjs'),bm:()=>import('./packages/bm.mjs'),amsbsy:()=>import('./packages/amsbsy.mjs'),amstext:()=>import('./packages/amstext.mjs'),amsthm:()=>import('./packages/amsthm.mjs'),amsmath:()=>import('./packages/amsmath.mjs'),graphicx:()=>import('./packages/graphicx.mjs'),geometry:()=>import('./packages/geometry.mjs'),xcolor:()=>import('./packages/xcolor.mjs'),color:()=>import('./packages/xcolor.mjs'),siunitx:()=>import('./packages/siunitx.mjs'),amsfonts:()=>import('./packages/amsfonts.mjs'),amssymb:()=>import('./packages/amssymb.mjs'),mathrsfs:()=>import('./packages/mathrsfs.mjs')};
export async function resolveDocumentClass(source){
 const diagnostics=[],match=/\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}/.exec(source),name=match?.[2]??'article',options=(match?.[1]??'').split(',').map(s=>s.trim()).filter(Boolean);
 if(!Object.hasOwn(classes,name))return{classModule:null,diagnostics:['Unsupported document class: '+name],options,imports:[]};
 const classModule=(await classes[name]()).default;for(const option of options)if(!classModule.options.includes(option))diagnostics.push('Unsupported '+name+' option: '+option);
 return{classModule,diagnostics,options};
}
export async function resolveModules(source){
 const {classModule,diagnostics,options}=await resolveDocumentClass(source),loaded=new Map();
 if(!classModule)return{classModule,packages:loaded,diagnostics,options,imports:[]};
 const imports=[...source.matchAll(/\\usepackage\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}/g)].flatMap(m=>m[2].split(',').map(name=>({name:name.trim(),options:(m[1]??'').split(',').map(s=>s.trim()).filter(Boolean)})));
 async function load(request){if(loaded.has(request.name))return;if(!Object.hasOwn(packages,request.name)){diagnostics.push('Unsupported package: '+request.name);return;}const namespace=await packages[request.name](),module=namespace.default;loaded.set(request.name,{...module,mathCommands:namespace.mathCommands,parseMathCommand:namespace.parseMathCommand,requestedOptions:request.options});for(const option of request.options){const key=option.split('=')[0];if(!module.options.includes(key))diagnostics.push('Unsupported '+request.name+' option: '+option);else if(!['geometry','hyperref'].includes(request.name)&&!module.implementedOptions?.includes(key)&&option!=='final')diagnostics.push('Package option implementation pending: '+request.name+' '+option);}for(const dependency of module.dependencies??[])await load({name:dependency,options:[]});}
 for(const dependency of classModule.dependencies??[])await load({name:dependency,options:[]});
 for(const request of imports)await load(request);
 return{classModule,packages:loaded,diagnostics,options,imports};
}
export function registerModule(kind,name,loader){if(!/^[A-Za-z][A-Za-z0-9-]*$/.test(name)||typeof loader!=='function')throw Error('Invalid module registration');const target=kind==='class'?classes:kind==='package'?packages:null;if(!target||Object.hasOwn(target,name))throw Error('Module already registered or invalid kind');target[name]=loader;}
export const supportedModules={classes:Object.keys(classes),packages:Object.keys(packages)};
