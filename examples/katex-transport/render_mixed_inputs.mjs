// Endpoint generator only. Solver receives raster arrays, never these definitions.
import {createServer} from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import katex from 'katex';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'/home/viktor/Projects/Cuvami/staging/node_modules/playwright/index.mjs');
const root=dirname(fileURLToPath(import.meta.url)),out=resolve(process.argv[2]);await mkdir(out,{recursive:true});
const math=t=>katex.renderToString(t,{displayMode:true,output:'html',throwOnError:true,strict:'error',trust:false});
const svg=body=>`<svg width="300" height="130" viewBox="0 0 300 130" xmlns="http://www.w3.org/2000/svg" fill="white">${body}</svg>`;
const disk='<circle cx="55" cy="65" r="27"/>';
const small=body=>svg(body).replace('width="300"','width="100"').replace('viewBox="0 0 300 130"','viewBox="0 0 100 130"');
const cases=[
 {id:'10-geometry-merge',from:svg('<circle cx="95" cy="65" r="28"/><circle cx="205" cy="65" r="28"/>'),to:svg('<rect x="80" y="37" width="140" height="56" rx="16"/>')},
 {id:'11-geometry-reform',from:svg('<path d="M150 20L205 110H95Z"/>'),to:svg('<rect x="100" y="35" width="100" height="60" rx="12"/>')},
 {id:'12-ring-to-text',from:svg('<circle cx="150" cy="65" r="40" fill="none" stroke="white" stroke-width="9"/>'),to:math('D')},
 {id:'13-mixed-collect',from:`<span class="mix">${svg(disk).replace('width="300"','width="100"').replace('viewBox="0 0 300 130"','viewBox="0 0 100 130"')}${math('+x')}</span>`,to:math('2x')},
 {id:'14-mixed-split',from:math('D'),to:svg('<circle cx="95" cy="65" r="29" fill="none" stroke="white" stroke-width="9"/><path d="M185 35L225 95H165Z"/>')},
 {id:'15-nested-fraction',from:math('\\frac{\\frac{x}{2}+\\frac{x}{3}}{x}'),to:math('\\frac{5}{6}')},
 {id:'16-long-factor',from:math('a^2+ab+ac+bc'),to:math('(a+b)(a+c)')},
 {id:'18-mixed-reform',from:`<span class="mix">${math('x+')} ${small(disk)}</span>`,to:`<span class="mix">${math('x+')} ${small('<path d="M50 30L85 100H15Z"/>')}</span>`},
 {id:'17-text',from:math('\\text{Forms can change.}'),to:math('\\text{Shapes can merge.}')},
];
const server=createServer(async(req,res)=>{try{const p=resolve(root,'node_modules/katex/dist','.'+decodeURIComponent(req.url));if(!p.startsWith(resolve(root,'node_modules/katex/dist')+'/'))throw Error('path');res.end(await readFile(p));}catch{res.writeHead(404);res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({channel:'chrome',headless:true,args:['--disable-gpu']});
const page=await browser.newPage({viewport:{width:960,height:540},deviceScaleFactor:3});let errors=[];page.on('pageerror',e=>errors.push(String(e)));
for(const c of cases.filter(c=>!process.argv[3]||c.id===process.argv[3]))for(const side of ['from','to']){
 await page.setContent(`<link rel="stylesheet" href="http://127.0.0.1:${server.address().port}/katex.min.css"><style>body{margin:0;background:black;color:white;width:960px;height:540px;display:grid;place-items:center}.formula{font-size:48px}.katex-display{margin:0}.mix{display:flex;align-items:center;gap:12px}</style><div class="formula">${c[side]}</div>`);
 await page.evaluate(()=>document.fonts.ready);
 await page.locator('.formula').evaluate(el=>{const b=el.getBoundingClientRect();el.style.transform=`scale(${Math.min(1,360/b.width,190/b.height)})`;});
 const box=await page.locator('.formula').boundingBox();if(box.x<270||box.x+box.width>690||box.y<150||box.y+box.height>390)throw Error('crop clipping');
 await page.screenshot({path:resolve(out,`${c.id}-${side}.png`)});
}
await writeFile(resolve(out,'mixed-inputs.json'),JSON.stringify({katex:katex.version,cases,errors,pixelRatio:3,solverInputs:'PNG arrays only'},null,2));
await browser.close();server.close();if(errors.length)throw Error(errors.join('\n'));console.log(`Rendered ${cases.length} new pairs`);
