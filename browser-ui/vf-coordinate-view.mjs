import {
  applyVkfViewGesture,
  inverseTransformVkfViewPoint,
  normalizeVkfViewTransform,
  transformVkfViewPoint
} from './vf-view-transform.mjs';
import vektorFlowAxis2d from 'vektor-flow/axis2d-ticks';
import { nearestVisibleGridSnap } from './vf-visible-grid-snap.mjs';

const DEFAULT_GRID_SPACING = 72;
const DEFAULT_VERTEX_RADIUS = 7;
const MIN_VIEW_SCALE = 1e-300;
const MAX_VIEW_SCALE = 1e300;
const MAX_GRID_LINES = 400;
const ROTATION_SNAP_STEP = Math.PI / 12;
const { buildAxisCrosshairTickState } = vektorFlowAxis2d;

export function createCoordinateView({
  bounds,
  gridSpacing = DEFAULT_GRID_SPACING,
  minScale = MIN_VIEW_SCALE,
  maxScale = MAX_VIEW_SCALE
}) {
  let viewport = { width: 1, height: 1 };
  let transform = normalizeVkfViewTransform();
  let referenceScale = 1;
  let initialized = false;

  function resize(width, height) {
    const next = {
      width: Math.max(1, finite(width, 1)),
      height: Math.max(1, finite(height, 1))
    };
    if (!initialized) {
      transform = initialTransform(bounds, next, minScale, maxScale);
      referenceScale = uniformScale(transform);
      initialized = true;
    } else if (next.width !== viewport.width || next.height !== viewport.height) {
      transform = applyVkfViewGesture(transform, {
        translation: [
          (next.width - viewport.width) / 2,
          (next.height - viewport.height) / 2
        ]
      });
    }
    viewport = next;
    return snapshot();
  }

  function worldToScreen(world) {
    return transformVkfViewPoint([world[0], -world[1]], transform);
  }

  function screenToWorld(screen) {
    const local = inverseTransformVkfViewPoint(screen, transform);
    return [local[0], -local[1]];
  }

  function screenBasis(world) {
    const origin = worldToScreen(world);
    const xPoint = worldToScreen([world[0] + 1, world[1]]);
    const yPoint = worldToScreen([world[0], world[1] + 1]);
    return Object.freeze({
      x: Object.freeze(unitVector(subtract(xPoint, origin))),
      y: Object.freeze(unitVector(subtract(yPoint, origin)))
    });
  }

  function grid() {
    const corners = [
      [0, 0],
      [viewport.width, 0],
      [viewport.width, viewport.height],
      [0, viewport.height]
    ].map(screenToWorld);
    const xRange = extent(corners.map(([x]) => x));
    const yRange = extent(corners.map(([, y]) => y));
    const tickState = buildAxisCrosshairTickState({
      width: viewport.width,
      height: viewport.height,
      x_visible_min: xRange[0],
      x_visible_max: xRange[1],
      y_visible_min: yRange[0],
      y_visible_max: yRange[1],
      x_mode: 'linear',
      y_mode: 'linear',
      hints: [1, 2, 5],
      dist: gridSpacing,
      min_dist: gridSpacing * 0.72,
      max_dist: gridSpacing * 1.45,
      tick_label_font_size: 11
    });
    const xInterval = tickState.x?.step || gridSpacing / uniformScale(transform);
    const yInterval = tickState.y?.step || xInterval;
    const lines = [];

    appendGridValues(lines, gridValues(tickState.x?.values, xRange), (value) => ({
      axis: nearlyZero(value, xInterval),
      interval: xInterval,
      orientation: 'vertical',
      value,
      from: worldToScreen([value, yRange[0]]),
      to: worldToScreen([value, yRange[1]])
    }));
    appendGridValues(lines, gridValues(tickState.y?.values, yRange), (value) => ({
      axis: nearlyZero(value, yInterval),
      interval: yInterval,
      orientation: 'horizontal',
      value,
      from: worldToScreen([xRange[0], value]),
      to: worldToScreen([xRange[1], value])
    }));

    return Object.freeze({
      interval: xInterval,
      xInterval,
      yInterval,
      lines: Object.freeze(lines)
    });
  }

  function resolvePlacement(screen, {
    shift = false,
    vertexRadius = DEFAULT_VERTEX_RADIUS,
    vertices = [],
    gridScene = null,
    gridScreenToWorld = screenToWorld
  } = {}) {
    const world = screenToWorld(screen);
    const vertex = nearestRenderedVertex(screen, vertices, worldToScreen, vertexRadius);
    if (vertex) {
      return Object.freeze({
        world: vertex.world,
        snap: 'vertex',
        targetPoint: vertex.index,
        screenTarget: vertex.screen
      });
    }
    if (!shift) {
      return Object.freeze({
        world,
        snap: 'none',
        targetPoint: null,
        screenTarget: screen
      });
    }

    if (gridScene) {
      const candidate = nearestVisibleGridSnap(gridScene, screen);
      if (!candidate) return Object.freeze({ world, snap: 'none', targetPoint: null, screenTarget: screen });
      return Object.freeze({
        world: Object.freeze(candidate.world || gridScreenToWorld(candidate.at)),
        snap: 'intersection',
        targetPoint: null,
        screenTarget: candidate.at
      });
    }

    const { xInterval, yInterval } = grid();
    const crossing = [
      Math.round(world[0] / xInterval) * xInterval,
      Math.round(world[1] / yInterval) * yInterval
    ];
    return Object.freeze({
      world: crossing,
      snap: 'intersection',
      targetPoint: null,
      screenTarget: worldToScreen(crossing)
    });
  }

  function applyGesture(gesture = {}, {
    shift = false,
    snapRotation = false,
    snapScale = false
  } = {}) {
    const requestedScale = finite(gesture.scale, 1);
    const currentScale = uniformScale(transform);
    const rawNextScale = currentScale * requestedScale;
    const snappedNextScale = shift && snapScale
      ? referenceScale * snapRelativeScale(rawNextScale / referenceScale)
      : rawNextScale;
    const nextScale = clamp(snappedNextScale, minScale, maxScale);
    const requestedRotation = finite(gesture.rotation, 0);
    const nextRotation = shift && snapRotation
      ? snapRotationDelta(transform.rotation + requestedRotation)
      : transform.rotation + requestedRotation;
    transform = applyVkfViewGesture(transform, {
      ...gesture,
      scale: nextScale / currentScale,
      rotation: nextRotation - transform.rotation
    });
    return snapshot();
  }

  function zoomAt(screen, wheelDelta, { shift = false } = {}) {
    return applyGesture({
      origin: screen,
      scale: Math.exp(-finite(wheelDelta, 0) * 0.0015)
    }, { shift, snapScale: true });
  }

  function pan(previous, current) {
    return applyGesture({
      translation: [current[0] - previous[0], current[1] - previous[1]]
    });
  }

  function rotate(previous, current, { shift = false } = {}) {
    const origin = worldToScreen([0, 0]);
    const previousVector = [previous[0] - origin[0], previous[1] - origin[1]];
    const currentVector = [current[0] - origin[0], current[1] - origin[1]];
    const previousRadius = Math.hypot(...previousVector);
    const currentRadius = Math.hypot(...currentVector);
    const rotation = previousRadius < 12 || currentRadius < 12
      ? (current[0] - previous[0]) * 0.01
      : Math.atan2(currentVector[1], currentVector[0]) - Math.atan2(previousVector[1], previousVector[0]);
    return applyGesture({ origin, rotation }, { shift, snapRotation: true });
  }

  function transformBetweenContactPairs(previous, current, { shift = false } = {}) {
    const before = normalizeContactPair(previous);
    const after = normalizeContactPair(current);
    const beforeCentroid = centroid(before);
    const afterCentroid = centroid(after);
    const beforeVector = subtract(before[1], before[0]);
    const afterVector = subtract(after[1], after[0]);
    const beforeDistance = Math.hypot(...beforeVector);
    const afterDistance = Math.hypot(...afterVector);
    if (beforeDistance === 0 || afterDistance === 0) return snapshot();

    return applyGesture({
      origin: beforeCentroid,
      translation: subtract(afterCentroid, beforeCentroid),
      scale: afterDistance / beforeDistance,
      rotation: Math.atan2(afterVector[1], afterVector[0]) - Math.atan2(beforeVector[1], beforeVector[0])
    }, { shift, snapRotation: true, snapScale: true });
  }

  function restore(next) {
    transform = normalizeVkfViewTransform(next?.transform);
    referenceScale = positiveFinite(next?.referenceScale, referenceScale);
    if (next?.viewport) {
      viewport = {
        width: Math.max(1, finite(next.viewport.width, viewport.width)),
        height: Math.max(1, finite(next.viewport.height, viewport.height))
      };
    }
    initialized = true;
    return snapshot();
  }

  function fit(nextBounds) {
    transform = initialTransform(nextBounds, viewport, minScale, maxScale);
    referenceScale = uniformScale(transform);
    initialized = true;
    return snapshot();
  }

  function snapshot() {
    return Object.freeze({
      transform: normalizeVkfViewTransform(transform),
      referenceScale,
      viewport: Object.freeze({ ...viewport })
    });
  }

  return Object.freeze({
    resize,
    worldToScreen,
    screenToWorld,
    screenBasis,
    grid,
    resolvePlacement,
    zoomAt,
    pan,
    rotate,
    transformBetweenContactPairs,
    fit,
    restore,
    snapshot
  });
}

export function snapRotationDelta(rotation, step = ROTATION_SNAP_STEP) {
  const normalizedStep = positiveFinite(step, ROTATION_SNAP_STEP);
  return Math.round(finite(rotation, 0) / normalizedStep) * normalizedStep;
}

export function snapRelativeScale(relativeScale) {
  const scale = positiveFinite(relativeScale, 1);
  const decade = 10 ** Math.floor(Math.log10(scale));
  const mantissa = scale / decade;
  const step = scale >= 1
    ? (mantissa < 2 ? decade * 0.1 : decade * 0.5)
    : (mantissa < 2 ? decade * 0.5 : decade);
  return Number((Math.round(scale / step) * step).toPrecision(12));
}

function initialTransform(bounds, viewport, minScale, maxScale) {
  const x = bounds?.x || [-1, 1];
  const y = bounds?.y || [-1, 1];
  const width = Math.max(Number.EPSILON, x[1] - x[0]);
  const height = Math.max(Number.EPSILON, y[1] - y[0]);
  const scale = clamp(Math.min(viewport.width / width, viewport.height / height) * 0.9, minScale, maxScale);
  const center = [(x[0] + x[1]) / 2, (y[0] + y[1]) / 2];
  return normalizeVkfViewTransform({
    position: [
      viewport.width / 2 - center[0] * scale,
      viewport.height / 2 + center[1] * scale
    ],
    scale,
    rotation: 0
  });
}

function gridValues(values, range) {
  const visible = Array.isArray(values)
    ? values.filter((value) => value >= range[0] && value <= range[1])
    : [];
  if (range[0] <= 0 && range[1] >= 0 && !visible.some((value) => value === 0)) visible.push(0);
  return visible.sort((a, b) => a - b);
}

function appendGridValues(lines, values, createLine) {
  if (values.length > MAX_GRID_LINES) return;
  for (const value of values) lines.push(createLine(value));
}

function normalizeContactPair(pair) {
  if (!Array.isArray(pair) || pair.length !== 2) {
    throw new TypeError('A coordinate gesture requires exactly two contacts.');
  }
  return pair.map((point) => [finite(point?.[0], 0), finite(point?.[1], 0)]);
}

function centroid(pair) {
  return [(pair[0][0] + pair[1][0]) / 2, (pair[0][1] + pair[1][1]) / 2];
}

function subtract(a, b) {
  return [a[0] - b[0], a[1] - b[1]];
}

function unitVector(vector) {
  const length = Math.hypot(...vector);
  return length > 0 ? [vector[0] / length, vector[1] / length] : [1, 0];
}

function extent(values) {
  return [Math.min(...values), Math.max(...values)];
}

function uniformScale(transform) {
  return Math.sqrt(Math.abs(transform.scale[0] * transform.scale[1]));
}

function distance(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

function nearestRenderedVertex(screen, vertices, worldToScreen, vertexRadius) {
  let nearest = null;
  let nearestDistance = Math.max(0, vertexRadius);
  vertices.forEach((world, index) => {
    if (!Array.isArray(world) || world.length < 2) return;
    const rendered = worldToScreen(world);
    const renderedDistance = distance(rendered, screen);
    if (renderedDistance <= nearestDistance) {
      nearest = { index, world: [...world], screen: rendered };
      nearestDistance = renderedDistance;
    }
  });
  return nearest;
}

function nearlyZero(value, interval) {
  return Math.abs(value) <= interval * 1e-9;
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function finite(value, fallback) {
  return Number.isFinite(value) ? value : fallback;
}

function positiveFinite(value, fallback) {
  return Number.isFinite(value) && value > 0 ? value : fallback;
}
