import { createScreenSpaceSimplexRenderer } from 'vektor-flow/web/vf-ui/geom/vf-screen-simplex-renderer.mjs';

export function createAntialiasedScreenSpaceRenderer(
  canvas,
  createRenderer = createScreenSpaceSimplexRenderer,
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
  return createRenderer(antialiasedCanvas, options);
}
