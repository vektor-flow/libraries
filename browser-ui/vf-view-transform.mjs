import vkfMath from 'vektor-flow/ui-math';

const { add2, matVec2, sub2 } = vkfMath;

export function normalizeVkfViewTransform(value = {}) {
  const scale = Array.isArray(value.scale)
    ? [positive(value.scale[0], 1), positive(value.scale[1], positive(value.scale[0], 1))]
    : [positive(value.scale, 1), positive(value.scale, 1)];
  return Object.freeze({
    position: Object.freeze(point(value.position)),
    scale: Object.freeze(scale),
    rotation: finite(value.rotation, 0)
  });
}

export function transformVkfViewPoint(local, value) {
  const transform = normalizeVkfViewTransform(value);
  return add2(
    transform.position,
    matVec2(rotationMatrix(transform.rotation), [
      finite(local?.[0], 0) * transform.scale[0],
      finite(local?.[1], 0) * transform.scale[1]
    ])
  );
}

export function inverseTransformVkfViewPoint(world, value) {
  const transform = normalizeVkfViewTransform(value);
  const translated = sub2(point(world), transform.position);
  const unrotated = matVec2(rotationMatrix(-transform.rotation), translated);
  return [
    unrotated[0] / transform.scale[0],
    unrotated[1] / transform.scale[1]
  ];
}

export function applyVkfViewGesture(value, gesture = {}) {
  const transform = normalizeVkfViewTransform(value);
  const origin = point(gesture.origin);
  const translation = point(gesture.translation);
  const scale = positive(gesture.scale, 1);
  const rotation = finite(gesture.rotation, 0);
  const relative = sub2(transform.position, origin);
  const moved = matVec2(rotationMatrix(rotation), [
    relative[0] * scale,
    relative[1] * scale
  ]);
  return normalizeVkfViewTransform({
    position: add2(add2(origin, moved), translation),
    scale: [transform.scale[0] * scale, transform.scale[1] * scale],
    rotation: transform.rotation + rotation
  });
}

function rotationMatrix(angle) {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return [cosine, -sine, sine, cosine];
}

function point(value) {
  return [finite(value?.[0], 0), finite(value?.[1], 0)];
}

function finite(value, fallback) {
  return Number.isFinite(Number(value)) ? Number(value) : fallback;
}

function positive(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : fallback;
}
