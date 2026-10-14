/** Bounded, explicit siunitx-compatible input subset; no package executes at runtime. */
const prefixes={quetta:'Q',ronna:'R',yotta:'Y',zetta:'Z',exa:'E',peta:'P',tera:'T',giga:'G',mega:'M',kilo:'k',hecto:'h',deca:'da',deci:'d',centi:'c',milli:'m',micro:'@micro',nano:'n',pico:'p',femto:'f',atto:'a',zepto:'z',yocto:'y',ronto:'r',quecto:'q'};
const units={m:'m',s:'s',A:'A',K:'K',mol:'mol',cd:'cd',g:'g',kg:'kg',km:'km',mm:'mm',cm:'cm',um:'@microMetre',nm:'nm',Hz:'Hz',kHz:'kHz',MHz:'MHz',N:'N',Pa:'Pa',J:'J',W:'W',V:'V',L:'L',metre:'m',meter:'m',second:'s',ampere:'A',kelvin:'K',mole:'mol',candela:'cd',gram:'g',kilogram:'kg',radian:'rad',steradian:'sr',hertz:'Hz',newton:'N',pascal:'Pa',joule:'J',watt:'W',coulomb:'C',volt:'V',farad:'F',ohm:'@ohm',siemens:'S',weber:'Wb',tesla:'T',henry:'H',degreeCelsius:'@degreeCelsius',celsius:'@degreeCelsius',lumen:'lm',lux:'lx',becquerel:'Bq',gray:'Gy',sievert:'Sv',katal:'kat',litre:'L',liter:'L',minute:'min',hour:'h',day:'d',tonne:'t',hectare:'ha',electronvolt:'eV',dalton:'Da',angstrom:'@angstrom',bar:'bar',percent:'@percent',degree:'@degree',arcminute:'@degreeMinute',arcsecond:'@degreeSecond',astronomicalunit:'au',neper:'Np',bel:'B',decibel:'dB'};
const glyph=token=>({type:'glyph',token}),hole=()=>({type:'hole'}),roman=text=>({type:'text',text,class:'ord'}),space=()=>({type:'space',mu:3});
function letters(value){if(value==='@microMetre')return[glyph('@unit:micro'),roman('m')];if(value==='@degreeMinute')return[glyph('@unit:arcminute')];if(value==='@degreeSecond')return[glyph('@unit:arcsecond')];if(value==='@degreeCelsius')return[glyph('@unit:degree'),roman('C')];return value.startsWith('@')?[glyph('@unit:'+value.slice(1))]:[roman(value)];}
export function unitOptions(raw,repair){const out={perMode:'power',group:true,decimal:'.'};
 for(const option of raw.split(/,(?![^{}]*})/).filter(Boolean)){const [key,v]=option.split('=');const value=(v??'').trim().replace(/^\{|\}$/g,'');
  if(key.trim()==='per-mode'&&['power','symbol','fraction','reciprocal'].includes(value))out.perMode=value==='reciprocal'?'power':value;
  else if(key.trim()==='group-digits'&&['true','false','all','none'].includes(value))out.group=!['false','none'].includes(value);
  else if(key.trim()==='output-decimal-marker'&&['.',','].includes(value))out.decimal=value;
  else repair('Unsupported unit option: '+key.trim());
 }return out;
}
export function numberNodes(raw,options,repair){
 const text=raw.trim().replace(/\s/g,'');if(!text){repair('Empty number placeholder');return[hole()];}
 const match=/^([+-]?)(\d*(?:[.,]\d*)?)(?:[eE]([+-]?\d*))?$/.exec(text);
 if(!match||!/[0-9]/.test(match[2])){repair('Unfinished or unsupported number');return[hole()];}
 let [integer,fraction]=match[2].replace(',','.').split('.');if(!integer)integer='0';let digits=integer;
 const out=[];if(match[1])out.push(glyph(match[1]));
 const group=parts=>{for(let i=0;i<parts.length;i++){if(i)out.push(space());out.push(roman(parts[i]));}};
 if(options.group&&digits.length>=5){const first=digits.length%3||3;group([digits.slice(0,first),...digits.slice(first).match(/.{1,3}/g)]);}else out.push(roman(digits));
 if(fraction!==undefined){out.push({...glyph(options.decimal),class:'ord'});if(options.group&&fraction.length>=5)group(fraction.match(/.{1,3}/g));else if(fraction)out.push(roman(fraction));}
 if(match[3]!==undefined){out.push(glyph('\\times'));const exponent=match[3];if(!/^[+-]?\d+$/.test(exponent))repair('Empty exponent placeholder');out.push({type:'group',unit:true,children:[roman('10')],sup:/^[+-]?\d+$/.test(exponent)?[roman(exponent)]:[hole()]});}
 return out;
}
export function unitNodes(raw,options,repair){
 const tokens=raw.match(/\\[a-zA-Z]+|\\.|[+-]?\d+|[A-Za-z]+|[^\s]/g)??[];const factors=[];let prefix=[],inverse=false,nextPower=1;
 const power=()=>{let value='';if(tokens[0]==='{'){tokens.shift();while(tokens.length&&tokens[0]!=='}')value+=tokens.shift();if(tokens[0]==='}')tokens.shift();else repair('Inferred a unit power closing brace');}else value=tokens.shift()??'';
  if(!/^[+-]?\d+$/.test(value)||value.length>8){repair('Empty unit power placeholder');return null;}return Number(value);
 };
 for(let i=0;tokens.length&&i<3000;i++){
  const token=tokens.shift(),name=token.startsWith('\\')?token.slice(1):token;
  if(name==='per'){inverse=true;continue;}if(token==='/'){factors.push({nodes:[glyph('/')],power:1,slash:true});continue;}
  if(['squared','cubed','tothe'].includes(name)||token==='^'){const exponent=name==='squared'?2:name==='cubed'?3:power();const f=factors.at(-1);if(f)f.power=exponent===null?null:(f.power<0?-1:1)*exponent;else{repair('Missing unit before power');factors.push({nodes:[hole()],power:exponent});}continue;}
  if(['square','cubic','raiseto'].includes(name)){nextPower=name==='square'?2:name==='cubic'?3:power();continue;}
  if(prefixes[name]!==undefined){prefix.push(...letters(prefixes[name]));continue;}
  if(['.','*','\\,','\\;','~'].includes(token))continue;
  let nodes;
  if(units[name]!==undefined)nodes=letters(units[name]);
  else if(/^[a-zA-Z0-9]+$/.test(token))nodes=[roman(token)];
  else if(token==='µ'||token==='μ')nodes=letters('@micro');
  else if(token==='Ω')nodes=letters('@ohm');
  else if(token==='°')nodes=letters('@degree');
  else{repair('Unfinished or unsupported unit: '+token);nodes=[hole()];}
  factors.push({nodes:[...prefix,...nodes],power:nextPower===null?null:(inverse?-1:1)*nextPower});prefix=[];inverse=false;nextPower=1;
 }
 if(prefix.length||inverse||nextPower!==1){repair('Empty unit operand placeholder');factors.push({nodes:[...prefix,hole()],power:inverse?-1:nextPower});}
 if(!factors.length){repair('Empty unit placeholder');return[hole()];}
 const join=(items,positive=false)=>items.flatMap((f,i)=>{const p=positive?Math.abs(f.power):f.power;return[...(i&&!f.slash&&!items[i-1].slash?[space()]:[]),{type:'group',unit:true,children:f.nodes,...(p!==1?{sup:p===null?[hole()]:[roman(String(p))]}:{})}];});
 if(options.perMode!=='power'&&factors.some(f=>f.power<0)){
  const numerator=join(factors.filter(f=>!(f.power<0))),denominator=join(factors.filter(f=>f.power<0),true);
  if(options.perMode==='fraction')return[{type:'frac',num:numerator.length?numerator:[roman('1')],den:denominator,style:null}];
  return[...numerator,glyph('/'),...(denominator.length>1?[{type:'delimited',left:'(',right:')',children:denominator,scalable:false}]:denominator)];
 }return join(factors);
}
