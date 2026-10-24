// PNG's noninterlaced RGB/gray IDAT stream already uses PDF-compatible lossless
// deflate and row predictors. Preserve it instead of decoding/recompressing it.
// Transparency, palettes, higher bit depths and colour-managed PNGs use the
// existing decoded RGBA path, preserving that path's colour/alpha behavior.
export function pdfPngImage(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 45) return null;
  if (![137,80,78,71,13,10,26,10].every((n,i) => bytes[i] === n)) return null;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let width, height, colors, ended = false, header = false, dataEnded = false;
  const chunks = [];
  for (let at = 8; at + 12 <= bytes.length;) {
    const length = view.getUint32(at), type = String.fromCharCode(...bytes.subarray(at+4, at+8));
    if (length > bytes.length-at-12) return null;
    if (!header && (type !== 'IHDR' || length !== 13)) return null;
    if (type === 'IHDR') {
      if (header) return null;
      header = true; width = view.getUint32(at+8); height = view.getUint32(at+12);
      const depth = bytes[at+16], kind = bytes[at+17];
      if (!width || !height || width*height > 16777216 || depth !== 8 || ![0,2].includes(kind) || bytes[at+18] || bytes[at+19] || bytes[at+20]) return null;
      colors = kind === 2 ? 3 : 1;
    } else if (type === 'IDAT') {
      if (dataEnded) return null;
      chunks.push(bytes.subarray(at+8, at+8+length));
    } else {
      if (chunks.length) dataEnded = true;
      if (['tRNS','iCCP','sRGB','gAMA','cHRM','cICP','mDCV','cLLI','acTL'].includes(type)) return null;
      if (type === 'IEND') { if (length || at+12 !== bytes.length) return null; ended = true; break; }
      // Reject unknown critical chunks rather than guessing their semantics.
      if (type[0] === type[0].toUpperCase() && type !== 'PLTE') return null;
    }
    at += length+12;
  }
  if (!ended || !chunks.length) return null;
  const idat = new Uint8Array(chunks.reduce((n,c) => n+c.length, 0));
  let at = 0; for (const chunk of chunks) { idat.set(chunk, at); at += chunk.length; }
  return {width, height, colors, idat};
}
