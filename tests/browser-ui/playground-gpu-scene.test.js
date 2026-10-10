import { describe, expect, it, vi } from 'vitest';

import { createRetainedGeometryScene } from '../../browser-ui/vf-retained-geometry-scene.mjs';

describe('playground GPU scene', () => {
  it('renders arrow heads as filled triangles', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.arrow('all', 'axis:x', { position: [10, 5], tangent: [1, 0] }, '#ff0000', 1);
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    expect(packed.length).toBe(18);
  });

  it('retains equivalent records across unchanged frames', () => {
    const setPackedVertices = vi.fn();
    const scene = createRetainedGeometryScene();
    const render = () => {
      scene.beginFrame();
      scene.path('all', 'edge:e0', [[0, 0], [10, 0]], 2, [
        { offset: 0, color: '#ff0000' },
        { offset: 1, color: '#0000ff' }
      ]);
      scene.selectionContour('all', 'edge:e0', [[0, 0], [10, 0]], '#00ffff', 1, {
        selectionRadius: 4,
        ringWidth: 2
      });
      return scene.commit({ setPackedVertices });
    };

    expect(render()).toBe(true);
    expect(render()).toBe(false);
    expect(setPackedVertices).toHaveBeenCalledTimes(1);
  });

  it('forces a full retained-scene upload after lifecycle invalidation', () => {
    const setPackedVertices = vi.fn();
    const scene = createRetainedGeometryScene();
    const renderer = { setPackedVertices };
    scene.beginFrame();
    scene.path('all', 'axis:x', [[0, 0], [10, 0]], 1, [
      { offset: 0, color: '#ffffff' },
      { offset: 1, color: '#ffffff' }
    ]);
    expect(scene.commit(renderer)).toBe(true);
    expect(scene.commit(renderer)).toBe(false);

    scene.invalidate();

    expect(scene.commit(renderer)).toBe(true);
    expect(setPackedVertices).toHaveBeenCalledTimes(2);
  });

  it('commits coordinate overlays after base geometry', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.primitive('all', 'axis', {
      kind: 'edge', from: [0, 0], to: [10, 0], width: 2, color: '#00ff00'
    }, { overlay: true });
    scene.primitive('all', 'base', {
      kind: 'edge', from: [0, 0], to: [10, 0], width: 2, color: '#ff0000'
    });
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    const lastColor = Array.from(packed.slice(-4, -1));
    expect(lastColor).toEqual([0, 1, 0]);
  });

  it('commits edge and vertex selection after coordinate overlays', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.primitive('all', 'selection', {
      kind: 'edge', from: [0, 0], to: [10, 0], width: 2, color: '#0000ff'
    }, { selection: true });
    scene.primitive('all', 'axis', {
      kind: 'edge', from: [0, 0], to: [10, 0], width: 2, color: '#00ff00'
    }, { overlay: true });
    scene.primitive('all', 'base', {
      kind: 'edge', from: [0, 0], to: [10, 0], width: 2, color: '#ff0000'
    });
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    expect(Array.from(packed.slice(-4, -1))).toEqual([0, 0, 1]);
  });

  it('always commits faces before edges and vertices regardless of enqueue order', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.primitive('all', 'vertex', {
      kind: 'vertex', center: [5, 5], radius: 2, segments: 8, color: '#0000ff'
    });
    scene.primitive('all', 'edge', {
      kind: 'edge', from: [0, 0], to: [10, 0], width: 2, color: '#00ff00'
    });
    scene.primitive('all', 'face', {
      kind: 'face', points: [[0, 0], [10, 0], [0, 10]], color: '#ff0000'
    });
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    const colors = Array.from({ length: packed.length / 6 }, (_, index) => (
      Array.from(packed.slice(index * 6 + 2, index * 6 + 5)).join(',')
    ));
    expect(colors.indexOf('1,0,0')).toBeLessThan(colors.indexOf('0,1,0'));
    expect(colors.indexOf('0,1,0')).toBeLessThan(colors.indexOf('0,0,1'));
  });

  it('closes edge selection contours with semicircular end caps', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.selectionContour('all', 'edge:e0', [[0, 0], [10, 0]], '#00ffff', 1, {
      selectionRadius: 4,
      ringWidth: 2
    });
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    const xs = Array.from({ length: packed.length / 6 }, (_, index) => packed[index * 6]);
    expect(Math.min(...xs)).toBeLessThanOrEqual(-3.9);
    expect(Math.max(...xs)).toBeGreaterThanOrEqual(13.9);
  });

  it('rounds every corner of a closed face selection contour', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.selectionContour(
      'all',
      'face:f0',
      [[0, 0], [10, 0], [0, 10], [0, 0]],
      '#00ffff',
      1,
      { selectionRadius: 4, ringWidth: 2 }
    );
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    // A closed face has three exterior offset segments plus one exterior arc
    // per corner. The opposite side is only valid for an open edge capsule.
    expect(packed.length).toBe(972);
  });

  it('places a closed face contour and its corner arcs outside the polygon winding', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.selectionContour(
      'all',
      'face:f0',
      [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
      '#00ffff',
      1,
      { selectionRadius: 4, ringWidth: 2 }
    );
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    const xs = Array.from({ length: packed.length / 6 }, (_, index) => packed[index * 6]);
    const ys = Array.from({ length: packed.length / 6 }, (_, index) => packed[index * 6 + 1]);
    expect(Math.min(...xs)).toBeLessThan(-3.5);
    expect(Math.max(...xs)).toBeGreaterThan(13.5);
    expect(Math.min(...ys)).toBeLessThan(-3.5);
    expect(Math.max(...ys)).toBeGreaterThan(13.5);
  });

  it('preserves internal colormap stops on a straight GPU edge', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.path('all', 'edge:e0', [[0, 0], [10, 0]], 2, [
      { offset: 0, color: '#ff0000' },
      { offset: 0.5, color: '#00ff00' },
      { offset: 1, color: '#0000ff' }
    ]);
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    const colors = Array.from({ length: packed.length / 6 }, (_, index) => (
      Array.from(packed.slice(index * 6 + 2, index * 6 + 5))
    ));
    expect(packed.length).toBeGreaterThan(36);
    expect(colors).toContainEqual([0, 1, 0]);
  });

  it('queues shaded sphere and tube impostors for 3D geometry', () => {
    let packed;
    const scene = createRetainedGeometryScene();
    scene.beginFrame();
    scene.sphereImpostor('all', 'vertex:v0', [10, 10], 5, '#6699cc');
    scene.tubeImpostor('all', 'edge:e0', [[0, 20], [10, 20]], 4, [
      { offset: 0, color: '#6699cc' },
      { offset: 1, color: '#6699cc' }
    ]);
    scene.commit({ setPackedVertices: (vertices) => { packed = vertices; } });

    expect(packed.length).toBeGreaterThan(0);
    const colors = Array.from({ length: packed.length / 6 }, (_, index) => (
      Array.from(packed.slice(index * 6 + 2, index * 6 + 5)).join(',')
    ));
    expect(new Set(colors).size).toBeGreaterThan(2);
  });
});
