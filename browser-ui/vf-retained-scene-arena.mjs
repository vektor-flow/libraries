// Zero-copy compiler ABI views, following VfDisplay's retained arena contract.
// No expression evaluation, geometry generation or physics occurs here.
export function materializeRetainedSceneArena(packet) {
  const schema = 'vektor-flow/retained-scene-arena';
  if (packet?.schema !== schema || packet.version !== 1 || packet.metadata?.schema !== schema || packet.metadata.version !== 1) throw new TypeError('unsupported retained scene arena schema');
  if (!(packet.arena instanceof Uint8Array)) throw new TypeError('retained arena bytes must be Uint8Array');
  const source = packet.metadata.scene;
  if (!source || typeof source.frame !== 'string' || !source.frame) throw new TypeError('retained arena requires a Frame identity');
  const scene = {...source};
  for (const collection of ['meshes', 'surfaces']) {
    if (source[collection] == null) continue;
    if (!Array.isArray(source[collection])) throw new TypeError('retained geometry collection must be an array');
    scene[collection] = source[collection].map(geometry => ({
      ...geometry,
      vertices: view(geometry.vertices, packet.arena, 'float32'),
      indices: view(geometry.indices, packet.arena, 'uint32')
    }));
  }
  return scene;
}

function view(reference, arena, storage) {
  if (!reference || reference.storage !== storage) throw new TypeError('unsupported retained arena storage');
  const offset = reference.byte_offset, length = reference.length;
  if (!Number.isSafeInteger(offset) || offset < 0 || offset % 4 || !Number.isSafeInteger(length) || length < 0 || offset + length * 4 > arena.byteLength) throw new RangeError('invalid retained arena range');
  const absolute = arena.byteOffset + offset;
  if (absolute % 4) throw new RangeError('retained arena view is not aligned');
  return storage === 'float32' ? new Float32Array(arena.buffer, absolute, length) : new Uint32Array(arena.buffer, absolute, length);
}
