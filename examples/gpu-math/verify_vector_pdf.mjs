// Browser integration check with WebGPU disabled. All files are served by the
// test route; no web server, TeX process, atlas upload or hardware GPU is used.
import assert from 'node:assert/strict';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {dirname, resolve, extname, basename} from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium} = await import(process.env.VKF_PLAYWRIGHT_MODULE ?? 'playwright');
const root = dirname(fileURLToPath(import.meta.url));
const output = resolve(process.argv[2]);
await mkdir(output, {recursive: true});
const softwarePreview = process.env.VKF_PDF_SOFTWARE_PREVIEW === '1';
if(softwarePreview && !process.env.VK_ICD_FILENAMES?.includes('swiftshader'))throw Error('Explicit SwiftShader ICD required');
const browser = await chromium.launch({headless: true, executablePath: process.env.VKF_CHROMIUM,
  args: softwarePreview ? ['--enable-unsafe-webgpu','--use-webgpu-adapter=swiftshader','--use-vulkan=swiftshader','--use-angle=vulkan','--enable-features=Vulkan','--disable-vulkan-surface','--no-sandbox'] : ['--disable-gpu', '--disable-webgpu', '--no-sandbox']});
try {
  const page = await browser.newPage({acceptDownloads: true, viewport: {width: 390, height: 844}});
  if(!softwarePreview)await page.addInitScript(() => Object.defineProperty(navigator, 'gpu', {value: undefined}));
  const errors = [], requested = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    const path = decodeURIComponent(new URL(route.request().url()).pathname);
    requested.push(path);
    if (!path.startsWith('/typing-demo/')) return route.abort();
    const relative = path.slice('/typing-demo/'.length);
    if (relative.includes('..')) return route.abort();
    let bytes;
    try { bytes = await readFile(resolve(root, 'typing-demo', relative)); }
    catch { try { bytes = await readFile(resolve(root, relative)); } catch { return route.fulfill({status: 404, body: ''}); } }
    const contentType = {'.html': 'text/html', '.mjs': 'text/javascript', '.json': 'application/json'}[extname(path)] ?? 'application/octet-stream';
    await route.fulfill({status: 200, contentType, body: bytes});
  });
  await page.goto('http://localhost:8731/typing-demo/document.html');
  await page.waitForFunction(() => (window.documentInitError || window.documentResult) && !document.getElementById('export-pdf').disabled);
  if(softwarePreview){assert.equal(await page.evaluate(() => window.documentInitError), undefined);assert.match(await page.evaluate(() => window.documentBackend), /SwiftShader/i);}
  else{assert.match(await page.evaluate(() => window.documentInitError), /WebGPU/);assert.ok(!requested.some(p => /atlas|draw\.wgsl|pdf-vectors/.test(p)), 'Fonts are lazy; export does not load GPU assets');}
  await page.locator('#navigation').click();
  const pending = page.waitForEvent('download');
  await page.locator('#export-pdf').click();
  const download = await pending;
  await download.saveAs(resolve(output, 'example.pdf'));
  await page.waitForFunction(() => document.getElementById('notice').textContent.startsWith('Vector PDF exported'));
  await page.screenshot({path: resolve(output, 'phone.png')});
  const notice = await page.locator('#notice').textContent();
  assert.deepEqual(errors, []);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  // Regression: unsupported draft geometry must show an error, not download
  // a raster substitute or silently omit the missing atom.
  await page.locator('#document').fill(String.raw`\documentclass{article}\begin{document}$\unknowncommand$\end{document}`);
  await page.locator('#navigation').click();
  await page.locator('#export-pdf').click();
  await page.waitForFunction(() => document.getElementById('notice').textContent.startsWith('PDF export failed:'));
  const failure = await page.locator('#notice').textContent();
  assert.match(failure, /Unsupported PDF layout item/);
  if(!softwarePreview)assert.ok(!requested.some(p => /atlas|draw\.wgsl/.test(p)));
  const linkSource = await readFile(resolve(root, 'tests/pdf-links.tex'), 'utf8');
  await page.locator('#document').fill(linkSource);
  if(!await page.locator('#navigation').evaluate(element => element.open))await page.locator('#navigation').click();
  const linkDownload = page.waitForEvent('download');
  await page.locator('#export-pdf').click();
  await (await linkDownload).saveAs(resolve(output, 'links.pdf'));
  await page.waitForFunction(() => document.getElementById('notice').textContent.startsWith('Vector PDF exported'));
  const linkLayout = await page.evaluate(async source => (await window.exportDocumentPdf(source)).layout, linkSource);
  await writeFile(resolve(output, 'links-layout.json'), JSON.stringify(linkLayout));
  assert.deepEqual(linkLayout.diagnostics, []);
  assert.equal(linkLayout.pages.length, 3);
  // Optional complete local corpus case (original files, unchanged source).
  if (process.argv[3]) {
    const corpus = resolve(process.argv[3]), record = JSON.parse(await readFile(resolve(corpus, 'sources.json')))[0];
    await page.evaluate(() => window.clearDocumentProject());
    for (const name of Object.keys(record.files)) {
      const bytes = await readFile(resolve(corpus, record.name, 'original', name));
      if (/\.png$/.test(name)) await page.evaluate(async ({name, base64}) => window.addDocumentAsset(name, base64), {name, base64: bytes.toString('base64')});
      else if (/\.(tex|bbl|bib|m|txt)$/.test(name)) await page.evaluate(({name, text}) => window.addDocumentFile(name, text), {name, text: bytes.toString()});
    }
    for (const name of Object.keys(record.preparedAssets)) {
      const spec = JSON.parse(await readFile(resolve(output, basename(name, '.pdf'), 'asset.json')));
      await page.evaluate(async ({name, spec}) => window.addDocumentVectorAsset(name, spec, ''), {name, spec});
    }
    // Match the original document's declared historical build context. This is
    // supplied by the project harness, not a reference page or glyph position.
    const source = await readFile(resolve(corpus, record.name, 'original', record.entry), 'utf8');
    const buildContext = {...record.buildContext, entry: record.entry, jobName: record.entry.replace(/\.tex$/, '')};
    const result = await page.evaluate(async ({source, buildContext}) => {
      const result = await window.exportDocumentPdf(source, {buildContext});
      let binary = '';
      for (let i = 0; i < result.bytes.length; i += 32768) binary += String.fromCharCode(...result.bytes.subarray(i, i + 32768));
      return {pages: result.pages, diagnostics: result.diagnostics, layout: result.layout, base64: btoa(binary)};
    }, {source, buildContext});
    assert.equal(result.pages, 39);
    await writeFile(resolve(output, 'full-paper.pdf'), Buffer.from(result.base64, 'base64'));
    await writeFile(resolve(output, 'full-paper-layout.json'), JSON.stringify(result.layout));
    await writeFile(resolve(output, 'full-paper-export.json'), JSON.stringify({pages: result.pages, diagnostics: result.diagnostics}, null, 2));
  }
  await writeFile(resolve(output, 'browser.json'), JSON.stringify({backend: softwarePreview ? 'SwiftShader preview and vector PDF export' : 'WebGPU disabled; headless browser PDF export', notice, failure, errors, requested}, null, 2));
  console.log(JSON.stringify({notice, errors, output}));
} finally { await browser.close(); }
