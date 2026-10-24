import {createSharedAreaRenderer} from './vf-shared-area-renderer.mjs';

export function createAntialiasedScreenSpaceRenderer(
  canvas,
  createRenderer = createSharedAreaRenderer,
  options = {}
) {
  const antialiasedCanvas = new Proxy(canvas, {
    get(target, property) {
      if (property === 'getContext') {
        return (kind, options) => kind === 'webgpu'
          ? null
          : target.getContext(kind, kind === 'webgl2'
            ? { ...(options || {}), antialias: true }
            : options);
      }
      const value = Reflect.get(target, property, target);
      return typeof value === 'function' ? value.bind(target) : value;
    },
    set(target, property, value) {
      return Reflect.set(target, property, value, target);
    }
  });
  const renderer=createRenderer(antialiasedCanvas, options);
  let redraw=()=>{},destroyed=false;
  return Object.freeze({...renderer,
    get backend(){return renderer.backend;},
    setScene(scene){renderer.setScene(scene);redraw=()=>renderer.setScene(scene);},
    setPackedVertices(vertices,dirtyRange=null){
      renderer.setPackedVertices(vertices,dirtyRange);
      redraw=()=>renderer.setPackedVertices(vertices);
    },
    // Re-render the committed vector triangles with explicit area coverage.
    // Redraw and read synchronously in one task: no preserved framebuffer,
    // seed renderer, alternative geometry, or timing/arena evaluation is used.
    capturePNG(){
      if(destroyed)throw Error('plot renderer is destroyed');
      if(typeof canvas.toDataURL!=='function')throw Object.assign(Error('PLOT_PNG_READBACK_UNAVAILABLE'),{status:'BLOCKED'});
      redraw();
      const url=canvas.toDataURL('image/png');
      if(!url.startsWith('data:image/png;base64,')||url.length<=22)throw Object.assign(Error('PLOT_PNG_READBACK_EMPTY'),{status:'FAIL'});
      return url;
    },
    destroy(){if(destroyed)return;destroyed=true;redraw=()=>{};renderer.destroy();}
  });
}
