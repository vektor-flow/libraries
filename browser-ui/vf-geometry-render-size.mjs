const DEFAULT_VERTEX_RADIUS_PX = 7;
const DEFAULT_EDGE_WIDTH_PX = 2;

export function vertexScreenRadius(properties = {}, projection = {}) {
  return screenSize({
    pixelValue: properties.vertexPxRadius,
    dataValue: properties.vertexRadius,
    fallbackPixels: DEFAULT_VERTEX_RADIUS_PX,
    ...projection
  });
}

export function edgeScreenWidth(properties = {}, projection = {}) {
  return screenSize({
    pixelValue: properties.edgePxWidth,
    dataValue: properties.edgeWidth,
    fallbackPixels: DEFAULT_EDGE_WIDTH_PX,
    ...projection
  });
}

export function vertexRenderPresentation(properties = {}, spatialDimension = 2) {
  return geometryRenderPresentation({
    spatialDimension,
    pixelValue: properties.vertexPxRadius,
    dataValue: properties.vertexRadius,
    flatShape: 'disk',
    spatialShape: 'sphere'
  });
}

export function edgeRenderPresentation(properties = {}, spatialDimension = 2) {
  return geometryRenderPresentation({
    spatialDimension,
    pixelValue: properties.edgePxWidth,
    dataValue: properties.edgeWidth,
    flatShape: 'line',
    spatialShape: 'tube'
  });
}

function geometryRenderPresentation({
  spatialDimension,
  pixelValue,
  dataValue,
  flatShape,
  spatialShape
}) {
  if (Number(spatialDimension) < 3) {
    return { shape: flatShape, renderMode: 'screen_geometry', sizeSpace: 'pixel' };
  }
  return {
    shape: spatialShape,
    renderMode: 'marker_impostor',
    sizeSpace: Number.isFinite(pixelValue) || !Number.isFinite(dataValue) ? 'pixel' : 'world'
  };
}

function screenSize({
  pixelValue,
  dataValue,
  fallbackPixels,
  pixelRatio = 1,
  dataLengthToPixels = () => 0
}) {
  if (Number.isFinite(pixelValue)) return Math.max(0, pixelValue) * pixelRatio;
  if (Number.isFinite(dataValue)) return Math.max(0, dataLengthToPixels(dataValue));
  return fallbackPixels * pixelRatio;
}
