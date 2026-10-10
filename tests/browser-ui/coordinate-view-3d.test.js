import { describe, expect, it } from 'vitest';

import { buildCrosshair3dScene, createCoordinateView3d } from '../../browser-ui/vf-coordinate-view-3d.mjs';

function view() {
  const result = createCoordinateView3d({
    bounds: { x: [-6, 6], y: [-4, 4], z: [-4, 4] }
  });
  result.resize(1200, 800);
  return result;
}

describe('3D coordinate view', () => {
  it('projects the focus point to the viewport center', () => {
    expect(view().worldToScreen([0, 0, 0])).toEqual([600, 400]);
  });

  it('round-trips through a camera-orthogonal drawing plane', () => {
    const coordinateView = view();
    const world = [2, -1, 3];
    const screen = coordinateView.worldToScreen(world);
    const restored = coordinateView.screenToWorld(screen, { planePoint: world });
    expect(restored[0]).toBeCloseTo(world[0], 10);
    expect(restored[1]).toBeCloseTo(world[1], 10);
    expect(restored[2]).toBeCloseTo(world[2], 10);
  });

  it('keeps unsnapped placement on the requested drawing plane', () => {
    const coordinateView = view();
    const planePoint = [1, 2, 3];
    const placement = coordinateView.resolvePlacement([420, 310], { planePoint });
    const basis = coordinateView.snapshot().camera;
    const normal = normalize([
      basis.target[0] - basis.pos[0],
      basis.target[1] - basis.pos[1],
      basis.target[2] - basis.pos[2]
    ]);
    expect(dot(subtract(placement.world, planePoint), normal)).toBeCloseTo(0, 10);
  });

  it('always snaps Shift placement to a full 3D grid crossing', () => {
    const coordinateView = view();
    const screen = [437, 283];
    const cursorLine = coordinateView.screenLine(screen);
    const unsnapped = coordinateView.resolvePlacement(screen);
    const snapped = coordinateView.resolvePlacement(screen, { shift: true, vertexRadius: 0 });
    const interval = coordinateView.grid().interval;
    const fractions = snapped.world.map((value) => {
      const normalized = value / interval;
      return normalized - Math.floor(normalized);
    });
    expect(snapped.snap).toBe('intersection');
    expect(coordinateView.worldToScreen(cursorLine.point)).toEqual(screen);
    expect(Math.hypot(...cursorLine.direction)).toBeCloseTo(1, 12);
    expect(snapped.world).not.toEqual(unsnapped.world);
    expect(fractions.every((fraction) => fraction < 1e-9 || 1 - fraction < 1e-9)).toBe(true);
    expect(snapped.screenTarget).toEqual(coordinateView.worldToScreen(snapped.world));
  });

  it('does not grid-snap when the rendered 3D dotted grid is hidden', () => {
    const coordinateView = view();
    const screen = [437, 283];
    const scene = buildCrosshair3dScene(coordinateView, { gridVisible: false });
    const result = coordinateView.resolvePlacement(screen, { shift: true, gridScene: scene });

    expect(result.snap).toBe('none');
    expect(result.screenTarget).toEqual(screen);
  });

  it('snaps only to points present in the rendered 3D dotted grid', () => {
    const coordinateView = view();
    const scene = buildCrosshair3dScene(coordinateView);
    const requested = [437, 283];
    const result = coordinateView.resolvePlacement(requested, { shift: true, gridScene: scene });

    expect(scene.points.some(({ at, world }) =>
      at[0] === result.screenTarget[0]
      && at[1] === result.screenTarget[1]
      && world.every((value, index) => value === result.world[index])
    )).toBe(true);
  });

  it('uses the VKF trackball to rotate while preserving camera distance', () => {
    const coordinateView = view();
    const before = coordinateView.snapshot().camera;
    coordinateView.rotate([300, 300], [430, 360]);
    const after = coordinateView.snapshot().camera;
    expect(after.pos).not.toEqual(before.pos);
    expect(distance(after.pos, after.target)).toBeCloseTo(distance(before.pos, before.target), 10);
  });

  it('visually snaps the complete camera exactly onto an axis within 15 degrees', () => {
    const coordinateView = view();
    const angle = 10 * Math.PI / 180;
    coordinateView.restore({
      kind: 'coordinate-view-3d',
      camera: {
        pos: [-4 * Math.cos(angle), -4 * Math.sin(angle), 0],
        target: [0, 0, 0],
        up: [0, 0, 1]
      }
    });

    coordinateView.rotate([600, 400], [601, 400]);

    const { camera } = coordinateView.snapshot();
    const forward = normalize(subtract(camera.target, camera.pos));
    expect(forward[0]).toBeCloseTo(1, 12);
    expect(forward[1]).toBeCloseTo(0, 12);
    expect(forward[2]).toBeCloseTo(0, 12);
  });

  it('keeps the continuous camera unsnapped outside 15 degrees', () => {
    const coordinateView = view();
    const angle = 16 * Math.PI / 180;
    coordinateView.restore({
      kind: 'coordinate-view-3d',
      camera: {
        pos: [-4 * Math.cos(angle), -4 * Math.sin(angle), 0],
        target: [0, 0, 0],
        up: [0, 0, 1]
      }
    });

    coordinateView.rotate([600, 400], [600, 400]);

    const { camera } = coordinateView.snapshot();
    const forward = normalize(subtract(camera.target, camera.pos));
    expect(forward[0]).not.toBeCloseTo(1, 6);
    expect(Math.acos(forward[0]) * 180 / Math.PI).toBeCloseTo(16, 8);
  });

  it('rotates a two-contact Ctrl drag as one sphere without zooming', () => {
    const coordinateView = view();
    const before = coordinateView.snapshot().camera;
    coordinateView.rotateBetweenContactPairs(
      [[300, 280], [500, 320]],
      [[360, 330], [620, 390]]
    );
    const after = coordinateView.snapshot().camera;

    expect(after.pos).not.toEqual(before.pos);
    expect(after.target).toEqual(before.target);
    expect(after.ortho_scale).toBe(before.ortho_scale);
    expect(distance(after.pos, after.target)).toBeCloseTo(distance(before.pos, before.target), 10);
  });

  it('fits imported spatial geometry inside the viewport', () => {
    const coordinateView = view();
    const points = [[20, 30, 40], [24, 30, 40], [24, 34, 44], [20, 34, 44]];
    coordinateView.fitPoints(points);
    expect(coordinateView.snapshot().camera.target).toEqual([22, 32, 42]);
    for (const point of points) {
      const [x, y] = coordinateView.worldToScreen(point);
      expect(x).toBeGreaterThan(0);
      expect(x).toBeLessThan(1200);
      expect(y).toBeGreaterThan(0);
      expect(y).toBeLessThan(800);
    }
  });

  it('builds continuous VKF crosshair axes with ticks, labels, and dotted coordinate planes', () => {
    const scene = buildCrosshair3dScene(view());
    expect(scene.axes.map(({ axis }) => axis)).toEqual(['x', 'y', 'z']);
    expect(scene.points.length).toBeGreaterThan(30);
    expect(scene.lines).toEqual([]);
    expect(scene.ticks.length).toBeGreaterThan(0);
    expect(scene.labels.length).toBeGreaterThan(0);
    expect(scene.axes.every(({ from, to }) =>
      [from, to].some(([x, y]) => x === 0 || x === 1200 || y === 0 || y === 800)
    )).toBe(true);
  });
});

function subtract(left, right) {
  return left.map((value, index) => value - right[index]);
}

function dot(left, right) {
  return left.reduce((sum, value, index) => sum + value * right[index], 0);
}

function normalize(value) {
  const length = Math.hypot(...value);
  return value.map((entry) => entry / length);
}

function distance(left, right) {
  return Math.hypot(...subtract(left, right));
}
