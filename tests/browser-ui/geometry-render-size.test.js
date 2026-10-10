import { describe, expect, it } from 'vitest';
import {
  edgeRenderPresentation,
  edgeScreenWidth,
  vertexRenderPresentation,
  vertexScreenRadius
} from '../../browser-ui/vf-geometry-render-size.mjs';

describe('geometry render sizing', () => {
  const projection = {
    pixelRatio: 2,
    dataLengthToPixels: (length) => length * 40
  };

  it('keeps pixel vertex radius zoom-independent and gives it precedence', () => {
    expect(vertexScreenRadius({ vertexPxRadius: 6, vertexRadius: 3 }, projection)).toBe(12);
    expect(vertexScreenRadius({ vertexRadius: 0.25 }, projection)).toBe(10);
    expect(vertexScreenRadius({}, projection)).toBe(14);
  });

  it('keeps pixel edge width zoom-independent and gives it precedence', () => {
    expect(edgeScreenWidth({ edgePxWidth: 3, edgeWidth: 2 }, projection)).toBe(6);
    expect(edgeScreenWidth({ edgeWidth: 0.1 }, projection)).toBe(4);
    expect(edgeScreenWidth({}, projection)).toBe(4);
  });

  it('maps 3D pixel and data sizes onto sphere and tube impostors', () => {
    expect(vertexRenderPresentation({ vertexPxRadius: 6 }, 3)).toEqual({
      shape: 'sphere', renderMode: 'marker_impostor', sizeSpace: 'pixel'
    });
    expect(vertexRenderPresentation({ vertexRadius: 0.25 }, 3)).toEqual({
      shape: 'sphere', renderMode: 'marker_impostor', sizeSpace: 'world'
    });
    expect(edgeRenderPresentation({ edgePxWidth: 3 }, 3)).toEqual({
      shape: 'tube', renderMode: 'marker_impostor', sizeSpace: 'pixel'
    });
    expect(edgeRenderPresentation({ edgeWidth: 0.1 }, 3)).toEqual({
      shape: 'tube', renderMode: 'marker_impostor', sizeSpace: 'world'
    });
  });
});
