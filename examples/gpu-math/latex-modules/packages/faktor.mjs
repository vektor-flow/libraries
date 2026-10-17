export const mathCommands=['\\faktor'];
export function parseMathCommand(raw,{take,optionalRaw,rawArgument,parseMath}){
 take();const modifier=optionalRaw()??'',numerator=rawArgument(),denominator=rawArgument();
 return{type:'quotient',num:parseMath(modifier+'{'+numerator+'}'),den:parseMath(modifier+'{'+denominator+'}')};
}
export default {name:'faktor',kind:'package',dependencies:['amssymb'],options:[],commands:['faktor'],
 scope:'Native style-preserving raised numerator and lowered denominator with AMS diagonal slash and mu kerns.'};
