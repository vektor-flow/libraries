import { createRetainedGeometryScene } from './vf-retained-geometry-scene.mjs';
import { materializeRetainedSceneArena } from './vf-retained-scene-arena.mjs';

// Presentation of compiler-owned field_mesh values. Geometry and physics are
// supplied by Frame.add/World; this view never evaluates source or steps a World.
export function createRetainedPlotView({ coordinates, renderer, pixelRatio = globalThis.devicePixelRatio || 1,
  selectionColor = '#00ffff', selectionRadius = 4, ringWidth = 2 } = {}) {
  if (typeof coordinates?.worldToScreen !== 'function') throw new TypeError('coordinates must project world positions');
  if (!(Number.isFinite(pixelRatio) && pixelRatio > 0)) throw new RangeError('pixelRatio must be positive');
  const scene = createRetainedGeometryScene();
  let frame = null;
  let meshes = [];
  let selected = new Set();

  function replace(next) {
    if (!next || typeof next.frame !== 'string' || !Array.isArray(next.meshes)) throw new TypeError('retained scene requires a frame and meshes');
    const ids = new Set();
    const values = next.meshes.filter(mesh => mesh.visible !== false).map(mesh => {
      if (mesh.type !== 'field_mesh') throw new TypeError('only compiler field_mesh geometry is supported');
      if (typeof mesh.id !== 'string' || !mesh.id || ids.has(mesh.id)) throw new TypeError('mesh ids must be unique');
      ids.add(mesh.id);
      const vertices = mesh.vertices;
      if ((!Array.isArray(vertices) && !(vertices instanceof Float32Array)) || vertices.length % 10 || !Array.from(vertices).every(Number.isFinite)) throw new TypeError('compiler vertices require finite position/normal/color records');
      const points = Array.from({length: vertices.length / 10}, (_, index) => Array.from(vertices.slice(index * 10, index * 10 + 3)));
      const colors = points.map((_, index) => Array.from(vertices.slice(index * 10 + 6, index * 10 + 10)));
      const topology = mesh.topology;
      const indices = Array.from(mesh.indices || []);
      if (!['line-list', 'line-strip', 'triangle-list', 'point-list'].includes(topology)) throw new TypeError('unsupported compiler topology');
      if (indices.some(index => !Number.isSafeInteger(index) || index < 0 || index >= points.length)) throw new RangeError('compiler index is outside vertex storage');
      if (topology === 'line-list' && indices.length % 2 || topology === 'triangle-list' && indices.length % 3) throw new RangeError('incomplete compiler primitive indices');
      return {id: mesh.id, pickable: mesh.pickable !== false, points, colors, indices, topology, sizeSpace:mesh.marker_space || 'pixel', width: mesh.edge_width ?? 2, radius: (mesh.vertex_size ?? mesh.point_size ?? 14) / 2};
    });
    if (frame !== next.frame) selected = new Set();
    frame = next.frame;
    meshes = values;
    selected = new Set([...selected].filter(id => ids.has(id)));
  }

  function projected(mesh) {
    return mesh.points.map(point => coordinates.worldToScreen(point).map(value => value * pixelRatio));
  }

  function pixelSize(mesh, size) {
    if (mesh.sizeSpace !== 'world') return size * pixelRatio;
    const state = coordinates.snapshot?.();
    const scale = state?.transform?.scale;
    const pixelsPerUnit = scale ? Math.sqrt(Math.abs(scale[0] * scale[1]))
      : state?.camera?.ortho_scale ? state.viewport.height / (2 * state.camera.ortho_scale) : null;
    if (!(Number.isFinite(pixelsPerUnit) && pixelsPerUnit > 0)) throw new TypeError('world marker size requires a supported coordinate view');
    return size * pixelsPerUnit * pixelRatio;
  }

  function segments(mesh) {
    const result = [];
    const indices = mesh.indices;
    if (mesh.topology === 'line-list') for (let i = 0; i < indices.length; i += 2) result.push([indices[i],indices[i+1]]);
    if (mesh.topology === 'line-strip') for (let i = 1; i < indices.length; i++) result.push([indices[i-1],indices[i]]);
    return result;
  }

  function render() {
    scene.beginFrame();
    for (const mesh of meshes) {
      const points = projected(mesh);
      for (const [index, [from, to]] of segments(mesh).entries()) {
        const path = [points[from], points[to]];
        scene.path(frame, `${mesh.id}:${index}`, path, pixelSize(mesh,mesh.width), [{offset:0,color:mesh.colors[from]},{offset:1,color:mesh.colors[to]}]);
      }
      if (mesh.topology === 'triangle-list') for (let i = 0; i < mesh.indices.length; i += 3) {
        const indices = mesh.indices.slice(i,i+3);
        const triangle = indices.map(index => points[index]);
        scene.primitive(frame, `${mesh.id}:${i}`, {kind:'face', points:triangle, colors:indices.map(index => mesh.colors[index])});
      }
      if (mesh.topology === 'point-list') for (const index of mesh.indices) {
        scene.primitive(frame, `${mesh.id}:${index}`, {kind:'vertex',center:points[index],radius:pixelSize(mesh,mesh.radius),color:mesh.colors[index]});
        if (selected.has(mesh.id)) scene.ring(frame, `${mesh.id}:${index}:selected`, points[index], pixelSize(mesh,mesh.radius) + selectionRadius * pixelRatio, ringWidth * pixelRatio, selectionColor, {selection:true});
      }
      if (selected.has(mesh.id)) for (const [index,path] of contourPaths(mesh,segments(mesh)).entries()) {
        scene.selectionContour(frame, `${mesh.id}:outline:${index}`, path.map(vertex=>points[vertex]), selectionColor, pixelRatio, {selectionRadius,ringWidth});
      }
    }
    return scene.commit(renderer);
  }

  function selectAt(point, { tolerance = 7, additive = false } = {}) {
    if (!Array.isArray(point) || point.length !== 2 || !point.every(Number.isFinite) || !Number.isFinite(tolerance) || tolerance < 0) throw new TypeError('selection needs a finite screen point and nonnegative tolerance');
    const screen = point.map(value => value * pixelRatio);
    let hit = null;
    let best = tolerance * pixelRatio;
    for (const mesh of meshes) {
      if (!mesh.pickable) continue;
      const points = projected(mesh);
      const distances = segments(mesh).map(([from,to]) => distanceToSegment(screen,points[from],points[to]));
      if (mesh.topology === 'point-list') distances.push(...mesh.indices.map(index => Math.max(0,Math.hypot(screen[0]-points[index][0],screen[1]-points[index][1])-pixelSize(mesh,mesh.radius))));
      if (mesh.topology === 'triangle-list') for (let i=0;i<mesh.indices.length;i+=3) {
        const triangle = mesh.indices.slice(i,i+3).map(index => points[index]);
        distances.push(insideTriangle(screen, triangle) ? 0 : Math.min(...triangle.map((from,index) => distanceToSegment(screen,from,triangle[(index+1)%3]))));
      }
      const distance = Math.min(...distances);
      if (distance <= best) { hit = mesh.id; best = distance; }
    }
    if (!additive) selected.clear();
    if (hit) selected.add(hit);
    return selection();
  }

  function selection() { return Object.freeze([...selected]); }
  function clearSelection() { selected.clear(); }
  return Object.freeze({replace, replaceArena: packet => replace(materializeRetainedSceneArena(packet)), render, selectAt, selection, clearSelection, invalidate:scene.invalidate});
}

function distanceToSegment(point, from, to) {
  const dx=to[0]-from[0],dy=to[1]-from[1];
  const length=dx*dx+dy*dy;
  const t=length ? Math.max(0,Math.min(1,((point[0]-from[0])*dx+(point[1]-from[1])*dy)/length)) : 0;
  return Math.hypot(point[0]-from[0]-t*dx,point[1]-from[1]-t*dy);
}

function insideTriangle(point, triangle) {
  const signs=triangle.map((a,index) => {const b=triangle[(index+1)%3]; return (b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0]);});
  return signs.some(value=>value>0) && !signs.some(value=>value<0) || signs.some(value=>value<0) && !signs.some(value=>value>0);
}

function contourPaths(mesh, lineSegments) {
  const edges = new Map();
  function append(from,to) {
    const key = from < to ? `${from}:${to}` : `${to}:${from}`;
    const entry = edges.get(key);
    if (entry) entry.count++;
    else edges.set(key,{from,to,count:1});
  }
  if (mesh.topology === 'triangle-list') {
    for (let i=0;i<mesh.indices.length;i+=3) {
      const [a,b,c]=mesh.indices.slice(i,i+3);
      append(a,b);append(b,c);append(c,a);
    }
    for (const [key,entry] of edges) if (entry.count!==1) edges.delete(key);
  } else for (const [from,to] of lineSegments) append(from,to);
  const adjacency=new Map();
  for (const [key,{from,to}] of edges) for (const vertex of [from,to]) {
    if (!adjacency.has(vertex)) adjacency.set(vertex,[]);
    adjacency.get(vertex).push(key);
  }
  const remaining=new Set(edges.keys());
  const paths=[];
  while (remaining.size) {
    const first=edges.get(remaining.values().next().value);
    const start=adjacency.get(first.from).length!==2 ? first.from : adjacency.get(first.to).length!==2 ? first.to : first.from;
    const path=[start];
    let current=start;
    while (true) {
      const key=adjacency.get(current).find(key=>remaining.has(key));
      if (!key) break;
      remaining.delete(key);
      const edge=edges.get(key);
      current=edge.from===current ? edge.to : edge.from;
      path.push(current);
      if (current===start || adjacency.get(current).length!==2) break;
    }
    if (path.length>1) paths.push(path);
  }
  return paths;
}
