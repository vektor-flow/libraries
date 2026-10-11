import {it,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import bridge from 'vektor-flow/web/vf-ui/vf-compiled-runtime-bridge.js';
import {createCoordinateView} from '../../browser-ui/vf-coordinate-view.mjs';
import {createCoordinateView3d} from '../../browser-ui/vf-coordinate-view-3d.mjs';
import {createNativePlotInteraction} from '../../browser-ui/vf-native-plot-interaction.mjs';

function native() {
  const root=new URL('../fixtures/native-drag-072/',import.meta.url);
  const runtime=bridge.instantiateWasmRuntime({bytes:readFileSync(new URL('position.wasm',root)),manifest:JSON.parse(readFileSync(new URL('manifest.json',root),'utf8'))});
  runtime.init();return runtime;
}
const fields={x:'x',y:'y',z:'z'};
it('writes declared native input bindings without writing retained geometry',()=>{
  const runtime=native(),coordinates=createCoordinateView({bounds:{x:[-5,5],y:[-5,5]}});
  coordinates.resize(400,400);
  const interaction=createNativePlotInteraction({targets:{point:{runtime,inputFields:fields,positionFields:fields,quantized:true,referenceSystem:'world'}}});
  expect(interaction.begin('point',coordinates.worldToScreen([0,0]),coordinates,{dimensions:2})).toBe(true);
  interaction.move(coordinates.worldToScreen([2,3]));
  expect(runtime.readState()).toEqual({x:2,y:3,z:0});
  interaction.end();
  expect(interaction.begin('unbound',coordinates.worldToScreen([0,0]),coordinates,{dimensions:2})).toBe(false);
});
it('uses a declared world plane and local reference axes for 3D dragging',()=>{
  const runtime=native(),coordinates=createCoordinateView3d({bounds:{x:[-5,5],y:[-5,5],z:[-5,5]}});
  coordinates.resize(600,400);
  const referenceSystem={origin:[1,0,2],basis:[[0,1,0],[-1,0,0],[0,0,1]]};
  const interaction=createNativePlotInteraction({targets:{point:{runtime,inputFields:fields,positionFields:fields,quantized:true,referenceSystem,constraint:{kind:'plane',point:[0,0,2],normal:[0,0,1]}}}});
  expect(interaction.begin('point',coordinates.worldToScreen([1,0,2]),coordinates,{dimensions:3})).toBe(true);
  interaction.move(coordinates.worldToScreen([1,2,2]));
  const state=runtime.readState();expect(state.x).toBeCloseTo(2,5);expect(state.y).toBe(0);expect(state.z).toBe(0);
});
it('requires a declared 3D constraint and explicit integer quantization',()=>{
  const runtime=native(),coordinates=createCoordinateView3d();coordinates.resize(600,400);
  expect(()=>createNativePlotInteraction({targets:{point:{runtime,inputFields:fields,positionFields:fields,referenceSystem:'world'}}})).toThrow(/quantized/);
  const interaction=createNativePlotInteraction({targets:{point:{runtime,inputFields:fields,positionFields:fields,quantized:true,referenceSystem:'world'}}});
  expect(interaction.begin('point',[300,200],coordinates,{dimensions:3})).toBe(false);
});

it('rebases a camera-facing grab without camera movement changing native position',()=>{
  const runtime=native(),coordinates=createCoordinateView3d();coordinates.resize(600,400);
  const interaction=createNativePlotInteraction({targets:{point:{runtime,inputFields:fields,
    positionFields:fields,quantized:true,referenceSystem:'world',
    constraint:{kind:'camera-plane',point:[0,0,0]}}}});
  const screen=coordinates.worldToScreen([0,0,0]);
  expect(interaction.begin('point',screen,coordinates,{dimensions:3})).toBe(true);
  coordinates.pan(screen,[screen[0]+80,screen[1]+40]);
  interaction.move(screen);
  expect(runtime.readState()).toEqual({x:0,y:0,z:0});
  interaction.move([screen[0]+120,screen[1]]);
  expect(Object.values(runtime.readState()).some(value=>value!==0)).toBe(true);
});
