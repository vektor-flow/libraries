// Shared plot/symbolic/selection/PDF stroke contract. All submitted positions
// and widths are CSS viewport units. Only the raster backend applies DPR.
export const DEFAULT_PLOT_STROKE=Object.freeze({units:'css-pixel',width:2,gap:4,cap:'round',join:'round'});
export const STROKE_CONTRACT_VERSION='vf-stroke/1';
export const COVERAGE_POLICY=Object.freeze({kind:'area-samples',samplesPerAxis:4,maxSamplesPerAxis:8,resolve:'premultiplied-box',edgeCoordinates:'physical-ink',pdf:'vector-no-raster-coverage'});
const positive=(n,name)=>{if(!Number.isFinite(n)||n<=0)throw RangeError(name+' must be positive');return n};
export function strokeContext({coordinates,pixelRatio=1,worldToCssScale}={}) {
 positive(pixelRatio,'pixelRatio');
 let worldScaleAvailable=worldToCssScale!==undefined||!coordinates;
 if(worldToCssScale===undefined){const s=coordinates?.snapshot?.(),a=s?.transform?.scale;
  worldScaleAvailable=worldScaleAvailable||!!a||!!s?.camera?.ortho_scale;
  worldToCssScale=a?Math.sqrt(Math.abs(a[0]*a[1])):s?.camera?.ortho_scale?s.viewport.height/(2*s.camera.ortho_scale):1;}
 positive(worldToCssScale,'worldToCssScale');
 return Object.freeze({version:STROKE_CONTRACT_VERSION,worldToCssScale,worldScaleAvailable,pixelRatio,coordinateSpace:'css-pixel',worldWidthPolicy:'geometric-mean-isotropic',coverage:COVERAGE_POLICY});
}
export function resolveStroke({width,gap=0,units='world',cap='round',join='round'}={},context=strokeContext()) {
 positive(width,'stroke width');if(!Number.isFinite(gap)||gap<0)throw RangeError('stroke gap must be nonnegative');
 if(!['world','css-pixel'].includes(units))throw TypeError('explicit world or css-pixel stroke units required');
 if(!['round','butt','square'].includes(cap)||!['round','miter','bevel'].includes(join))throw TypeError('stroke cap/join unsupported');
 if(units==='world'&&!context.worldScaleAvailable)throw TypeError('world stroke requires an authentic camera scale');
 const scale=units==='world'?context.worldToCssScale:1,cssWidth=width*scale,cssGap=gap*scale;
 return Object.freeze({version:STROKE_CONTRACT_VERSION,units,width,gap,cap,join,cssWidth,cssGap,deviceWidth:cssWidth*context.pixelRatio,deviceGap:cssGap*context.pixelRatio,
  selectionInnerOffset:cssGap,selectionCenterOffset:cssGap+cssWidth/2,selectionOuterOffset:cssGap+cssWidth,context,
  // PDF receives this same projected ink; its output transform applies once.
  pdf:Object.freeze({width:cssWidth,cap,join,units:'css-pixel'}),
  tessellationToleranceCss:.125/context.pixelRatio});
}
export function circleSegments(radiusCss,context=strokeContext(),{maxSegments=4096}={}) {
 positive(radiusCss,'radius');const tolerance=.125/context.pixelRatio;
 const count=Math.max(12,Math.ceil(Math.PI/Math.acos(Math.max(-1,1-Math.min(tolerance,radiusCss)/radiusCss))));
 if(count>maxSegments)throw RangeError('stroke tessellation budget exceeded');return count;
}
// Source-level numerical oracle for box-filtered samples. GPU uses these exact
// centered locations in each device pixel; this is not evidence of pixels read.
export function areaSampleOffsets(samples=COVERAGE_POLICY.samplesPerAxis){
 if(!Number.isInteger(samples)||samples<1||samples>COVERAGE_POLICY.maxSamplesPerAxis)throw RangeError('area sample budget');
 return Object.freeze(Array.from({length:samples*samples},(_,i)=>Object.freeze([(i%samples+.5)/samples-.5,(Math.floor(i/samples)+.5)/samples-.5])));
}
export function signedDistanceCoverage(distanceDevice,halfWidthDevice,{samples=COVERAGE_POLICY.samplesPerAxis}={}) {
 if(!Number.isFinite(distanceDevice)||!Number.isFinite(halfWidthDevice)||halfWidthDevice<0)throw RangeError('finite signed edge distance required');
 return areaSampleOffsets(samples).reduce((n,[,y])=>n+(Math.abs(distanceDevice+y)<=halfWidthDevice?1:0),0)/(samples*samples);
}
