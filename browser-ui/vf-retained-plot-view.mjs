import {strokeContext,resolveStroke,circleSegments,DEFAULT_PLOT_STROKE} from './vf-stroke-contract.mjs';
import {curveContract,drawCurves} from './vf-analytic-curves.mjs';
import {createSelectionController} from './vf-selection-controller.mjs';
import {nativeGeometrySelectionObject} from './vf-selection-adapters.mjs';
import { createRetainedGeometryScene } from './vf-retained-geometry-scene.mjs';
import {createRetainedTimeProjection} from './vf-retained-layer-time.mjs';

// Presentation of compiler-owned field_mesh values. Geometry and physics are
// supplied by Frame.add/World; this view never evaluates source or steps a World.
export function createRetainedPlotView({ coordinates, renderer, pixelRatio = ()=>globalThis.devicePixelRatio || 1,
  selectionColor = '#00ffff', selectionRadius = DEFAULT_PLOT_STROKE.gap+DEFAULT_PLOT_STROKE.width/2, ringWidth = DEFAULT_PLOT_STROKE.width, selectionStroke = null } = {}) {
  if (typeof coordinates?.worldToScreen !== 'function') throw new TypeError('coordinates must project world positions');
  const deviceRatio=()=>{const r=typeof pixelRatio==='function'?pixelRatio():pixelRatio;if(!Number.isFinite(r)||r<=0)throw RangeError('pixelRatio must be positive');return r};deviceRatio();
  const scene = createRetainedGeometryScene();
  let frame = null;
  let meshes = [];
  let nativeLabelLayer=null,labelObjects=[];
  function syncNativeLabels(){const objects=nativeLabelLayer?.selectionObjects()??[];if(objects.length===labelObjects.length&&objects.every((v,i)=>v===labelObjects[i]))return;labelObjects=objects;selectionController.registerObjects("native-label-layer",objects);}
  let arenaProjection = null,coordinateRevision=null;
  function replaceArena(packet,{elapsedSeconds=0,layerTimeOffsets={}}={}) {
    const projection=arenaProjection?.packet===packet?arenaProjection:createRetainedTimeProjection(packet);
    const projected=projection.at(elapsedSeconds,{layerTimeOffsets});
    replace(projected.scene);arenaProjection=projection;
  }
  const getStrokeContext=()=>strokeContext({coordinates,pixelRatio:deviceRatio()});
  const selectionController=createSelectionController({selectionColor,selectionRadius,ringWidth,stroke:selectionStroke,getStrokeContext});

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
      for (const name of ['selectable','draggable']) {
        if (name in mesh && typeof mesh[name] !== 'boolean') throw new TypeError(`mesh ${name} must be a boolean`);
      }
      const curve = mesh.analytic_curve === undefined ? null : curveContract(mesh.analytic_curve);
      if (curve && (mesh.selectable || mesh.draggable || !['line-list','line-strip'].includes(topology))) throw TypeError('analytic curve interaction/topology unsupported');
      return {curve, id: mesh.id, pickable: mesh.pickable !== false, selectable:mesh.selectable === true, draggable:mesh.draggable === true, points, colors, indices, topology, sizeSpace:mesh.marker_space || 'pixel', width: mesh.edge_width ?? 2, radius: (mesh.vertex_size ?? mesh.point_size ?? 14) / 2};
    });
    frame = next.frame;
    meshes = values;
    selectionController.replace(frame, values.filter(mesh=>mesh.pickable&&mesh.selectable).map(mesh=>({
      ...nativeGeometrySelectionObject({objectId:mesh.id,points:mesh.points,indices:mesh.indices,topology:mesh.topology,coordinates,
        width:()=>pixelSize(mesh,mesh.width),radius:()=>pixelSize(mesh,mesh.radius)}),
      pickable:mesh.pickable,selectable:mesh.selectable,
      // Preserve the retained picker's nearest/tie/tolerance semantics.
      hitTest:(point,options)=>hitTest(point,options)?.id===mesh.id
    })));
  }

  function projected(mesh) {
    return mesh.points.map(point => coordinates.worldToScreen(point));
  }

  function pixelSize(mesh,size) {
    if(size===0)return 0;
    return resolveStroke({width:size,units:mesh.sizeSpace==='world'?'world':'css-pixel'},getStrokeContext()).cssWidth;
  }

  function segments(mesh) {
    const result = [];
    const indices = mesh.indices;
    if (mesh.topology === 'line-list') for (let i = 0; i < indices.length; i += 2) result.push([indices[i],indices[i+1]]);
    if (mesh.topology === 'line-strip') for (let i = 1; i < indices.length; i++) result.push([indices[i-1],indices[i]]);
    return result;
  }

  function render() {
    const revision=JSON.stringify([coordinates.snapshot?.()??coordinates.affineWorldToScreen?.()??null,deviceRatio()]);
    if(coordinateRevision!==null&&revision!==coordinateRevision)selectionController.invalidateCoordinates();
    coordinateRevision=revision;scene.beginFrame();
    for (const mesh of meshes) {
      const points = projected(mesh);
      if (mesh.curve) {
        drawCurves(scene,frame,mesh.id,mesh.curve,{matrix:coordinates.affineWorldToScreen?.(),pixelRatio:1,devicePixelRatio:deviceRatio()},pixelSize(mesh,mesh.width));
        continue;
      }
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
        scene.primitive(frame, `${mesh.id}:${index}`, {kind:'vertex',center:points[index],radius:pixelSize(mesh,mesh.radius),segments:circleSegments(pixelSize(mesh,mesh.radius),getStrokeContext()),color:mesh.colors[index]});

      }
    }
    nativeLabelLayer?.render(scene,frame);syncNativeLabels();
    selectionController.render(scene,{pixelRatio:deviceRatio(),coordinateSpace:'css-pixel'});
    return scene.commit(renderer);
  }

  function hitTest(point, { tolerance = 7, capability = 'selectable' } = {}) {
    if (!Array.isArray(point) || point.length !== 2 || !point.every(Number.isFinite) || !Number.isFinite(tolerance) || tolerance < 0) throw new TypeError('selection needs a finite screen point and nonnegative tolerance');
    if (!['selectable','draggable'].includes(capability)) throw new TypeError('hit capability must be selectable or draggable');
    const screen = point;
    let hit = null;
    let best = tolerance;
    for (const mesh of meshes) {
      if (!mesh.pickable || !mesh[capability]) continue;
      const points = projected(mesh);
      const distances = segments(mesh).map(([from,to]) => distanceToSegment(screen,points[from],points[to]));
      if (mesh.topology === 'point-list') distances.push(...mesh.indices.map(index => Math.max(0,Math.hypot(screen[0]-points[index][0],screen[1]-points[index][1])-pixelSize(mesh,mesh.radius))));
      if (mesh.topology === 'triangle-list') for (let i=0;i<mesh.indices.length;i+=3) {
        const triangle = mesh.indices.slice(i,i+3).map(index => points[index]);
        distances.push(insideTriangle(screen, triangle) ? 0 : Math.min(...triangle.map((from,index) => distanceToSegment(screen,from,triangle[(index+1)%3]))));
      }
      const distance = Math.min(...distances);
      if (distance <= best) { hit = mesh; best = distance; }
    }
    return hit ? Object.freeze({id:hit.id,selectable:hit.selectable,draggable:hit.draggable}) : null;
  }

  const {selectAt,selectRectangle,selection,clearSelection}=selectionController;
  return Object.freeze({setNativeLabelLayer(layer){nativeLabelLayer=layer;syncNativeLabels();},replace, replaceArena, render, hitTest, selectAt, selectRectangle, selection, clearSelection, selectionController, registerSelectionObjects:selectionController.registerObjects, removeSelectionObjects:selectionController.removeObjects, strokeContext:getStrokeContext, dispose:selectionController.dispose, invalidate(){selectionController.invalidateCoordinates();scene.invalidate()}});
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

