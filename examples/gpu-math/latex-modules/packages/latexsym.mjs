export const mathCommands=['\\mho','\\Join','\\Box','\\Diamond','\\leadsto','\\sqsubset','\\sqsupset','\\lhd','\\unlhd','\\rhd','\\unrhd'];
export function parseMathCommand(raw,{take}){take();return{type:'glyph',token:'@latexsym:'+raw};}
export default {name:'latexsym',kind:'package',dependencies:[],options:[],commands:mathCommands,scope:'Native regular lasy symbols; bold symbol fonts remain unsupported.'};
