export default {name:'float',kind:'package',dependencies:[],options:[],commands:['newfloat','floatname','floatstyle'],environments:[]};
export function floatDeclarations(source){
 const floats=new Map();
 for(const m of source.matchAll(/\\newfloat\s*\{([A-Za-z]+)\}\s*\{([htbp!H]+)\}\s*\{([^{}]+)\}\s*(?:\[([A-Za-z]+)\])?/g))floats.set(m[1],{name:m[1],placement:m[2],within:m[4],title:m[1],count:0});
 for(const m of source.matchAll(/\\floatname\s*\{([A-Za-z]+)\}\s*\{([^{}]+)\}/g))if(floats.has(m[1]))floats.get(m[1]).title=m[2];
 return floats;
}
