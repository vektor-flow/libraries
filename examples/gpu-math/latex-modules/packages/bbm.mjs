export const mathCommands=['\\mathbbm','\\mathbbmss','\\mathbbmtt'];
export function parseMathCommand(raw,{take,argument,depth}){take();return{type:'font',name:raw.slice(1),children:argument(depth)};}
export default {name:'bbm',kind:'package',dependencies:[],options:[],commands:['mathbbm','mathbbmss','mathbbmtt']};
