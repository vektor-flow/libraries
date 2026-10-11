import { describe, it, expect } from 'vitest';
import { createRetainedPlotView } from '../../browser-ui/vf-retained-plot-view.mjs';
import { createCoordinateView } from '../../browser-ui/vf-coordinate-view.mjs';
import { materializeRetainedSceneArena } from '../../browser-ui/vf-retained-scene-arena.mjs';
import { stepInertialBodies } from 'vektor-flow/physics-engine';
import { readFileSync } from 'node:fs';

describe('compiled retained plot selection and animation', () => {
  function view() {
    const coordinates = createCoordinateView({bounds:{x:[-1,1],y:[-1,1]}});
    coordinates.resize(400,300);
    let packed;
    const renderer = {setPackedVertices(value) {packed = value}};
    const result = createRetainedPlotView({coordinates,renderer});
    return {result,coordinates,packed:()=>packed};
  }
  const mesh = (id='line',dy=0) => ({id,type:'field_mesh',topology:'line-list',vertices:new Float32Array([-1,dy,0,0,0,1,1,0,0,1,1,dy,0,0,0,1,0,0,1,1]),indices:new Uint32Array([0,1]),edge_width:2});
  it('selects compiled geometry with a visible contour and preserves its id after a frame update', () => {
    const {result,coordinates,packed} = view();
    result.replace({frame:'f',meshes:[mesh()]});
    result.render();
    const plain = packed().length;
    expect(result.selectAt(coordinates.worldToScreen([0,0]))).toEqual(['line']);
    result.render();
    expect(packed().length).toBeGreaterThan(plain);
    result.replace({frame:'f',meshes:[mesh('line',0.5)]});
    result.render();
    expect(result.selection()).toEqual(['line']);
    expect(result.selectAt(coordinates.worldToScreen([0,0]),{tolerance:1})).toEqual([]);
    expect(result.selectAt(coordinates.worldToScreen([0,0.5]))).toEqual(['line']);
  });
  it('does not close the ends of an open curve, and keeps vertex colors', () => {
    const {result,packed} = view();
    result.replace({frame:'f',meshes:[mesh()]});
    result.render();
    expect(packed().length).toBe(36);
    expect(Array.from(packed().slice(2,6))).toEqual([1,0,0,1]);
  });
  it('drops removed selected ids and rejects malformed packed geometry', () => {
    const {result,coordinates} = view();
    result.replace({frame:'f',meshes:[mesh()]});
    result.selectAt(coordinates.worldToScreen([0,0]));
    result.replace({frame:'f',meshes:[]});
    expect(result.selection()).toEqual([]);
    expect(()=>result.replace({frame:'f',meshes:[{...mesh(),indices:[0,20]}]})).toThrow(/index/i);
  });
  it('renders non-pickable geometry without allowing it to be selected', () => {
    const {result,coordinates,packed} = view();
    result.replace({frame:'f',meshes:[{...mesh(),pickable:false}]});
    result.render();
    expect(packed().length).toBe(36);
    expect(result.selectAt(coordinates.worldToScreen([0,0]))).toEqual([]);
  });
  it('allows dragging by default while honoring explicit opt-out', () => {
    const {result,coordinates} = view();
    const point = coordinates.worldToScreen([0,0]);
    result.replace({frame:'f',meshes:[mesh()]});
    expect(result.hitTest(point,{capability:'draggable'})?.id).toBe('line');
    result.replace({frame:'f',meshes:[{...mesh(),draggable:false}]});
    expect(result.hitTest(point,{capability:'draggable'})).toBeNull();
  });
  it.each([[false,false],[false,true],[true,false],[true,true]])(
    'keeps selectable=%s independent of draggable=%s', (selectable,draggable) => {
      const {result,coordinates,packed} = view();
      result.replace({frame:'f',meshes:[{...mesh(),selectable,draggable}]});
      result.render();
      expect(packed().length).toBe(36);
      const point=coordinates.worldToScreen([0,0]);
      expect(result.selectAt(point)).toEqual(selectable ? ['line'] : []);
      expect(result.hitTest(point,{capability:'draggable'})?.id ?? null).toBe(draggable ? 'line' : null);
    }
  );
  it('prunes selection when its stable id becomes non-selectable', () => {
    const {result,coordinates} = view();
    result.replace({frame:'f',meshes:[mesh()]});
    result.selectAt(coordinates.worldToScreen([0,0]));
    result.replace({frame:'f',meshes:[{...mesh(),selectable:false,draggable:true}]});
    expect(result.selection()).toEqual([]);
  });
  it('does not bridge separate explicit segments while drawing or selecting', () => {
    const {result,coordinates,packed} = view();
    const vertices=[[-1,0],[-0.5,0],[0.5,0],[1,0]].flatMap(([x,y])=>[x,y,0,0,0,1,1,0,0,1]);
    result.replace({frame:'f',meshes:[{...mesh(),vertices,indices:[0,1,2,3]}]});
    result.render();
    expect(packed().length).toBe(72);
    expect(result.selectAt(coordinates.worldToScreen([0,0]),{tolerance:1})).toEqual([]);
  });
  it('renders actual compiler add output, then follows upstream physics with the same selection', () => {
    const packet = JSON.parse(readFileSync(new URL('../fixtures/canonical-add-071.json', import.meta.url),'utf8'));
    packet.arena = Uint8Array.from(packet.arena);
    const {result,coordinates,packed} = view();
    result.replaceArena(packet);
    result.render();
    expect(packed().length).toBe(36);
    expect(result.selectAt(coordinates.worldToScreen([0,0]))).toEqual(['line']);
    const body = stepInertialBodies([{position:[0,0,0],momentum:[0,0,0],force:[0,2,0],mass:2,inertia:[[1,0,0],[0,1,0],[0,0,1]]}],1)[0];
    expect(body.position).toEqual([0,1,0]);
    const frame = materializeRetainedSceneArena(packet);
    frame.meshes[0].vertices = frame.meshes[0].vertices.slice();
    for (let i=1;i<frame.meshes[0].vertices.length;i+=10) frame.meshes[0].vertices[i]+=body.position[1];
    result.replace(frame);
    result.render();
    expect(result.selection()).toEqual(['line']);
    expect(result.selectAt(coordinates.worldToScreen([0,1]))).toEqual(['line']);
  });
  it('rejects compiler arena ranges outside the supplied packet', () => {
    const packet = JSON.parse(readFileSync(new URL('../fixtures/canonical-add-071.json', import.meta.url),'utf8'));
    packet.arena = Uint8Array.from(packet.arena);
    packet.metadata.scene.meshes[0].vertices.length = 100000;
    expect(()=>materializeRetainedSceneArena(packet)).toThrow(/range/);
  });
  it('preserves native World embedding size in data coordinates', () => {
    const {result,coordinates,packed} = view();
    const point = {...mesh(),topology:'point-list',indices:[0],vertex_size:0.7,marker_space:'world'};
    result.replace({frame:'f',meshes:[point]});
    result.render();
    const center = coordinates.worldToScreen([-1,0]);
    const expectedRadius = Math.abs(coordinates.worldToScreen([-0.65,0])[0]-center[0]);
    const xs = Array.from(packed()).filter((_,index)=>index%6===0);
    expect(Math.max(...xs)-center[0]).toBeCloseTo(expectedRadius,4);
  });
  it('marks a triangulated face boundary without marking its internal diagonal', () => {
    const {result,coordinates,packed} = view();
    const corners=[[-0.5,-0.5],[0.5,-0.5],[0.5,0.5],[-0.5,0.5]];
    const vertices=corners.flatMap(([x,y])=>[x,y,0,0,0,1,1,1,1,1]);
    result.replace({frame:'f',meshes:[{...mesh('face'),vertices,topology:'triangle-list',indices:[0,1,2,0,2,3]}]});
    result.selectAt(coordinates.worldToScreen([0,0]));
    result.render();
    const cornersScreen=corners.map(coordinates.worldToScreen);
    const xs=cornersScreen.map(p=>p[0]),ys=cornersScreen.map(p=>p[1]);
    const cyan=[];
    for(let i=0;i<packed().length;i+=18) {
      if([0,6,12].every(offset=>packed()[i+offset+2]===0 && packed()[i+offset+3]===1 && packed()[i+offset+4]===1))
        cyan.push([(packed()[i]+packed()[i+6]+packed()[i+12])/3,(packed()[i+1]+packed()[i+7]+packed()[i+13])/3]);
    }
    expect(cyan.length).toBeGreaterThan(0);
    expect(cyan.every(([x,y])=>x<=Math.min(...xs)+2 || x>=Math.max(...xs)-2 || y<=Math.min(...ys)+2 || y>=Math.max(...ys)-2)).toBe(true);
  });
});
