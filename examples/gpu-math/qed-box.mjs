// amsthm's openbox uses text-font em, default .4pt rules and centered side glue.
const pt=72/72.27;
export function qedBox(quad){
 const width=.77778*quad,height=.675*quad,rule=.4*pt,inner=.6*quad,left=(width-inner-2*rule)/2;
 return{width,height,depth:0,class:'ord',italic:0,items:[
  {kind:'rule',x:left,y:-height,width:rule,height},
  {kind:'rule',x:left+rule,y:-height,width:inner,height:rule},
  {kind:'rule',x:left+rule,y:-rule,width:inner,height:rule},
  {kind:'rule',x:left+rule+inner,y:-height,width:rule,height}
 ]};
}
