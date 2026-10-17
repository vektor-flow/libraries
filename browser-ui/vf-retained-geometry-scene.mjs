import {
  colorToRgba
} from 'vektor-flow/screen-simplex-renderer';
import { createLayeredScreenScene } from 'vektor-flow/layered-screen-scene';

export function createRetainedGeometryScene() {
  const scene = createLayeredScreenScene();

  // Keep only the preceding/current frame's privately owned contour records.
  // Caller geometry is compared by value every time, including mutable arrays.
  let previousContours = new Map(), currentContours = new Map(), recording = null;
  const own = value => Array.isArray(value) ? Object.freeze(value.map(own))
    : value && typeof value === 'object'
      ? Object.freeze(Object.fromEntries(Object.entries(value).map(([key, item]) => [key, own(item)])))
      : value;
  const samePoints = (a, b) => a.length === b.length && a.every((point, i) =>
    point.length === b[i].length && point.every((value, j) => Object.is(value, b[i][j])));

  function beginFrame() {
    previousContours = currentContours;
    currentContours = new Map();
    scene.beginFrame();
  }

  function primitive(scope, id, value, { selection = false, overlay = false } = {}) {
    if (recording) {
      value = own(value);
      recording.push({scope, id, value, selection, overlay});
    }
    scene.primitive(scope, id, value, { selection, overlay });
  }

  function path(scope, id, points, width, stops, options = {}) {
    if (!Array.isArray(points) || points.length < 2) return;
    const lengths = [0];
    for (let index = 1; index < points.length; index += 1) {
      lengths.push(lengths.at(-1) + Math.hypot(
        points[index][0] - points[index - 1][0],
        points[index][1] - points[index - 1][1]
      ));
    }
    const total = lengths.at(-1) || 1;
    const offsets = uniqueSortedOffsets([
      ...lengths.map((length) => length / total),
      ...(Array.isArray(stops) ? stops.map(({ offset }) => offset) : [])
    ]);
    for (let index = 1; index < offsets.length; index += 1) {
      const fromOffset = offsets[index - 1];
      const toOffset = offsets[index];
      const fromColor = rgbaAtStops(stops, fromOffset);
      const toColor = rgbaAtStops(stops, toOffset);
      primitive(scope, `${id}:${index - 1}`, {
        kind: 'edge',
        from: pointAtPathOffset(points, lengths, total, fromOffset),
        to: pointAtPathOffset(points, lengths, total, toOffset),
        width,
        fromColor,
        toColor
      }, options);
    }
  }

  function sphereImpostor(scope, id, center, radius, color, options = {}) {
    const rgba = colorToRgba(color);
    primitive(scope, `${id}:rim`, {
      kind: 'vertex',
      center,
      radius,
      segments: 32,
      color: shadeRgba(rgba, -0.48)
    }, options);
    primitive(scope, `${id}:body`, {
      kind: 'vertex',
      center: [center[0] - radius * 0.08, center[1] - radius * 0.08],
      radius: radius * 0.78,
      segments: 32,
      color: rgba
    }, options);
    primitive(scope, `${id}:light`, {
      kind: 'vertex',
      center: [center[0] - radius * 0.3, center[1] - radius * 0.3],
      radius: radius * 0.24,
      segments: 20,
      color: shadeRgba(rgba, 0.52)
    }, options);
  }

  function tubeImpostor(scope, id, points, width, stops, options = {}) {
    path(scope, `${id}:shadow`, points, width, shadeStops(stops, -0.42), options);
    path(scope, `${id}:light`, points, width * 0.58, shadeStops(stops, 0.28), options);
  }

  function ring(scope, id, center, radius, width, color, options = {}) {
    const segments = 32;
    const points = Array.from({ length: segments + 1 }, (_, index) => {
      const angle = index / segments * Math.PI * 2;
      return [center[0] + Math.cos(angle) * radius, center[1] + Math.sin(angle) * radius];
    });
    path(scope, id, points, width, solidStops(color), options);
  }

  function arrow(scope, id, arrowValue, color, pixelRatio, options = {}) {
    const [ux, uy] = arrowValue.tangent;
    const length = 8 * pixelRatio;
    const halfWidth = 4.5 * pixelRatio;
    const [x, y] = arrowValue.position;
    primitive(scope, `${id}:head`, {
      kind: 'face',
      points: [
        [x, y],
        [x - ux * length - uy * halfWidth, y - uy * length + ux * halfWidth],
        [x - ux * length + uy * halfWidth, y - uy * length - ux * halfWidth]
      ],
      color
    }, options);
  }

  function selectionContour(scope, id, points, color, pixelRatio, metrics) {
    if (!Array.isArray(points) || points.length < 2) return;
    const rgba = colorToRgba(color);
    const key = JSON.stringify([scope, id]);
    const prior = currentContours.get(key) || previousContours.get(key);
    if (prior && Object.is(prior.pixelRatio, pixelRatio)
      && Object.is(prior.radius, metrics.selectionRadius)
      && Object.is(prior.width, metrics.ringWidth)
      && samePoints([prior.color], [rgba]) && samePoints(prior.points, points)) {
      currentContours.set(key, prior);
      for (const item of prior.primitives) scene.primitive(item.scope, item.id, item.value, item);
      return;
    }
    const entry = {points:own(points), color:own(rgba), pixelRatio,
      radius:metrics.selectionRadius, width:metrics.ringWidth, primitives:[]};
    recording = entry.primitives;
    try { buildSelectionContour(scope, id, points, rgba, pixelRatio, metrics); }
    finally { recording = null; }
    currentContours.set(key, entry);
  }

  function buildSelectionContour(scope, id, points, color, pixelRatio, metrics) {
    if (!Array.isArray(points) || points.length < 2) return;
    const offset = metrics.selectionRadius * pixelRatio;
    const width = metrics.ringWidth * pixelRatio;
    const first = points[0];
    const last = points.at(-1);
    const closed = Math.hypot(last[0] - first[0], last[1] - first[1]) <= 1e-9;
    const outwardSide = closed ? -(Math.sign(closedPathSignedArea(points)) || 1) : null;
    const contourSides = closed ? [outwardSide] : [-1, 1];
    for (let index = 1; index < points.length; index += 1) {
      const from = points[index - 1];
      const to = points[index];
      const dx = to[0] - from[0];
      const dy = to[1] - from[1];
      const length = Math.hypot(dx, dy);
      if (length <= 1e-9) continue;
      const normal = [-dy / length * offset, dx / length * offset];
      for (const side of contourSides) {
        primitive(scope, `${id}:${index - 1}:${side}`, {
          kind: 'edge',
          from: [from[0] + normal[0] * side, from[1] + normal[1] * side],
          to: [to[0] + normal[0] * side, to[1] + normal[1] * side],
          width,
          color
        }, { selection: true });
      }
    }
    if (closed) {
      const vertexCount = points.length - 1;
      for (let index = 0; index < vertexCount; index += 1) {
        addSelectionRoundJoin(
          scope,
          `${id}:join:${index}`,
          points[index],
          points[(index - 1 + vertexCount) % vertexCount],
          points[(index + 1) % vertexCount],
          offset,
          width,
          color,
          [outwardSide]
        );
      }
      return;
    }
    for (let index = 1; index < points.length - 1; index += 1) {
      addSelectionRoundJoin(
        scope,
        `${id}:join:${index}`,
        points[index],
        points[index - 1],
        points[index + 1],
        offset,
        width,
        color
      );
    }
    addSelectionEndCap(scope, `${id}:start-cap`, first, points[1], -1, offset, width, color);
    addSelectionEndCap(
      scope,
      `${id}:end-cap`,
      last,
      points.at(-2),
      -1,
      offset,
      width,
      color
    );
  }

  function addSelectionRoundJoin(
    scope,
    id,
    center,
    previous,
    next,
    radius,
    width,
    color,
    sides = [-1, 1]
  ) {
    // Radius zero creates only zero-length edges, which the packed backend
    // discards. Avoid allocating those empty primitives in the first place.
    if (radius === 0) return;
    const incoming = unitVector(center[0] - previous[0], center[1] - previous[1]);
    const outgoing = unitVector(next[0] - center[0], next[1] - center[1]);
    if (!incoming || !outgoing) return;
    for (const side of sides) {
      const startAngle = Math.atan2(incoming[0] * side, -incoming[1] * side);
      const endAngle = Math.atan2(outgoing[0] * side, -outgoing[1] * side);
      const delta = shortestAngleDelta(startAngle, endAngle);
      if (Math.abs(delta) <= 1e-9) continue;
      const segments = Math.max(2, Math.ceil(Math.abs(delta) / (Math.PI / 12)));
      let previousPoint = [
        center[0] + Math.cos(startAngle) * radius,
        center[1] + Math.sin(startAngle) * radius
      ];
      for (let index = 1; index <= segments; index += 1) {
        const angle = startAngle + delta * index / segments;
        const currentPoint = [
          center[0] + Math.cos(angle) * radius,
          center[1] + Math.sin(angle) * radius
        ];
        primitive(scope, `${id}:${side}:${index - 1}`, {
          kind: 'edge',
          from: previousPoint,
          to: currentPoint,
          width,
          color
        }, { selection: true });
        previousPoint = currentPoint;
      }
    }
  }

  function addSelectionEndCap(scope, id, center, inside, outwardSign, radius, width, color) {
    if (radius === 0) return;
    const inwardX = inside[0] - center[0];
    const inwardY = inside[1] - center[1];
    const length = Math.hypot(inwardX, inwardY);
    if (length <= 1e-9) return;
    const outward = [inwardX / length * outwardSign, inwardY / length * outwardSign];
    const normal = [-outward[1], outward[0]];
    const segments = 12;
    let previous = [center[0] + normal[0] * radius, center[1] + normal[1] * radius];
    for (let index = 1; index <= segments; index += 1) {
      const angle = index / segments * Math.PI;
      const current = [
        center[0] + (normal[0] * Math.cos(angle) + outward[0] * Math.sin(angle)) * radius,
        center[1] + (normal[1] * Math.cos(angle) + outward[1] * Math.sin(angle)) * radius
      ];
      primitive(scope, `${id}:${index - 1}`, {
        kind: 'edge',
        from: previous,
        to: current,
        width,
        color
      }, { selection: true });
      previous = current;
    }
  }

  function commit(renderer) {
    return scene.commit(renderer);
  }

  function invalidate() {
    scene.invalidate();
  }

  return Object.freeze({
    beginFrame,
    primitive,
    path,
    sphereImpostor,
    tubeImpostor,
    ring,
    arrow,
    selectionContour,
    commit,
    invalidate
  });
}

function shadeRgba(color, amount) {
  const toward = amount >= 0 ? 1 : 0;
  const strength = Math.min(1, Math.abs(amount));
  return color.map((value, index) => index === 3
    ? value
    : value + (toward - value) * strength);
}

function shadeStops(stops, amount) {
  return stops.map((stop) => ({
    ...stop,
    color: shadeRgba(colorToRgba(stop.color), amount)
  }));
}

function rgbaAtStops(stops, offset) {
  const rightIndex = Math.max(1, stops.findIndex((stop) => stop.offset >= offset));
  const left = stops[rightIndex - 1] || stops[0];
  const right = stops[rightIndex] || stops.at(-1);
  const span = right.offset - left.offset;
  const t = span > 1e-12 ? Math.max(0, Math.min(1, (offset - left.offset) / span)) : 0;
  const from = colorToRgba(left.color);
  const to = colorToRgba(right.color);
  return from.map((value, index) => value + (to[index] - value) * t);
}

function solidStops(color) {
  return [{ offset: 0, color }, { offset: 1, color }];
}

function uniqueSortedOffsets(offsets) {
  const sorted = offsets
    .map(Number)
    .filter(Number.isFinite)
    .map((offset) => Math.max(0, Math.min(1, offset)))
    .sort((left, right) => left - right);
  return sorted.filter((offset, index) => index === 0 || offset - sorted[index - 1] > 1e-9);
}

function pointAtPathOffset(points, lengths, total, offset) {
  const target = offset * total;
  let index = 1;
  while (index < lengths.length - 1 && lengths[index] < target) index += 1;
  const fromLength = lengths[index - 1];
  const span = lengths[index] - fromLength;
  if (span <= 1e-12) return [...points[index]];
  const t = Math.max(0, Math.min(1, (target - fromLength) / span));
  return [
    points[index - 1][0] + (points[index][0] - points[index - 1][0]) * t,
    points[index - 1][1] + (points[index][1] - points[index - 1][1]) * t
  ];
}

function unitVector(x, y) {
  const length = Math.hypot(x, y);
  return length > 1e-9 ? [x / length, y / length] : null;
}

function shortestAngleDelta(from, to) {
  let delta = (to - from) % (Math.PI * 2);
  if (delta > Math.PI) delta -= Math.PI * 2;
  if (delta < -Math.PI) delta += Math.PI * 2;
  return delta;
}

function closedPathSignedArea(points) {
  let area = 0;
  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index];
    const to = points[index + 1];
    area += from[0] * to[1] - to[0] * from[1];
  }
  return area / 2;
}
