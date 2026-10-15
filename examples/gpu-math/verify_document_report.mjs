import {mkdir,writeFile} from 'node:fs/promises';
const {chromium}=await import(process.env.VKF_PLAYWRIGHT_MODULE??'playwright');
const [url,output]=process.argv.slice(2);await mkdir(output);
const browser=await chromium.launch({headless:true,executablePath:process.env.VKF_CHROMIUM,args:['--disable-gpu']});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true}),errors=[];
 page.on('pageerror',error=>errors.push(error.message));await page.goto(url);
 await page.waitForFunction(()=>document.getElementById('doc').options.length>0);
 const report=await page.evaluate(()=>fetch('./report.json').then(response=>response.json()));let images=0,missingViews=0;
 for(const [index,doc] of report.documents.entries()){
  await page.locator('#doc').selectOption(String(index));
  for(const p of doc.pages){
   await page.locator('#page').selectOption(String(p.page));
   for(const view of ['reference','native','difference','local-error']){
    await page.locator('#view').selectOption(view);
    const missing=view==='reference'?p.page>doc.referencePages:p.page>doc.nativePages||view!=='native'&&p.page>doc.referencePages;
    if(missing){if(!await page.locator('#image').isHidden())throw Error('Missing page shown as measured output');missingViews++;}
    else{await page.waitForFunction(()=>{const image=document.getElementById('image');return !image.hidden&&image.complete&&image.naturalWidth>0;});images++;}
   }
  }
 }
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),timings=await page.locator('#timings').textContent();
 if(/NaN|undefined|Infinity/.test(timings))throw Error('Unmeasured timings shown as numbers');
 await page.locator('#doc').selectOption('0');await page.locator('#page').selectOption('1');await page.locator('#view').selectOption('reference');
 await page.screenshot({path:output+'/phone-report.png'});
 const result={documents:report.documents.length,images,missingViews,overflow,errors,accepted:report.accepted,scope:'Report navigation only; browser GPU disabled. Every present and missing full-page view checked.'};
 await writeFile(output+'/report-ui.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
 if(overflow||errors.length)throw Error('Document report failed');
}finally{await browser.close();}
