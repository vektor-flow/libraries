export function nearestVisibleGridSnap(scene, screen) {
  if (!scene || scene.mode === 'none' || !isPoint(screen)) return null;
  const candidates = visibleGridSnapCandidates(scene);
  let nearest = null;
  let nearestDistance = Infinity;
  for (const candidate of candidates) {
    const distance = Math.hypot(candidate.at[0] - screen[0], candidate.at[1] - screen[1]);
    if (distance >= nearestDistance) continue;
    nearest = candidate;
    nearestDistance = distance;
  }
  return nearest && Object.freeze({ ...nearest, distance: nearestDistance });
}

export function visibleGridSnapCandidates(scene) {
  if (!scene || scene.mode === 'none') return Object.freeze([]);
  const candidates = [];
  const seen = new Set();
  const append = (at, world = null) => {
    if (!isPoint(at)) return;
    const key = `${at[0].toFixed(6)}:${at[1].toFixed(6)}`;
    if (seen.has(key)) return;
    seen.add(key);
    candidates.push(Object.freeze({
      at: Object.freeze([at[0], at[1]]),
      ...(Array.isArray(world) ? { world: Object.freeze([...world]) } : {})
    }));
  };
  for (const point of scene.points || []) append(point.at, point.world);

  const lines = (scene.lines || []).filter(validLine);
  const circles = (scene.circles || []).filter(validCircle);
  for (let left = 0; left < lines.length; left += 1) {
    for (let right = left + 1; right < lines.length; right += 1) {
      const at = segmentIntersection(lines[left], lines[right]);
      if (!at) continue;
      append(at);
    }
    for (const circle of circles) {
      for (const at of segmentCircleIntersections(lines[left], circle)) {
        append(at);
      }
    }
  }
  return Object.freeze(candidates);
}

function segmentIntersection(left, right) {
  const a = subtract(left.to, left.from);
  const b = subtract(right.to, right.from);
  const denominator = cross(a, b);
  if (Math.abs(denominator) <= 1e-9) return null;
  const relative = subtract(right.from, left.from);
  const t = cross(relative, b) / denominator;
  const u = cross(relative, a) / denominator;
  if (t < -1e-9 || t > 1 + 1e-9 || u < -1e-9 || u > 1 + 1e-9) return null;
  return [left.from[0] + t * a[0], left.from[1] + t * a[1]];
}

function segmentCircleIntersections(line, circle) {
  const delta = subtract(line.to, line.from);
  const relative = subtract(line.from, circle.center);
  const a = dot(delta, delta);
  const b = 2 * dot(relative, delta);
  const c = dot(relative, relative) - circle.radius * circle.radius;
  const discriminant = b * b - 4 * a * c;
  if (!(a > 0) || discriminant < -1e-9) return [];
  const root = Math.sqrt(Math.max(0, discriminant));
  return [(-b - root) / (2 * a), (-b + root) / (2 * a)]
    .filter((value, index, values) => value >= -1e-9 && value <= 1 + 1e-9
      && (index === 0 || Math.abs(value - values[0]) > 1e-9))
    .map((value) => [line.from[0] + value * delta[0], line.from[1] + value * delta[1]]);
}

function validLine(line) {
  return isPoint(line?.from) && isPoint(line?.to);
}

function validCircle(circle) {
  return isPoint(circle?.center) && Number.isFinite(circle?.radius) && circle.radius > 0;
}

function subtract(left, right) {
  return [left[0] - right[0], left[1] - right[1]];
}

function dot(left, right) {
  return left[0] * right[0] + left[1] * right[1];
}

function cross(left, right) {
  return left[0] * right[1] - left[1] * right[0];
}

function isPoint(point) {
  return Array.isArray(point) && point.length >= 2
    && Number.isFinite(point[0]) && Number.isFinite(point[1]);
}
