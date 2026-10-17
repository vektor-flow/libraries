export function buildEdgeSelectionPaths(edges = []) {
  const records = edges
    .map(({ a, b }, index) => ({ a: Number(a), b: Number(b), index }))
    .filter(({ a, b }) => Number.isInteger(a) && Number.isInteger(b) && a !== b);
  const adjacency = new Map();
  for (const edge of records) {
    appendAdjacent(adjacency, edge.a, edge);
    appendAdjacent(adjacency, edge.b, edge);
  }
  for (const incident of adjacency.values()) {
    incident.sort(compareEdges);
  }

  const visited = new Set();
  const paths = [];
  const boundaryVertices = [...adjacency.entries()]
    .filter(([, incident]) => incident.length !== 2)
    .map(([vertex]) => vertex)
    .sort(compareNumbers);

  for (const vertex of boundaryVertices) {
    for (const edge of adjacency.get(vertex)) {
      if (visited.has(edge.index)) continue;
      paths.push(normalizeOpenPath(walkPath(vertex, edge, adjacency, visited)));
    }
  }

  for (const edge of records.sort(compareEdges)) {
    if (visited.has(edge.index)) continue;
    paths.push(normalizeCycle(walkPath(Math.min(edge.a, edge.b), edge, adjacency, visited)));
  }

  return paths.sort(comparePaths);
}

export function buildFaceSelectionBoundaryPaths(faces = []) {
  const boundaryByKey = new Map();
  for (const face of faces) {
    const vertices = normalizeFace(face);
    for (let index = 0; index < vertices.length; index += 1) {
      const a = vertices[index];
      const b = vertices[(index + 1) % vertices.length];
      const key = a < b ? `${a}:${b}` : `${b}:${a}`;
      const boundary = boundaryByKey.get(key);
      if (boundary) {
        boundary.count += 1;
      } else {
        boundaryByKey.set(key, { a, b, count: 1 });
      }
    }
  }
  return buildEdgeSelectionPaths(
    [...boundaryByKey.values()]
      .filter(({ count }) => count === 1)
      .map(({ a, b }) => ({ a, b }))
  );
}

export function buildIndependentEdgeSelectionPaths(edges = []) {
  return edges
    .map(({ a, b }) => [Number(a), Number(b)])
    .filter(([a, b]) => Number.isInteger(a) && Number.isInteger(b) && a !== b)
    .map(normalizeOpenPath)
    .sort(comparePaths);
}

export function buildIndependentFaceSelectionPaths(faces = []) {
  return faces
    .map(normalizeFace)
    .filter((face) => face.length >= 3)
    .map((face) => normalizeCycle([...face, face[0]]))
    .sort(comparePaths);
}

function walkPath(start, firstEdge, adjacency, visited) {
  const path = [start];
  let vertex = start;
  let edge = firstEdge;
  while (edge && !visited.has(edge.index)) {
    visited.add(edge.index);
    vertex = edge.a === vertex ? edge.b : edge.a;
    path.push(vertex);
    const incident = adjacency.get(vertex) || [];
    if (incident.length !== 2) break;
    edge = incident.find((candidate) => !visited.has(candidate.index));
  }
  return path;
}

function normalizeOpenPath(path) {
  const reversed = [...path].reverse();
  return comparePaths(path, reversed) <= 0 ? path : reversed;
}

function normalizeCycle(path) {
  if (path[0] !== path.at(-1)) return normalizeOpenPath(path);
  const cycle = path.slice(0, -1);
  const candidates = [];
  for (const direction of [cycle, [...cycle].reverse()]) {
    for (let index = 0; index < direction.length; index += 1) {
      const rotated = [...direction.slice(index), ...direction.slice(0, index)];
      candidates.push([...rotated, rotated[0]]);
    }
  }
  return candidates.sort(comparePaths)[0];
}

function appendAdjacent(adjacency, vertex, edge) {
  if (!adjacency.has(vertex)) adjacency.set(vertex, []);
  adjacency.get(vertex).push(edge);
}

function compareEdges(left, right) {
  return Math.min(left.a, left.b) - Math.min(right.a, right.b)
    || Math.max(left.a, left.b) - Math.max(right.a, right.b)
    || left.index - right.index;
}

function comparePaths(left, right) {
  const length = Math.min(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    if (left[index] !== right[index]) return left[index] - right[index];
  }
  return left.length - right.length;
}

function compareNumbers(left, right) {
  return left - right;
}

function normalizeFace(face) {
  if (!Array.isArray(face)) return [];
  const vertices = face
    .map(Number)
    .filter((vertex) => Number.isInteger(vertex) && vertex >= 0);
  if (vertices.length > 1 && vertices[0] === vertices.at(-1)) vertices.pop();
  return vertices.length >= 3 ? vertices : [];
}
