import { describe, expect, it } from 'vitest';
import {
  createCoordinateView,
  snapRelativeScale,
  snapRotationDelta
} from '../../browser-ui/vf-coordinate-view.mjs';

function createView() {
  const view = createCoordinateView({ bounds: { x: [-6, 6], y: [-4, 4] } });
  view.resize(1200, 800);
  return view;
}

function expectPointClose(actual, expected, precision = 9) {
  expect(actual[0]).toBeCloseTo(expected[0], precision);
  expect(actual[1]).toBeCloseTo(expected[1], precision);
}

describe('coordinate view', () => {
  it('fits a newly opened world to its authored bounds', () => {
    const view = createView();
    view.fit({ x: [-1, 1], y: [-1, 1] });

    expectPointClose(view.worldToScreen([-1, -1]), [240, 760]);
    expectPointClose(view.worldToScreen([1, 1]), [960, 40]);
  });

  it.each([
    [0.94, 0.9],
    [1.06, 1.1],
    [1.96, 2],
    [2.24, 2],
    [2.26, 2.5],
    [9.49, 9.5],
    [9.76, 10],
    [10.6, 11],
    [19.4, 19],
    [22.6, 25],
    [0.16, 0.15],
    [0.096, 0.1]
  ])('snaps relative scale %s to the adaptive view rhythm %s', (raw, expected) => {
    expect(snapRelativeScale(raw)).toBeCloseTo(expected, 12);
  });

  it('snaps rotation deltas to 15-degree increments', () => {
    expect(snapRotationDelta(22 * Math.PI / 180)).toBeCloseTo(15 * Math.PI / 180, 12);
    expect(snapRotationDelta(-22 * Math.PI / 180)).toBeCloseTo(-15 * Math.PI / 180, 12);
    expect(snapRotationDelta(359 * Math.PI / 180)).toBeCloseTo(360 * Math.PI / 180, 12);
  });

  it('preserves full world precision when Shift is not active', () => {
    const view = createView();
    const world = [1.234567890123, -2.345678901234];
    const result = view.resolvePlacement(view.worldToScreen(world));

    expectPointClose(result.world, world, 11);
    expect(result.snap).toBe('none');
    expect(result.targetPoint).toBeNull();
  });

  it.each([false, true])('snaps to an existing vertex before grid placement when Shift is %s', (shift) => {
    const view = createView();
    const vertex = [1.125, -0.875];
    const rendered = view.worldToScreen(vertex);
    const result = view.resolvePlacement([rendered[0] + 4, rendered[1] - 3], {
      shift,
      vertexRadius: 7,
      vertices: [[-2, 1], vertex]
    });

    expect(result.snap).toBe('vertex');
    expect(result.targetPoint).toBe(1);
    expect(result.world).toEqual(vertex);
    expectPointClose(result.screenTarget, rendered);
  });

  it('uses exactly one rendered vertex radius for vertex snapping', () => {
    const view = createView();
    const vertex = [1, 1];
    const rendered = view.worldToScreen(vertex);

    expect(view.resolvePlacement([rendered[0] + 7, rendered[1]], {
      vertexRadius: 7,
      vertices: [vertex]
    }).snap).toBe('vertex');
    expect(view.resolvePlacement([rendered[0] + 7.01, rendered[1]], {
      vertexRadius: 7,
      vertices: [vertex]
    }).snap).toBe('none');
  });

  it('snaps both coordinates to a grid crossing while Shift is active', () => {
    const view = createView();
    const interval = view.grid().interval;
    const world = [interval * 0.12, interval * 0.44];
    const screen = view.worldToScreen(world);
    const exact = view.screenToWorld(screen);
    const result = view.resolvePlacement(screen, { shift: true, vertexRadius: 1 });

    expect(result.snap).toBe('intersection');
    expectPointClose(result.world, [0, 0]);
    expect(result.world[1]).not.toBe(exact[1]);
  });

  it('never leaves one coordinate arbitrary on a Shift grid snap', () => {
    const view = createView();
    const interval = view.grid().interval;
    const world = [interval * 0.44, interval * 0.12];
    const screen = view.worldToScreen(world);
    const exact = view.screenToWorld(screen);
    const result = view.resolvePlacement(screen, {
      shift: true,
      vertexRadius: 1
    });

    expect(result.snap).toBe('intersection');
    expectPointClose(result.world, [0, 0]);
    expect(result.world[0]).not.toBe(exact[0]);
  });

  it('snaps both coordinates within one rendered vertex radius of a crossing', () => {
    const view = createView();
    const crossing = [0, 0];
    const screen = view.worldToScreen(crossing);
    const result = view.resolvePlacement([screen[0] + 5, screen[1] - 4], {
      shift: true,
      vertexRadius: 7
    });

    expect(result.snap).toBe('intersection');
    expect(result.world).toEqual(crossing);
  });

  it('prefers a Shift grid point over either grid line at their crossing', () => {
    const view = createView();
    const crossing = [0, 0];
    const screen = view.worldToScreen(crossing);
    const result = view.resolvePlacement([screen[0] + 4, screen[1] - 4], {
      shift: true,
      vertexRadius: 7
    });

    expect(result).toMatchObject({
      world: crossing,
      snap: 'intersection',
      targetPoint: null
    });
  });

  it('does not grid-snap with Shift when the rendered grid is hidden', () => {
    const view = createView();
    const world = [0.37, -0.42];
    const screen = view.worldToScreen(world);
    const result = view.resolvePlacement(screen, {
      shift: true,
      gridScene: { mode: 'none', lines: [], points: [], circles: [] }
    });

    expect(result.snap).toBe('none');
    expectPointClose(result.world, world);
    expect(result.screenTarget).toEqual(screen);
  });

  it('snaps to a point from the rendered point grid instead of a synthesized line fraction', () => {
    const view = createView();
    const rendered = [view.worldToScreen([0, 0]), view.worldToScreen([2, 1])];
    const result = view.resolvePlacement([rendered[1][0] + 3, rendered[1][1] - 2], {
      shift: true,
      gridScene: {
        mode: 'points',
        lines: [],
        circles: [],
        points: rendered.map((at) => ({ at }))
      }
    });

    expect(result.snap).toBe('intersection');
    expect(result.screenTarget).toEqual(rendered[1]);
    expectPointClose(result.world, [2, 1]);
  });

  it('keeps the exact world coordinate under the wheel cursor', () => {
    const view = createView();
    const cursor = [841.25, 273.75];
    const before = view.screenToWorld(cursor);

    for (let index = 0; index < 24; index += 1) {
      view.zoomAt(cursor, -37);
      expectPointClose(view.screenToWorld(cursor), before, 10);
    }
    for (let index = 0; index < 24; index += 1) {
      view.zoomAt(cursor, 37);
      expectPointClose(view.screenToWorld(cursor), before, 10);
    }
  });

  it('supports deep zoom to floating-point-scale coordinates', () => {
    const view = createView();
    const center = [600, 400];
    view.zoomAt(center, -445000);

    expect(view.snapshot().transform.scale[0]).toBeGreaterThan(1e290);
    expect(Math.abs(view.screenToWorld([601, 400])[0])).toBeLessThan(1e-290);
    expect(view.grid().interval).toBeGreaterThan(0);
    expect(view.grid().interval).toBeLessThanOrEqual(1e-290);
  });

  it('zooms out beyond a 100-unit vertical span without an artificial scale floor', () => {
    const view = createView();
    const center = [600, 400];
    view.zoomAt(center, 5000);

    const verticalSpan = Math.abs(
      view.screenToWorld([600, 800])[1] - view.screenToWorld([600, 0])[1]
    );
    expect(verticalSpan).toBeGreaterThan(10_000);
    expect(view.snapshot().transform.scale[0]).toBeLessThan(0.1);
    expect(view.grid().interval).toBeGreaterThan(100);
  });

  it('pans by screen displacement without changing world scale', () => {
    const view = createView();
    const world = [2, -1];
    const before = view.worldToScreen(world);

    view.pan([100, 100], [145, 72]);
    expectPointClose(view.worldToScreen(world), [before[0] + 45, before[1] - 28]);
  });

  it('rotates the coordinate axes around the data origin', () => {
    const view = createView();
    const originBefore = view.worldToScreen([0, 0]);
    const pointBefore = view.worldToScreen([1, 0]);

    view.rotate(
      [originBefore[0] + 100, originBefore[1]],
      [originBefore[0], originBefore[1] + 100]
    );

    expectPointClose(view.worldToScreen([0, 0]), originBefore);
    expectPointClose(view.worldToScreen([1, 0]), [
      originBefore[0],
      originBefore[1] + (pointBefore[0] - originBefore[0])
    ]);
  });

  it('Shift-snaps an absolute rotation gesture relative to its baseline', () => {
    const view = createView();
    const origin = view.worldToScreen([0, 0]);
    const radius = 100;
    const angle = 22 * Math.PI / 180;

    view.rotate(
      [origin[0] + radius, origin[1]],
      [origin[0] + Math.cos(angle) * radius, origin[1] + Math.sin(angle) * radius],
      { shift: true }
    );

    expect(view.snapshot().transform.rotation).toBeCloseTo(15 * Math.PI / 180, 10);
  });

  it('Shift-snaps two-contact scale and rotation while preserving the centroid anchor', () => {
    const view = createView();
    const before = [[400, 400], [600, 400]];
    const centroidWorld = view.screenToWorld([500, 400]);
    const angle = 22 * Math.PI / 180;
    const radius = 226;
    const after = [
      [500 - Math.cos(angle) * radius, 400 - Math.sin(angle) * radius],
      [500 + Math.cos(angle) * radius, 400 + Math.sin(angle) * radius]
    ];
    const baselineScale = view.snapshot().transform.scale[0];

    view.transformBetweenContactPairs(before, after, { shift: true });

    expect(view.snapshot().transform.scale[0] / baselineScale).toBeCloseTo(2.5, 10);
    expect(view.snapshot().transform.rotation).toBeCloseTo(15 * Math.PI / 180, 10);
    expectPointClose(view.worldToScreen(centroidWorld), [500, 400], 8);
  });

  it('keeps both touched data coordinates attached through pan, zoom, and rotation', () => {
    const view = createView();
    const beforeContacts = [[360, 330], [720, 470]];
    const data = beforeContacts.map(view.screenToWorld);
    const afterContacts = [[410, 270], [790, 530]];
    const finalContacts = [[470, 310], [750, 610]];

    view.transformBetweenContactPairs(beforeContacts, afterContacts);
    expectPointClose(view.worldToScreen(data[0]), afterContacts[0], 8);
    expectPointClose(view.worldToScreen(data[1]), afterContacts[1], 8);

    view.transformBetweenContactPairs(afterContacts, finalContacts);
    expectPointClose(view.worldToScreen(data[0]), finalContacts[0], 8);
    expectPointClose(view.worldToScreen(data[1]), finalContacts[1], 8);
  });

  it('returns rotated coordinate grid lines with explicit axes', () => {
    const view = createView();
    const origin = view.worldToScreen([0, 0]);
    view.rotate([origin[0] + 100, origin[1]], [origin[0] + 70, origin[1] + 70]);

    const grid = view.grid();
    const axes = grid.lines.filter(({ axis }) => axis);
    expect(axes).toHaveLength(2);
    expect(axes.every(({ from, to }) => from[0] !== to[0] && from[1] !== to[1])).toBe(true);
  });

  it('returns screen basis vectors aligned with the rotated coordinate grid', () => {
    const view = createView();
    const origin = view.worldToScreen([0, 0]);
    view.rotate([origin[0] + 100, origin[1]], [origin[0] + 80, origin[1] + 60]);

    const basis = view.screenBasis([1, -2]);
    const point = view.worldToScreen([1, -2]);
    const xPoint = view.worldToScreen([2, -2]);
    const yPoint = view.worldToScreen([1, -1]);

    expectPointClose(basis.x, normalize([xPoint[0] - point[0], xPoint[1] - point[1]]));
    expectPointClose(basis.y, normalize([yPoint[0] - point[0], yPoint[1] - point[1]]));
  });

  it('uses the rotated rendered grid for Shift snapping', () => {
    const view = createView();
    const origin = view.worldToScreen([0, 0]);
    view.rotate([origin[0] + 100, origin[1]], [origin[0] + 80, origin[1] + 60]);
    const interval = view.grid().interval;
    const world = [interval * 0.08, interval * 0.42];

    const result = view.resolvePlacement(view.worldToScreen(world), {
      shift: true,
      vertexRadius: 1
    });

    expect(result.snap).toBe('intersection');
    expectPointClose(result.world, [0, 0]);
  });
});

function normalize(vector) {
  const length = Math.hypot(...vector);
  return [vector[0] / length, vector[1] / length];
}
