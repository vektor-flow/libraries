export function createSelectionContourMetrics({
  vertexRadius,
  gap = 4,
  ringWidth = 2
}) {
  assertPositiveFinite('vertexRadius', vertexRadius);
  assertNonNegativeFinite('gap', gap);
  assertPositiveFinite('ringWidth', ringWidth);

  const selectionRadius = vertexRadius + gap + ringWidth / 2;
  const outerRadius = selectionRadius + ringWidth / 2;
  const innerRadius = selectionRadius - ringWidth / 2;

  return Object.freeze({
    gap,
    ringWidth,
    selectionRadius,
    vertexRingRadius: selectionRadius,
    outerRadius,
    innerRadius,
    edgeOuterWidth: outerRadius * 2,
    edgeClearWidth: innerRadius * 2,
    faceOuterWidth: outerRadius * 2,
    faceClearWidth: innerRadius * 2
  });
}

export function createSelectionLayerPasses(geometry, metrics) {
  assertMetrics(metrics);

  if (geometry === 'vertex') {
    return Object.freeze([
      pass('stroke', 'source-over', {
        lineWidth: metrics.ringWidth,
        radius: metrics.selectionRadius
      })
    ]);
  }

  if (geometry === 'edge') {
    return Object.freeze([
      pass('stroke', 'source-over', { lineWidth: metrics.edgeOuterWidth }),
      pass('stroke', 'destination-out', { lineWidth: metrics.edgeClearWidth })
    ]);
  }

  if (geometry === 'face') {
    return Object.freeze([
      pass('stroke', 'source-over', { lineWidth: metrics.faceOuterWidth }),
      pass('stroke', 'destination-out', { lineWidth: metrics.faceClearWidth }),
      pass('fill', 'destination-out')
    ]);
  }

  throw new TypeError(`Unknown selection geometry: ${geometry}`);
}

export function renderSelectionLayer(
  context,
  {
    geometry,
    metrics,
    trace,
    color = '#78b7d3',
    pixelRatio = 1
  }
) {
  if (!context || typeof context !== 'object') {
    throw new TypeError('A selection-layer rendering context is required.');
  }
  if (typeof trace !== 'function') {
    throw new TypeError('A selection geometry trace function is required.');
  }
  assertPositiveFinite('pixelRatio', pixelRatio);

  const passes = createSelectionLayerPasses(geometry, metrics);
  context.save();
  context.lineJoin = 'round';
  context.lineCap = 'round';

  for (const layerPass of passes) {
    context.globalCompositeOperation = layerPass.composite;
    context.beginPath();
    trace(context, {
      ...layerPass,
      radius: layerPass.radius == null ? undefined : layerPass.radius * pixelRatio
    });

    if (layerPass.operation === 'stroke') {
      context.lineWidth = layerPass.lineWidth * pixelRatio;
      context.strokeStyle = color;
      context.stroke();
    } else {
      context.fill();
    }
  }

  context.restore();
}

function pass(operation, composite, values = {}) {
  return Object.freeze({ operation, composite, ...values });
}

function assertMetrics(metrics) {
  if (!metrics || typeof metrics !== 'object') {
    throw new TypeError('Selection contour metrics are required.');
  }
  assertPositiveFinite('selectionRadius', metrics.selectionRadius);
  assertPositiveFinite('ringWidth', metrics.ringWidth);
}

function assertPositiveFinite(name, value) {
  if (!Number.isFinite(value) || value <= 0) {
    throw new RangeError(`${name} must be a positive finite number.`);
  }
}

function assertNonNegativeFinite(name, value) {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError(`${name} must be a non-negative finite number.`);
  }
}

// Global extension of Platonic's source-over/destination-out contract. The caller
// supplies vector-unioned paths for ALL objects, not one canvas per path. Use a
// dedicated transparent selection layer; destination-out must not erase content.
export function renderMergedSelectionLayer(context,{outerPaths,innerPaths,color='#00ffff',pixelRatio=1}) {
  assertPositiveFinite('pixelRatio',pixelRatio);
  context.save();
  try {
    context.lineJoin='round';context.lineCap='round';
    for(const [paths,composite]of [[outerPaths,'source-over'],[innerPaths,'destination-out']]){
      context.globalCompositeOperation=composite;context.fillStyle=color;context.beginPath();
      for(const path of paths){if(!path.length)continue;context.moveTo(path[0][0]*pixelRatio,path[0][1]*pixelRatio);for(const p of path.slice(1))context.lineTo(p[0]*pixelRatio,p[1]*pixelRatio);context.closePath()}
      context.fill('evenodd');
    }
  }finally{context.restore()}
}
