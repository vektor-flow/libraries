export default {name:'amsmath',kind:'package',dependencies:[],options:['fleqn','leqno','intlimits','nointlimits','sumlimits','nosumlimits'],commands:['frac','dfrac','tfrac','binom','dbinom','tbinom','genfrac','operatorname','boxed','overset','underset','text','tag','notag','nonumber','eqref'],environments:['equation','equation*','align','align*','aligned','split','gather','gather*','gathered','multline','multline*','cases','matrix','pmatrix','bmatrix','Bmatrix','vmatrix','Vmatrix','smallmatrix']};

export const mathCommands=["\\binom", "\\dbinom", "\\tbinom", "\\genfrac", "\\pmod", "\\pod", "\\mod", "\\bmod", "\\tag", "\\notag", "\\nonumber", "\\operatorname"];
export function parseMathCommand(raw,{take,argument,rawGroup,optionalRaw,parseText,repair,depth,star:takeStar}){
  if(['\\binom','\\dbinom','\\tbinom'].includes(raw)){take();return{type:'frac',num:argument(depth),den:argument(depth),thickness:'0pt',left:'(',right:')',style:raw==='\\dbinom'?0:raw==='\\tbinom'?1:null};}
  if(raw==='\\genfrac'){take();const left=rawGroup()||'.',right=rawGroup()||'.',thickness=rawGroup(),styleRaw=rawGroup();if(styleRaw&&!/^[0-3]$/.test(styleRaw))repair('Unsupported fraction style');return{type:'frac',left,right,thickness,style:/^[0-3]$/.test(styleRaw)?Number(styleRaw):null,num:argument(depth),den:argument(depth)};}
  if(['\\pmod','\\pod','\\mod','\\bmod'].includes(raw)){take();return{type:'mod',name:raw.slice(1),children:raw==='\\bmod'?[]:argument(depth)};}
  if(raw==='\\notag'||raw==='\\nonumber'){take();return{type:'space',mu:0,noNumber:true};}
  if(raw==='\\tag'){take();const star=takeStar();return{type:'tag',star,children:parseText(rawGroup(),depth)};}
  if(raw==='\\operatorname'){take();const operatorLimits=takeStar();return{type:'textflow',children:parseText(rawGroup(),depth),class:'op',operatorLimits};}
 return null;
}
