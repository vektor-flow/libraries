// Independent PDF output backend. Input coordinates are layout bp (1/72 inch),
// with y downward. No text shaping, pixel rounding, atlas sampling or GPU calls.
import {pdfPngImage} from './pdf-images.mjs';
import {plotPathPdfCommands} from '../vf-plot-pdf-commands.mjs';
import {opaquePlotPathBatches} from '../vf-opaque-plot-batches.mjs';
const encoder = new TextEncoder();
const ascii = value => encoder.encode(value);
function num(value) {
  if (!Number.isFinite(value) || Math.abs(value) > 1e9) throw Error('Invalid PDF coordinate');
  // PDF accepts ordinary decimals, but not JavaScript exponent notation.
  // String retains full IEEE64 precision and avoids fixed-decimal trimming for
  // the normal coordinate range. Tiny values keep the bounded decimal path.
  if (value === 0 || Math.abs(value) >= 1e-6) return String(value);
  return value.toFixed(10).replace(/\.?0+$/, '') || '0';
}
const numbers = values => values.map(num).join(' ');
const ref = id => `${id} 0 R`;
// Hex strings keep URI/name bytes separate from PDF syntax, including brackets,
// parentheses, backslashes and Unicode in author-supplied link destinations.
const pdfString = value => '<' + [...ascii(value)].map(v => v.toString(16).padStart(2, '0')).join('') + '>';
function primitivePath(item) {
  if (item.kind === 'segment') return `0 0 m ${numbers(item.delta)} l`;
  if (item.kind === 'bezier') return `0 0 m ${numbers([...item.controls.flatMap(p => [p.x, p.y]), ...item.delta])} c`;
  if (item.kind === 'vectorrect') return `0 0 ${numbers([item.width, item.height])} re`;
  // PDF has cubic paths rather than a circle operator. Eight cubic arcs keep
  // the radial approximation below 5e-6 of the radius at any output resolution.
  const rx = item.width / 2, ry = item.height / 2, step = Math.PI / 4, k = 4 / 3 * Math.tan(step / 4);
  const commands = [`${numbers([2 * rx, ry])} m`];
  for (let i = 0; i < 8; i++) {
    const a = i * step, b = (i + 1) * step;
    commands.push(`${numbers([rx + rx*(Math.cos(a)-k*Math.sin(a)), ry + ry*(Math.sin(a)+k*Math.cos(a)), rx + rx*(Math.cos(b)+k*Math.sin(b)), ry + ry*(Math.sin(b)-k*Math.cos(b)), rx + rx*Math.cos(b), ry + ry*Math.sin(b)])} c`);
  }
  return commands.join('\n') + '\nh';
}
function concatenate(parts) {
  const result = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let offset = 0;
  for (const part of parts) { result.set(part, offset); offset += part.length; }
  return result;
}
async function compress(bytes) {
  const stream = new CompressionStream('deflate'), writer = stream.writable.getWriter();
  const output = new Response(stream.readable).arrayBuffer();
  await writer.write(bytes);
  await writer.close();
  return new Uint8Array(await output);
}
let compressionPool;
function workerCompression() {
  if (typeof Worker === 'undefined') return null;
  if (compressionPool) return compressionPool;
  const worker = new Worker(new URL('./pdf-compression-worker.mjs', import.meta.url), {type: 'module'}), pending = new Map();
  let next = 0;
  worker.onmessage = ({data}) => {
    const job = pending.get(data.id); if (!job) return;
    pending.delete(data.id);
    if (data.error) job.reject(Error(data.error)); else job.resolve(new Uint8Array(data.buffer));
  };
  worker.onerror = event => {
    event.preventDefault();
    for (const job of pending.values()) job.reject(Error(event.message || 'PDF compression worker failed'));
    pending.clear(); worker.terminate(); compressionPool = null;
  };
  compressionPool = bytes => new Promise((resolve, reject) => {
    const id = next++; pending.set(id, {resolve, reject});
    worker.postMessage({id, bytes}, [bytes.buffer]);
  });
  return compressionPool;
}
// Start the CPU worker while independent layout/font work is in progress.
export function preparePdfCompression() { workerCompression(); }
class Pdf {
  objects = [null];
  pendingStreams = [];
  constructor(metrics, useWorker, compressStream) { this.metrics = metrics; this.compress = compressStream ?? (useWorker ? workerCompression() : null); }
  reserve() { this.objects.push(null); return this.objects.length - 1; }
  add(value) { const id = this.reserve(); this.set(id, value); return id; }
  set(id, value) { this.objects[id] = typeof value === 'string' ? ascii(value) : value; }
  encodedStream(dictionary, bytes) {
    return this.add(concatenate([ascii(`<< ${dictionary} /Length ${bytes.length} >>\nstream\n`), bytes, ascii('\nendstream')]));
  }
  stream(dictionary, bytes) {
    // Small reusable glyph outlines cost more to hand to a native compression
    // stream than they save in PDF bytes. Keep these as ordinary vector streams;
    // compress larger outlines, page content and decoded image planes.
    if (dictionary.includes('/Subtype /Form')) {
      const raw = typeof bytes === 'string' ? ascii(bytes) : bytes;
      if (raw.length <= 2048) {
        if(this.metrics){this.metrics.rawFormCount++;this.metrics.rawFormBytes+=raw.length;}
        return this.encodedStream(dictionary, raw);
      }
    }
    // Reserve IDs in painting order. Compression can complete out of order
    // without changing references, object order or the final PDF bytes.
    const id = this.reserve();
    if (this.compress) {
      const output = this.compress(typeof bytes === 'string' ? ascii(bytes) : bytes);
      // Observe rejection immediately even while the synchronous page loop runs.
      output.catch(() => {});
      this.pendingStreams.push({id, dictionary, output});
    } else this.pendingStreams.push({id, dictionary, bytes});
    return id;
  }
  async completeStreams() {
    const start = this.metrics ? performance.now() : 0;
    let next = 0;
    const worker = async () => {
      while (next < this.pendingStreams.length) {
        const job = this.pendingStreams[next++], {id, dictionary, bytes} = job;
        job.bytes = null;
        const body = job.output ? await job.output : await compress(typeof bytes === 'string' ? ascii(bytes) : bytes);
        this.set(id, concatenate([ascii(`<< ${dictionary} /Length ${body.length} /Filter /FlateDecode >>\nstream\n`), body, ascii('\nendstream')]));
        if (this.metrics) this.metrics.compressedBytes += body.length;
      }
    };
    // Bound simultaneous buffers/native compression jobs even for large files.
    await Promise.all(Array.from({length: Math.min(4, this.pendingStreams.length)}, worker));
    if (this.metrics) {
      this.metrics.streamCount = this.pendingStreams.length;
      this.metrics.compressionMs = performance.now()-start;
      this.metrics.compressionWorker = !!this.compress;
    }
    this.pendingStreams.length = 0;
  }
  finish(root) {
    const parts = [ascii('%PDF-1.7\n%VKF vector PDF\n')], offsets = [0];
    let offset = parts[0].length;
    for (let id = 1; id < this.objects.length; id++) {
      if (!this.objects[id]) throw Error('Unresolved PDF object');
      offsets.push(offset);
      const object = concatenate([ascii(`${id} 0 obj\n`), this.objects[id], ascii('\nendobj\n')]);
      parts.push(object); offset += object.length;
    }
    const xref = `xref\n0 ${this.objects.length}\n0000000000 65535 f \n` + offsets.slice(1).map(n => `${String(n).padStart(10, '0')} 00000 n \n`).join('');
    parts.push(ascii(`${xref}trailer\n<< /Size ${this.objects.length} /Root ${ref(root)} >>\nstartxref\n${offset}\n%%EOF\n`));
    return concatenate(parts);
  }
}

/** Export positioned pages with reusable cubic Bezier Form XObjects.
 * images is an optional dictionary of original illustration RGBA pixels;
 * only those illustrations are raster objects, never text or complete pages.
 * Additional vector-asset paths use the same keys/paths contract as the bundle.
 * Missing outlines and unsupported items fail explicitly; no raster fallback.
 */
export async function exportVectorPdf(layout, vectors, {images = {}, defaultColor = [0, 0, 0, 1], metrics = null, compressionWorker = true, compressStream = null} = {}) {
  if (vectors?.schema !== 'vkf.pdf-vectors/1') throw Error('Unsupported PDF vector bundle');
  if (!Array.isArray(layout?.pages) || !layout.pages.length || layout.pages.length > 100) throw Error('PDF requires 1–100 layout pages');
  const start = metrics ? performance.now() : 0;
  if(metrics)Object.assign(metrics,{streamCount:0,compressionMs:0,compressedBytes:0,imageChannelMs:0,preservedPngCount:0,rawFormCount:0,rawFormBytes:0});
  const pdf = new Pdf(metrics, compressionWorker, compressStream), catalog = pdf.reserve(), tree = pdf.reserve(), resources = pdf.reserve();
  const forms = new Map(), imageObjects = new Map(), alphas = new Map(), pageIds = layout.pages.map(() => pdf.reserve());
  const paintCache = new WeakMap(), keyForms = new Map(), scales = new Map();
  function glyphMatrix(sx, sy, x, y) {
    let row = scales.get(sx);
    if (!row) scales.set(sx, row = new Map());
    let prefix = row.get(sy);
    if (!prefix) { prefix = `${num(sx)} 0 0 ${num(sy)} `; row.set(sy, prefix); }
    return prefix + num(x) + ' ' + num(y);
  }
  function annotation(item, page, pageId) {
    if (!item.target) return null;
    let action;
    if (item.target.type === 'uri') {
      if (typeof item.target.value !== 'string' || !item.target.value || /[\x00-\x1f\x7f]/.test(item.target.value)) throw Error('Invalid PDF link URI');
      const uri = item.target.value.replace(/[^\x21-\x7e]/gu, c => encodeURIComponent(c));
      action = `/A << /S /URI /URI ${pdfString(uri)} >>`;
    } else if (item.target.type === 'destination') {
      const point = layout.destinations?.[item.target.value];
      if (!point || !Number.isInteger(point.page) || !pageIds[point.page]) throw Error('Missing PDF link destination: ' + item.target.value);
      action = `/Dest [${ref(pageIds[point.page])} /XYZ ${numbers([point.x, layout.pages[point.page].height-point.y])} null]`;
    } else throw Error('Unsupported PDF link target: ' + item.target.type);
    if (!(item.width > 0 && item.height > 0)) throw Error('Invalid PDF link rectangle');
    const rect = [Math.max(0, item.x-1), Math.max(0, page.height-item.y-item.height-1), Math.min(page.width, item.x+item.width+1), Math.min(page.height, page.height-item.y+1)];
    if (rect[2] <= rect[0] || rect[3] <= rect[1]) return null;
    // The visible border, if requested, is already in the vector content. Keep
    // the interactive annotation border invisible to avoid double painting.
    return pdf.add(`<< /Type /Annot /Subtype /Link /P ${ref(pageId)} /Rect [${numbers(rect)}] /Border [0 0 0] /H /I ${action} >>`);
  }
  function colorCommands(color) {
    const cached = paintCache.get(color);
    if (cached) return cached;
    if (!Array.isArray(color) || ![3, 4].includes(color.length) || color.some(v => !Number.isFinite(v) || v < 0 || v > 1)) throw Error('Invalid PDF color');
    const alpha = color[3] ?? 1;
    if (!alphas.has(alpha)) alphas.set(alpha, {name: `A${alphas.size}`, id: pdf.add(`<< /Type /ExtGState /ca ${num(alpha)} /CA ${num(alpha)} >>`)});
    const rgb = numbers(color.slice(0, 3)), command = `${rgb} rg ${rgb} RG /${alphas.get(alpha).name} gs`;
    paintCache.set(color, command); return command;
  }
  function form(key) {
    const cached = keyForms.get(key);
    if (cached) return cached;
    const digest = vectors.keys[key];
    if (!digest || !Object.hasOwn(vectors.paths, digest)) throw Error('Missing PDF vector outline: ' + key);
    if (!forms.has(digest)) {
      const path = vectors.paths[digest];
      if (!Array.isArray(path.bounds) || path.bounds.length !== 4 || path.bounds[2] < path.bounds[0] || path.bounds[3] < path.bounds[1] || typeof path.operators !== 'string') throw Error('Invalid PDF vector: ' + key);
      // Only path construction operators from our prepared bundle are allowed.
      if (!/^(?:[\d.eE+\-\s]|re\b|[mlch]\b)*$/.test(path.operators)) throw Error('Invalid PDF path operators: ' + key);
      const id = pdf.stream(`/Type /XObject /Subtype /Form /BBox [${numbers(path.bounds)}] /Resources << >>`, path.operators + '\nf');
      forms.set(digest, {id, name: `G${forms.size}`});
    }
    const name = forms.get(digest).name;
    keyForms.set(key, name);
    return name;
  }
  // Type 3 charprocs paint the same authenticated font outlines at the same
  // packet positions. Unicode comes only from the actual shaper cluster, never
  // from a document overlay or reverse lookup of font character codes.
  const textFonts = [], textGlyphs = new Map();
  function textGlyph(item) {
    const semantic = item.textSemantic;
    if (!semantic) return null;
    const {unicode, font, code, advance} = semantic;
    if (typeof unicode !== 'string' || !unicode || !unicode.isWellFormed() ||
        typeof font !== 'string' || !Number.isInteger(code) || !Number.isFinite(advance))
      throw Error('Invalid shaped text semantics');
    const identity = JSON.stringify([item.key, unicode, font, code, advance]);
    if (textGlyphs.has(identity)) return textGlyphs.get(identity);
    let face = textFonts.at(-1);
    if (!face || face.glyphs.length === 255) {
      face = {id:pdf.reserve(), name:`T${textFonts.length}`, glyphs:[]};
      textFonts.push(face);
    }
    const glyph = {face, code:face.glyphs.length+1, item, unicode, advance};
    face.glyphs.push(glyph);textGlyphs.set(identity,glyph);return glyph;
  }
  function finishTextFonts() {
    for (const face of textFonts) {
      const chars = [], widths = [], mappings = [], bounds = [];
      for (const glyph of face.glyphs) {
        const {item,code,unicode,advance} = glyph;
        // Reuse the same validated path resource as the ordinary outline path.
        const name = form(item.key), b = vectors.paths[vectors.keys[item.key]].bounds;
        const textBounds=[b[0],-b[3],b[2],-b[1]];
        bounds.push(textBounds);widths.push(num(advance));
        const proc = pdf.stream('', `${num(advance)} 0 ${numbers(textBounds)} d1\nq 1 0 0 -1 0 0 cm /${name} Do Q`);
        chars.push(`/c${code} ${ref(proc)}`);
        let hex = '';for(let i=0;i<unicode.length;i++)hex += unicode.charCodeAt(i).toString(16).padStart(4,'0');
        mappings.push(`<${code.toString(16).padStart(2,'0')}> <${hex}>`);
      }
      const cmap = ['/CIDInit /ProcSet findresource begin','12 dict begin','begincmap',
        '/CIDSystemInfo << /Registry (VKF) /Ordering (Shaped) /Supplement 0 >> def',
        '/CMapName /VKFShaped def','/CMapType 2 def','1 begincodespacerange','<01> <ff>','endcodespacerange'];
      for(let i=0;i<mappings.length;i+=100){const chunk=mappings.slice(i,i+100);cmap.push(`${chunk.length} beginbfchar`,...chunk,'endbfchar');}
      cmap.push('endcmap','CMapName currentdict /CMap defineresource pop','end','end');
      const unicodeId=pdf.stream('',cmap.join('\n'));
      const bbox=[Math.min(...bounds.map(b=>b[0])),Math.min(...bounds.map(b=>b[1])),Math.max(...bounds.map(b=>b[2])),Math.max(...bounds.map(b=>b[3]))];
      pdf.set(face.id, `<< /Type /Font /Subtype /Type3 /Name /${face.name} /FontBBox [${numbers(bbox)}] /FontMatrix [1 0 0 1 0 0] /CharProcs << ${chars.join(' ')} >> /Encoding << /Type /Encoding /Differences [1 ${face.glyphs.map(g=>'/c'+g.code).join(' ')}] >> /FirstChar 1 /LastChar ${face.glyphs.length} /Widths [${widths.join(' ')}] /Resources << /XObject << ${[...forms.values()].map(f=>'/'+f.name+' '+ref(f.id)).join(' ')} >> >> /ToUnicode ${ref(unicodeId)} >>`);
    }
  }
  function image(name) {
    if (!imageObjects.has(name)) {
      const source = images[name] ?? images[name.replace(/\.[^.]+$/, '')];
      if (!source) throw Error('Missing PDF illustration: ' + name);
      if (source.png) {
        const png = pdfPngImage(source.png);
        if (!png) throw Error('PNG illustration requires decoded RGBA pixels: ' + name);
        const {width, height, colors, idat} = png;
        const id = pdf.encodedStream(`/Type /XObject /Subtype /Image /Width ${width} /Height ${height} /ColorSpace /${colors === 3 ? 'DeviceRGB' : 'DeviceGray'} /BitsPerComponent 8 /Interpolate false /Filter /FlateDecode /DecodeParms << /Predictor 15 /Colors ${colors} /BitsPerComponent 8 /Columns ${width} >>`, idat);
        imageObjects.set(name, {id, name: `I${imageObjects.size}`});
        if(metrics)metrics.preservedPngCount=(metrics.preservedPngCount??0)+1;
        return imageObjects.get(name).name;
      }
      const {width, height, rgba} = source;
      if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 || width * height > 16777216 || !(rgba instanceof Uint8Array || rgba instanceof Uint8ClampedArray) || rgba.length !== width * height * 4) throw Error('Invalid PDF illustration pixels: ' + name);
      const rgb = new Uint8Array(width * height * 3), alpha = new Uint8Array(width * height);
      const channelStart = metrics ? performance.now() : 0;
      let transparent = false;
      for (let i = 0, sourceAt = 0, targetAt = 0; i < alpha.length; i++, sourceAt += 4, targetAt += 3) {
        rgb[targetAt] = rgba[sourceAt]; rgb[targetAt+1] = rgba[sourceAt+1]; rgb[targetAt+2] = rgba[sourceAt+2];
        alpha[i] = rgba[sourceAt+3]; transparent ||= alpha[i] !== 255;
      }
      if(metrics)metrics.imageChannelMs+=performance.now()-channelStart;
      const mask = transparent ? pdf.stream(`/Type /XObject /Subtype /Image /Width ${width} /Height ${height} /ColorSpace /DeviceGray /BitsPerComponent 8`, alpha) : null;
      const id = pdf.stream(`/Type /XObject /Subtype /Image /Width ${width} /Height ${height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Interpolate false${mask ? ' /SMask ' + ref(mask) : ''}`, rgb);
      imageObjects.set(name, {id, name: `I${imageObjects.size}`});
    }
    return imageObjects.get(name).name;
  }
  for (const [pageIndex, page] of layout.pages.entries()) {
    if (!(page.width > 0 && page.height > 0) || !Array.isArray(page.items) || page.items.length > 50000) throw Error('Invalid PDF layout page');
    const commands = [`q 1 0 0 -1 0 ${num(page.height)} cm`], annotations = [];
    let currentPaint;
    for (const item of opaquePlotPathBatches(page.items)) {
      const paint = colorCommands(item.color ?? defaultColor);
      // Each item restores the page graphics state. Set shared paint once per
      // run rather than repeating color and alpha operators for every glyph.
      if (paint !== currentPaint) { commands.push(paint); currentPaint = paint; }
      const x = item.x, y = item.y;
      if(!Number.isFinite(x)||!Number.isFinite(y)||Math.abs(x)>1e9||Math.abs(y)>1e9)throw Error('Invalid PDF coordinate');
      if (item.kind === 'plotpath') {
        commands.push(plotPathPdfCommands(item, colorCommands));
      } else if (item.kind === 'glyph' || item.kind === 'field') {
        const name = form(item.key), sx = item.sx ?? 1, sy = item.sy ?? 1;
        if (!sx || !sy) continue;
        commands.push(`q ${glyphMatrix(sx, sy, item.x, item.y)} cm`);
        if (item.crop || item.cropX) {
          const b = vectors.paths[vectors.keys[item.key]].bounds;
          const l = Math.max(b[0], item.cropX?.[0] ?? b[0]), r = Math.min(b[2], item.cropX?.[1] ?? b[2]);
          const t = Math.max(b[1], item.crop?.[0] ?? b[1]), bottom = Math.min(b[3], item.crop?.[1] ?? b[3]);
          commands.push(`${numbers([l, t, Math.max(0, r-l), Math.max(0, bottom-t)])} re W n`);
        }
        const glyph = item.kind === 'glyph' ? textGlyph(item) : null;
        if (glyph) commands.push(`BT /${glyph.face.name} 1 Tf 1 0 0 -1 0 0 Tm <${glyph.code.toString(16).padStart(2,'0')}> Tj ET Q`);
        else commands.push(`/${name} Do Q`);
      } else if (item.kind === 'rule') {
        commands.push(`q ${numbers([item.x, item.y, item.width, item.height])} re f Q`);
      } else if (item.kind === 'link') {
        const width = item.borderWidth ?? 1;
        if (width) commands.push(`q ${num(width)} w ${numbers([item.x-1, item.y-1, item.width+2, item.height+2])} re S Q`);
        const id = annotation(item, page, pageIds[pageIndex]);
        if (id) annotations.push(id);
      } else if (item.kind === 'image') {
        const name = image(item.asset);
        // Image rows are top to bottom; compensate for PDF image space's y axis.
        commands.push(`q ${numbers([item.width, 0, 0, -item.height, item.x, item.y+item.height])} cm /${name} Do Q`);
      } else if (['segment', 'bezier', 'circle', 'vectorrect'].includes(item.kind)) {
        const width = item.lineWidth ?? 0, path = primitivePath(item);
        if (width < 0) throw Error('Invalid PDF stroke width');
        commands.push(`q ${numbers([item.sx ?? 1, 0, 0, item.sy ?? 1, item.x, item.y])} cm`);
        if (item.fill) commands.push(`${colorCommands(item.fillColor ?? item.color ?? defaultColor)} ${path} f`);
        if (width) {
          let dash = '[] 0 d 0 J';
          if (item.dash && item.dash !== 'solid') {
            const pt = 72/72.27;
            if (item.dash === 'dashed') dash = `[${numbers([3*pt, 3*pt])}] 0 d 0 J`;
            else if (['dotted', 'densely dotted', 'loosely dotted'].includes(item.dash)) dash = `[0 ${num((item.dash === 'densely dotted' ? 1 : item.dash === 'loosely dotted' ? 4 : 2)*pt + width)}] 0 d 1 J`;
            else throw Error('Unsupported PDF dash style: ' + item.dash);
          }
          commands.push(`${colorCommands(item.strokeColor ?? item.color ?? defaultColor)} ${num(width)} w ${dash} ${path} S`);
        }
        commands.push('Q');
      } else {
        throw Error('Unsupported PDF layout item: ' + item.kind + ' at ' + x + ',' + y);
      }
    }
    commands.push('Q');
    for (const item of page.links ?? []) {
      const id = annotation(item, page, pageIds[pageIndex]);
      if (id) annotations.push(id);
    }
    const contents = pdf.stream('', commands.join('\n'));
    pdf.set(pageIds[pageIndex], `<< /Type /Page /Parent ${ref(tree)} /MediaBox [0 0 ${numbers([page.width, page.height])}] /Resources ${ref(resources)} /Contents ${ref(contents)}${annotations.length ? ' /Annots [' + annotations.map(ref).join(' ') + ']' : ''} >>`);
  }
  finishTextFonts();
  pdf.set(resources, `<< /Font << ${textFonts.map(f=>`/${f.name} ${ref(f.id)}`).join(' ')} >> /XObject << ${[...forms.values(), ...imageObjects.values()].map(o => `/${o.name} ${ref(o.id)}`).join(' ')} >> /ExtGState << ${[...alphas.values()].map(o => `/${o.name} ${ref(o.id)}`).join(' ')} >> >>`);
  pdf.set(tree, `<< /Type /Pages /Count ${pageIds.length} /Kids [${pageIds.map(ref).join(' ')}] >>`);
  pdf.set(catalog, `<< /Type /Catalog /Pages ${ref(tree)} >>`);
  await pdf.completeStreams();
  const finishStart=metrics?performance.now():0,bytes=pdf.finish(catalog);
  if(metrics)Object.assign(metrics,{assemblyMs:performance.now()-finishStart,totalMs:performance.now()-start,formCount:forms.size,imageCount:imageObjects.size,objectCount:pdf.objects.length-1});
  return bytes;
}

/** Verify the lazy-loaded vector asset belongs to this exact layout mapping. */
export async function verifyVectorMapping(vectors, mappingBytes) {
  const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', mappingBytes))].map(v => v.toString(16).padStart(2, '0')).join('');
  if (vectors.mappingSha256 !== hash) throw Error('PDF vector bundle does not match the font mapping');
}
