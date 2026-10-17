// CPU-only lossless compression, overlapped with main-thread PDF construction.
const queue = [];
let active = 0;
function drain() {
  while (active < 4 && queue.length) {
    const {id, bytes} = queue.shift(); active++;
    (async () => {
      try {
        const stream = new CompressionStream('deflate'), writer = stream.writable.getWriter();
        const output = new Response(stream.readable).arrayBuffer();
        await writer.write(bytes); await writer.close();
        const buffer = await output;
        self.postMessage({id, buffer}, [buffer]);
      } catch (error) { self.postMessage({id, error: error.message}); }
      finally { active--; drain(); }
    })();
  }
}
self.onmessage = event => { queue.push(event.data); drain(); };
