import {exceptions} from '../core/ams-hyphenation.mjs';
// Class dimensions and spacing from amsart.cls; independent of author input.
const pt=72/72.27;
export default {name:'amsart',kind:'class',dependencies:['amsmath','amsthm','amsfonts'],
 options:['8pt','9pt','10pt','11pt','12pt','a4paper','letterpaper','draft','final','oneside','twoside'],
 configure(options){
  const requested=options.find(o=>/^\d+pt$/.test(o))??'10pt',size=Number(requested.slice(0,-2)),nativeSize=size===11?10.95:size;
  const a4=options.includes('a4paper'),paperWidth=a4?210*72/25.4:612,paperHeight=a4?297*72/25.4:792,fullHeight=(a4?54.5:50.5)*12*pt,lineHeight=(size+2)*pt;
  return{lineSkipLimit:pt,lineSkip:pt,mathJot:.25*lineHeight,maxDepth:4*pt,penalties:{club:10000,widow:10000,broken:10000},hyphenationExceptions:exceptions,fontProfile:'amsart-'+size,fontSize:nativeSize*pt,paperWidth,paperHeight,logicalPaperWidth:paperWidth,logicalPaperHeight:paperHeight,textWidth:360*pt,textHeight:fullHeight-22*pt,left:Math.max(36,(paperWidth-360*pt)/2),top:Math.max(36,(paperHeight-fullHeight)/2)+22*pt,paragraphIndent:12*pt,lineHeight,
   title:{spaceScale:1.3,firstBaseline:42*pt,lineHeight,after:30*pt-10*pt},author:{lineHeight:12*pt,after:20*pt},
   section:{before:.7*lineHeight,after:.5*lineHeight,lineHeight,align:'center'},subsection:{before:.5*lineHeight,after:0,lineHeight,runIn:true},subsubsection:{before:.5*lineHeight,after:0,lineHeight,runIn:true},
   abstract:{margin:36*pt,lineHeight:12*pt,font:'abstract'},bibItemSep:0,displaySkip:.35*lineHeight,shortDisplaySkip:.175*lineHeight,footnoteLeading:12*pt,footnoteSkip:7*pt,footerOffset:12*pt,headerOffset:14*pt};
 }};
