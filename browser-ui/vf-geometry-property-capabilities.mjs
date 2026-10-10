const GEOMETRY = new Set(['p', 'x', 'y', 'z', 'v', 'vx', 'vy', 'vz', 'a', 'L',
  'vertex_px_radius', 'vertex_radius', 'edge_px_width', 'edge_width', 'c']);
const MASS = ['m', 'lambda_m', 'sigma_m', 'rho_m'];
const MODULE_PROPERTIES = {
  inertia: [...MASS, 'k', 'k_theta'],
  gravity: MASS,
  specialRelativity: MASS,
  rigidCollisions: [...MASS, 'k', 'k_theta', 'eta', 'nu', 'P'],
  em: [...MASS, 'q', 'lambda_q', 'sigma_q', 'rho_q', 'epsilon', 'mu', 'sigma_e', 'E', 'B', 'phi'],
  temperature: [...MASS, 'T', 'kappa', 'alpha', 'c_p', 'h', 'epsilon_rad'],
  light: ['epsilon', 'mu']
};

export function allowedGeometryProperties(descriptors, { physicsEnabled = false, physics = null } = {}) {
  const available = new Set(physicsEnabled && physics
    ? Object.entries(MODULE_PROPERTIES).filter(([module]) => physics[module]).flatMap(([, names]) => names)
    : []);
  return descriptors.filter(({ name }) => GEOMETRY.has(name)
    || physicsEnabled && (physics == null || available.has(name)));
}
