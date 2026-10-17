// The independent document flow implements bounded theorem/proof environments.
export const mathCommands=['\\qed','\\qedhere','\\pushQED','\\popQED'];
export function parseMathCommand(raw,{take,rawArgument,parseMath}){
 take();if(raw==='\\pushQED')return{type:'qedpush',children:parseMath(rawArgument())};
 return{type:raw==='\\popQED'?'qedpop':raw==='\\qedhere'?'qedhere':'qed'};
}
export default {name:'amsthm',dependencies:[],options:[],features:['newtheorem','theoremstyle','proof']};
