import { describe, expect, it } from 'vitest';
import { nearestVisibleGridSnap, visibleGridSnapCandidates } from '../../browser-ui/vf-visible-grid-snap.mjs';

describe('visible grid snapping', () => {
  it('has no candidates for a hidden grid', () => {
    expect(nearestVisibleGridSnap({ mode: 'none' }, [10, 10])).toBeNull();
  });

  it('uses only points supplied by a dotted grid', () => {
    const scene = { mode: 'points', points: [{ at: [10, 10] }, { at: [30, 20] }] };
    expect(nearestVisibleGridSnap(scene, [28, 19]).at).toEqual([30, 20]);
  });

  it('uses only crossings from a visible line grid', () => {
    const scene = {
      mode: 'lines',
      points: [], circles: [],
      lines: [
        { from: [0, 0], to: [100, 0] },
        { from: [0, -20], to: [0, 20] },
        { from: [100, -20], to: [100, 20] }
      ]
    };
    expect(visibleGridSnapCandidates(scene).map(({ at }) => at)).toEqual([
      [0, 0],
      [100, 0]
    ]);
  });

  it('uses intersections of visible polar rays and circles', () => {
    const scene = {
      mode: 'polar', points: [],
      lines: [{ from: [0, 0], to: [100, 0] }],
      circles: [{ center: [0, 0], radius: 30 }]
    };
    expect(nearestVisibleGridSnap(scene, [29, 1]).at).toEqual([30, 0]);
  });
});
