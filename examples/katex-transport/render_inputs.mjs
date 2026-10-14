import {createServer} from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import katex from 'katex';
const {chromium}=await import(process.env.PLAYWRIGHT_MODULE||'/home/viktor/Projects/Cuvami/staging/node_modules/playwright/index.mjs');
const root=dirname(fileURLToPath(import.meta.url)),out=resolve(process.argv[2]);await mkdir(out,{recursive:true});
const cases=JSON.parse(await readFile(resolve(root,'cases.json')));
const server=createServer(async(req,res)=>{try{
 const path=resolve(root,'node_modules/katex/dist','.'+decodeURIComponent(req.url));
 if(!path.startsWith(resolve(root,'node_modules/katex/dist')+'/'))throw Error('path');
 const data=await readFile(path);res.setHeader('Content-Type',path.endsWith('.css')?'text/css':path.endsWith('.woff2')?'font/woff2':'application/octet-stream');res.end(data);
}catch{res.writeHead(404);res.end();}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({channel:'chrome',headless:true,args:['--disable-gpu']});
const page=await browser.newPage({viewport:{width:960,height:540},deviceScaleFactor:Number(process.env.PIXEL_RATIO||1)});
let errors=[];page.on('pageerror',e=>errors.push(String(e)));
for(const item of cases)for(const side of ['from','to']){
 const html=katex.renderToString(item[side],{displayMode:true,output:'html',throwOnError:true,strict:'error',trust:false});
 const offset=item.shift?(side==='from'?-item.shift/2:item.shift/2):0;
 await page.setContent(`<!doctype html><html><head><link rel="stylesheet" href="${base}/katex.min.css"><style>body{margin:0;background:black;color:white;width:960px;height:540px;display:grid;place-items:center}.formula{font-size:54px;transform:translateX(${offset}px)}.katex-display{margin:0}</style></head><body><div class="formula">${html}</div></body></html>`);
 await page.evaluate(()=>document.fonts.ready);
 const bounds=await page.locator('.formula').boundingBox();if(bounds.x<0||bounds.x+bounds.width>960||bounds.y<0||bounds.y+bounds.height>540)throw Error('clipped expression');
 await page.screenshot({path:resolve(out,`${item.id}-${side}.png`)});
}
await writeFile(resolve(out,'inputs.json'),JSON.stringify({katex:katex.version,viewport:[960,540],pixelRatio:Number(process.env.PIXEL_RATIO||1),cases,errors,renderer:'Chrome headless software; only PNG masks enter matching'},null,2));
await browser.close();server.close();console.log(`Rendered ${cases.length*2} KaTeX endpoints; errors: ${errors.length}`);
