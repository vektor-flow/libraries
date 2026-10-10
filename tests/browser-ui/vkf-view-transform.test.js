import { describe, expect, it } from 'vitest';
import {
  applyVkfViewGesture,
  inverseTransformVkfViewPoint,
  normalizeVkfViewTransform,
  transformVkfViewPoint
} from '../../browser-ui/vf-view-transform.mjs';

describe('direct VKF view transform adapter', () => {
  it('round-trips a rotated anisotropic point', () => {
    const transform = normalizeVkfViewTransform({
      position: [12, -4],
      scale: [3, 2],
      rotation: Math.PI / 3
    });
    const world = transformVkfViewPoint([2, -5], transform);

    expect(inverseTransformVkfViewPoint(world, transform)[0]).toBeCloseTo(2);
    expect(inverseTransformVkfViewPoint(world, transform)[1]).toBeCloseTo(-5);
  });

  it('keeps the gesture origin fixed during scale and rotation', () => {
    const origin = [100, 80];
    const next = applyVkfViewGesture({
      position: origin,
      scale: 4,
      rotation: 0
    }, {
      origin,
      scale: 1.5,
      rotation: Math.PI / 2
    });

    expect(next.position).toEqual(origin);
    expect(next.scale).toEqual([6, 6]);
    expect(next.rotation).toBeCloseTo(Math.PI / 2);
  });
});
