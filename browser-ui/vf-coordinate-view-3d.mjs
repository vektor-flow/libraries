import axis3dAdapter from 'vektor-flow/web/vf-ui/vf-axis3d-kernel-adapter.mjs';
import { buildCoordinateCrosshair3dScene } from 'vektor-flow/coordinate-grid';
import { nearestSpatialPointToLine } from 'vektor-flow/spatial-geometry';
import { nearestVisibleGridSnap } from './vf-visible-grid-snap.mjs';

const DEFAULT_VERTEX_RADIUS = 7;
const DEFAULT_GRID_SPACING = 72;
const AXIS_VIEW_SNAP_ANGLE_DEG = 15;
const MIN_ORTHO_SCALE = 0.05;
const MAX_ORTHO_SCALE = 1e4;
const { createJsAxis3DKernelAdapter } = axis3dAdapter;
const vkfAxis3d = createJsAxis3DKernelAdapter();

export function createCoordinateView3d({
  bounds,
  gridSpacing = DEFAULT_GRID_SPACING
} = {}) {
  let viewport = { width: 1, height: 1 };
  let camera = initialCamera(bounds);
  let initialized = false;

  function resize(width, height) {
    viewport = {
      width: Math.max(1, finite(width, 1)),
      height: Math.max(1, finite(height, 1))
    };
    initialized = true;
    return snapshot();
  }

  function worldToScreen(world) {
    const point = vec3(world);
    const basis = vkfAxis3d.screenBasis(camera, camera.target);
    const relative = subtract3(point, camera.target);
    const pixelsPerUnit = viewport.height / (2 * camera.ortho_scale);
    return [
      viewport.width / 2 + dot3(relative, basis.right) * pixelsPerUnit,
      viewport.height / 2 - dot3(relative, basis.up) * pixelsPerUnit
    ];
  }

  function screenToWorld(screen, options = {}) {
    const basis = vkfAxis3d.screenBasis(camera, camera.target);
    const pixelsPerUnit = viewport.height / (2 * camera.ortho_scale);
    const planePoint = vec3(options.planePoint, camera.target);
    const base = add3(
      camera.target,
      add3(
        scale3(basis.right, (finite(screen?.[0], viewport.width / 2) - viewport.width / 2) / pixelsPerUnit),
        scale3(basis.up, -(finite(screen?.[1], viewport.height / 2) - viewport.height / 2) / pixelsPerUnit)
      )
    );
    return add3(base, scale3(basis.forward, dot3(subtract3(planePoint, base), basis.forward)));
  }

  function screenBasis(world) {
    const origin = worldToScreen(world);
    return Object.freeze({
      x: Object.freeze(unit2(subtract2(worldToScreen(add3(vec3(world), [1, 0, 0])), origin))),
      y: Object.freeze(unit2(subtract2(worldToScreen(add3(vec3(world), [0, 1, 0])), origin))),
      z: Object.freeze(unit2(subtract2(worldToScreen(add3(vec3(world), [0, 0, 1])), origin)))
    });
  }

  function screenLine(screen) {
    const basis = vkfAxis3d.screenBasis(camera, camera.target);
    return Object.freeze({
      point: Object.freeze(screenToWorld(screen, { planePoint: camera.target })),
      direction: Object.freeze([...basis.forward])
    });
  }

  function grid() {
    const worldPerGridSpacing = gridSpacing * 2 * camera.ortho_scale / viewport.height;
    const interval = niceInterval(worldPerGridSpacing);
    return Object.freeze({
      interval,
      xInterval: interval,
      yInterval: interval,
      zInterval: interval,
      lines: Object.freeze([])
    });
  }

  function resolvePlacement(screen, {
    shift = false,
    vertexRadius = DEFAULT_VERTEX_RADIUS,
    vertices = [],
    planePoint = camera.target,
    gridScene = null,
    gridScreenToWorld = (point) => screenToWorld(point, { planePoint })
  } = {}) {
    if (shift) {
      if (gridScene) {
        const candidate = nearestVisibleGridSnap(gridScene, screen);
        if (candidate) return Object.freeze({
          world: Object.freeze(candidate.world || gridScreenToWorld(candidate.at)),
          snap: 'intersection',
          targetPoint: null,
          screenTarget: candidate.at
        });
      } else {
      const interval = grid().interval;
      const radius = gridRadius(interval, camera.ortho_scale);
      const visible = crosshairGridPoints(worldToScreen, interval, radius)
        .filter(({ at }) => insideViewport(at, viewport));
      const line = screenLine(screen);
      const nearestResult = visible.length ? nearestSpatialPointToLine(
        visible.map(({ world }) => world),
        {
          linePoint: line.point,
          lineDirection: line.direction,
          cameraForward: line.direction
        }
      ) : null;
      const nearest = nearestResult ? visible[nearestResult.index] : null;
      if (nearest) {
        return Object.freeze({
          world: nearest.world,
          snap: 'intersection',
          targetPoint: null,
          screenTarget: nearest.at
        });
      }
      }
    }
    const vertex = nearestRenderedVertex(screen, vertices, worldToScreen, vertexRadius, camera);
    if (vertex) {
      return Object.freeze({
        world: vertex.world,
        snap: 'vertex',
        targetPoint: vertex.index,
        screenTarget: vertex.screen
      });
    }
    const world = screenToWorld(screen, { planePoint });
    if (!shift) {
      return Object.freeze({
        world: Object.freeze(world),
        snap: 'none',
        targetPoint: null,
        screenTarget: Object.freeze([...screen])
      });
    }
    return Object.freeze({
      world: Object.freeze(world),
      snap: 'none',
      targetPoint: null,
      screenTarget: Object.freeze([...screen])
    });
  }

  function zoomAt(_screen, wheelDelta) {
    camera.ortho_scale = clamp(
      camera.ortho_scale * Math.exp(finite(wheelDelta, 0) * 0.0015),
      MIN_ORTHO_SCALE,
      MAX_ORTHO_SCALE
    );
    return snapshot();
  }

  function pan(previous, current) {
    const delta = vkfAxis3d.dragWorldDelta(
      camera,
      viewport.width,
      viewport.height,
      finite(current?.[0], 0) - finite(previous?.[0], 0),
      finite(current?.[1], 0) - finite(previous?.[1], 0)
    );
    camera.pos = add3(camera.pos, delta);
    camera.target = add3(camera.target, delta);
    return snapshot();
  }

  function rotate(previous, current) {
    vkfAxis3d.virtualTrackballRotate(
      camera,
      { mode: 'crosshair' },
      viewport,
      finite(previous?.[0], 0),
      finite(previous?.[1], 0),
      finite(current?.[0], 0),
      finite(current?.[1], 0)
    );
    vkfAxis3d.snapViewDirectionToNearestAxis(
      camera,
      { mode: 'crosshair' },
      { snapAngleDeg: AXIS_VIEW_SNAP_ANGLE_DEG }
    );
    return snapshot();
  }

  function transformBetweenContactPairs(previous, current) {
    const before = normalizeContactPair(previous);
    const after = normalizeContactPair(current);
    const beforeCenter = centroid(before);
    const afterCenter = centroid(after);
    const beforeDistance = distance2(before[0], before[1]);
    const afterDistance = distance2(after[0], after[1]);
    pan(beforeCenter, afterCenter);
    if (beforeDistance > 0 && afterDistance > 0) {
      camera.ortho_scale = clamp(
        camera.ortho_scale * beforeDistance / afterDistance,
        MIN_ORTHO_SCALE,
        MAX_ORTHO_SCALE
      );
    }
    return snapshot();
  }

  function rotateBetweenContactPairs(previous, current) {
    const beforeCenter = centroid(normalizeContactPair(previous));
    const afterCenter = centroid(normalizeContactPair(current));
    return rotate(beforeCenter, afterCenter);
  }

  function restore(next) {
    if (next?.kind !== 'coordinate-view-3d') return snapshot();
    camera = normalizeCamera(next.camera, camera);
    if (next.viewport) resize(next.viewport.width, next.viewport.height);
    initialized = true;
    return snapshot();
  }

  function snapshot() {
    return Object.freeze({
      kind: 'coordinate-view-3d',
      camera: freezeCamera(camera),
      viewport: Object.freeze({ ...viewport }),
      initialized
    });
  }

  function focusPoint() {
    return Object.freeze([...camera.target]);
  }

  function fitPoints(points, { padding = 1.18 } = {}) {
    const valid = (Array.isArray(points) ? points : []).map((point) => vec3(point))
      .filter((point) => point.every(Number.isFinite));
    if (!valid.length) return snapshot();
    const minimum = [0, 1, 2].map((axis) => Math.min(...valid.map((point) => point[axis])));
    const maximum = [0, 1, 2].map((axis) => Math.max(...valid.map((point) => point[axis])));
    const target = minimum.map((value, axis) => (value + maximum[axis]) / 2);
    const basis = vkfAxis3d.screenBasis(camera, target);
    const projected = valid.map((point) => {
      const relative = subtract3(point, target);
      return [dot3(relative, basis.right), dot3(relative, basis.up)];
    });
    const halfWidth = Math.max(1e-6, ...projected.map(([x]) => Math.abs(x)));
    const halfHeight = Math.max(1e-6, ...projected.map(([, y]) => Math.abs(y)));
    const aspect = viewport.width / Math.max(1, viewport.height);
    const translation = subtract3(target, camera.target);
    camera.pos = add3(camera.pos, translation);
    camera.target = target;
    camera.ortho_scale = clamp(Math.max(halfHeight, halfWidth / aspect) * padding, MIN_ORTHO_SCALE, MAX_ORTHO_SCALE);
    return snapshot();
  }

  return Object.freeze({
    resize,
    worldToScreen,
    screenToWorld,
    screenBasis,
    screenLine,
    grid,
    resolvePlacement,
    zoomAt,
    pan,
    rotate,
    transformBetweenContactPairs,
    rotateBetweenContactPairs,
    restore,
    snapshot,
    focusPoint,
    fitPoints
  });
}

export function buildCrosshair3dScene(view, {
  gridVisible = true,
  axisVisible = true,
  extent = null
} = {}) {
  const interval = view.grid().interval;
  const snapshot = view.snapshot();
  const cameraScale = snapshot.camera.ortho_scale;
  const radius = extent || gridRadius(interval, cameraScale);
  const points = gridVisible ? crosshairGridPoints(view.worldToScreen, interval, radius) : [];
  const crosshair = axisVisible
    ? buildCoordinateCrosshair3dScene({
        width: snapshot.viewport.width,
        height: snapshot.viewport.height,
        interval,
        worldToScreen: view.worldToScreen
      })
    : { axes: [], ticks: [], labels: [], axisLabels: [] };
  return Object.freeze({
    mode: 'points',
    axisMode: axisVisible ? 'regular' : 'none',
    lines: Object.freeze([]),
    points: Object.freeze(points),
    circles: Object.freeze([]),
    axes: crosshair.axes,
    ticks: crosshair.ticks,
    labels: crosshair.labels,
    axisLabels: crosshair.axisLabels
  });
}

function crosshairGridPoints(worldToScreen, interval, radius) {
  const values = multiples(-radius, radius, interval);
  const points = [];
  const seen = new Set();
  for (const plane of ['xy', 'xz', 'yz']) {
    const append = (first, second) => {
      const world = plane === 'xy'
        ? [first, second, 0]
        : plane === 'xz'
          ? [first, 0, second]
          : [0, first, second];
      const key = world.map((value) => Number(value.toPrecision(10))).join(':');
      if (seen.has(key)) return;
      seen.add(key);
      points.push(Object.freeze({
        at: Object.freeze(worldToScreen(world)),
        world: Object.freeze(world),
        kind: 'grid-point'
      }));
    };
    for (const first of values) for (const second of values) append(first, second);
  }
  return Object.freeze(points);
}

function gridRadius(interval, cameraScale) {
  return Math.max(interval, Math.ceil(cameraScale * 1.5 / interval) * interval);
}

function insideViewport([x, y], viewport) {
  return x >= 0 && x <= viewport.width && y >= 0 && y <= viewport.height;
}

function initialCamera(bounds = {}) {
  const xSpan = span(bounds.x, 12);
  const ySpan = span(bounds.y, 8);
  const zSpan = span(bounds.z, Math.min(xSpan, ySpan));
  const orthoScale = Math.max(xSpan, ySpan, zSpan) * 0.55;
  return {
    pos: [7, 7, 7],
    target: [0, 0, 0],
    up: [0, 0, 1],
    projection: 'orthographic',
    fov: 45,
    ortho_scale: orthoScale
  };
}

function normalizeCamera(value, fallback) {
  return {
    ...fallback,
    ...(value || {}),
    pos: vec3(value?.pos, fallback.pos),
    target: vec3(value?.target, fallback.target),
    up: vec3(value?.up, fallback.up),
    projection: 'orthographic',
    ortho_scale: clamp(finite(value?.ortho_scale, fallback.ortho_scale), MIN_ORTHO_SCALE, MAX_ORTHO_SCALE)
  };
}

function freezeCamera(camera) {
  return Object.freeze({
    ...camera,
    pos: Object.freeze([...camera.pos]),
    target: Object.freeze([...camera.target]),
    up: Object.freeze([...camera.up])
  });
}

function nearestRenderedVertex(screen, vertices, project, radius, camera) {
  const basis = vkfAxis3d.screenBasis(camera, camera.target);
  return vertices
    .map((world, index) => ({
      index,
      world: Object.freeze(vec3(world)),
      screen: Object.freeze(project(world)),
      depth: dot3(subtract3(vec3(world), camera.pos), basis.forward)
    }))
    .map((candidate) => ({ ...candidate, distance: distance2(candidate.screen, screen) }))
    .filter(({ distance }) => distance <= radius)
    .sort((left, right) => left.distance - right.distance || left.depth - right.depth)[0] || null;
}

function normalizeContactPair(value) {
  if (!Array.isArray(value) || value.length !== 2) {
    throw new TypeError('A 3D coordinate gesture requires exactly two contacts.');
  }
  return value.map((point) => [finite(point?.[0], 0), finite(point?.[1], 0)]);
}

function centroid(pair) {
  return [(pair[0][0] + pair[1][0]) / 2, (pair[0][1] + pair[1][1]) / 2];
}

function multiples(minimum, maximum, interval) {
  const result = [];
  for (let value = minimum; value <= maximum + interval * 1e-9; value += interval) {
    result.push(Number(value.toPrecision(12)));
  }
  return result;
}

function niceInterval(value) {
  const normalized = Math.max(1e-12, finite(value, 1));
  const magnitude = 10 ** Math.floor(Math.log10(normalized));
  const fraction = normalized / magnitude;
  const nice = fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10;
  return nice * magnitude;
}

function span(value, fallback) {
  return Array.isArray(value) && value.length >= 2
    ? Math.max(1e-9, finite(value[1], fallback) - finite(value[0], 0))
    : fallback;
}

function vec3(value, fallback = [0, 0, 0]) {
  return [0, 1, 2].map((index) => finite(value?.[index], fallback[index] || 0));
}

function add3(left, right) {
  return [left[0] + right[0], left[1] + right[1], left[2] + right[2]];
}

function subtract3(left, right) {
  return [left[0] - right[0], left[1] - right[1], left[2] - right[2]];
}

function scale3(value, scale) {
  return [value[0] * scale, value[1] * scale, value[2] * scale];
}

function dot3(left, right) {
  return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

function subtract2(left, right) {
  return [left[0] - right[0], left[1] - right[1]];
}

function unit2(value) {
  const length = Math.hypot(value[0], value[1]);
  return length > 1e-9 ? [value[0] / length, value[1] / length] : [1, 0];
}

function distance2(left, right) {
  return Math.hypot(left[0] - right[0], left[1] - right[1]);
}

function finite(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}
