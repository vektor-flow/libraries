"""Current CPU reference qualification/provenance; no native fluid-port claim.
Snapshot manifests hash EVERY value/array of the complete in-memory snapshot.
They are evidence manifests, not partial checkpoint files or restorable archives.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import numpy as np
import scipy
from ns_reference import Smoke, Config, strain_viscosity
from parcels import ParcelSmoke
from demo_case import make_demo

ROOT = Path(__file__).parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot_manifest(value):
    """Typed, complete canonical provenance, including masks/control/RNG state."""
    if isinstance(value, np.ndarray):
        raw = np.ascontiguousarray(value).tobytes()
        return {'kind': 'ndarray', 'dtype': value.dtype.str,
                'shape': list(value.shape), 'order': 'C', 'bytes': len(raw),
                'sha256': sha(raw)}
    if isinstance(value, np.generic):
        return snapshot_manifest(value.item())
    if isinstance(value, dict):
        return {k: snapshot_manifest(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return {'kind': 'tuple', 'items': [snapshot_manifest(v) for v in value]}
    if isinstance(value, list):
        return [snapshot_manifest(v) for v in value]
    if isinstance(value, float):
        if not np.isfinite(value):
            raise ValueError('Nonfinite snapshot scalar')
        return {'kind': 'binary64', 'hex': value.hex()}
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError('Unspecified snapshot value type: ' + str(type(value)))


def snapshot_evidence(snapshot):
    manifest = snapshot_manifest(snapshot)
    raw = json.dumps(manifest, sort_keys=True, separators=(',', ':'),
                     allow_nan=False).encode()
    return {'sha256': sha(raw), 'manifest': manifest,
            'meaning': 'Complete in-memory snapshot provenance; hashes, not array payloads; NOT a restorable checkpoint archive'}


def source_provenance():
    paths = sorted([*ROOT.glob('*.py'), ROOT/'PHYSICS.txt', ROOT/'SDF_COUPLING.txt'])
    return {p.name: {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
            for p in paths}


def flow_metrics(s):
    uc = np.array([(s.u[i]+np.roll(s.u[i], -1, axis=i))/2 for i in range(3)])
    grad = np.array([[(np.roll(uc[i], -1, axis=j)-np.roll(uc[i], 1, axis=j))/(2*s.h[j])
                      for j in range(3)] for i in range(3)])
    omega = np.array([grad[2, 1]-grad[1, 2], grad[0, 2]-grad[2, 0], grad[1, 0]-grad[0, 1]])
    stretch = np.einsum('jxyz,ijxyz->ixyz', omega, grad)
    eddy = strain_viscosity(s.u, s.h, s.cfg.nu, s.cfg.cs)-s.cfg.nu
    return {'rmsSpeed': float(np.sqrt(np.mean(uc**2))),
            'rmsVorticity': float(np.sqrt(np.mean(omega**2))),
            'rmsVorticityStretching': float(np.sqrt(np.mean(stretch**2))),
            'maxSubgridViscosity': float(eddy.max()),
            'mixedMassFraction': float(np.minimum(s.c[0], s.c[1]).sum()*s.dv/max(1e-20, s.mass().sum()))}


def run_case(s, frames, name, continue_hold=False):
    fps = 60
    initial = s.mass().copy()
    initial_snapshot = snapshot_evidence(s.snapshot())
    initial_time = s.time
    timings, rows = [], []
    largest_div = largest_stage_div = largest_mass = largest_courant = 0.
    minimum = float(s.c.min())
    started = time.perf_counter()
    for frame in range(1, frames+1):
        tick = time.perf_counter()
        s.advance_to(initial_time+frame/fps)
        timings.append((time.perf_counter()-tick)*1000)
        largest_div = max(largest_div, s.last['divergenceResidualMax'])
        largest_stage_div = max(largest_stage_div, s.last['stageDivergenceResidualMax'])
        largest_courant = max(largest_courant, s.last['stageTransportCourant'], s.last['finalTransportCourant'])
        largest_mass = max(largest_mass, float(np.max(np.abs(s.mass()+s.deposited-initial))))
        minimum = min(minimum, float(s.c.min()), s.last['stageMinimum'])
        if frame % fps == 0:
            rows.append({'time': s.time, **flow_metrics(s),
                         'gasMass': s.mass().tolist(), 'depositedMass': s.deposited.tolist()})
            print('FRAME', name, frame, 'ms', round(timings[-1], 2), 'massResidual', largest_mass, flush=True)
    wall = time.perf_counter()-started
    final_snapshot = snapshot_evidence(s.snapshot())
    assert largest_div < 1e-9 and largest_stage_div < 1e-9
    assert largest_mass < 1e-11 and minimum >= -1e-11
    assert largest_courant <= s.cfg.cfl*(1+1e-10)
    record = {'case': name, 'config': asdict(s.cfg), 'initialization': 'make_demo(count=0), seed701' if name == 'moving-collector' else 'Smoke.plumes seed701; collector disabled',
              'shape': s.shape, 'cells': int(np.prod(s.shape)), 'frameRate': fps,
              'observationPolicy': 'absolute advance_to(frame/fps); fixed outer ticks; adaptive subdivisions only within complete ticks',
              'simulatedSeconds': s.time-initial_time, 'observationNs': s.observation_ns,
              'wallSeconds': wall, 'realTimeRatio': (s.time-initial_time)/wall,
              'frameMsP50': float(np.percentile(timings, 50)), 'frameMsP95': float(np.percentile(timings, 95)),
              'substeps': s.steps, 'ticks': s.ticks,
              'maximumDivergenceResidual': largest_div,
              'maximumStageDivergenceResidual': largest_stage_div,
              'maximumTransportCourant': largest_courant,
              'maximumSpeciesMassResidual': largest_mass, 'minimumConcentration': minimum,
              'initialMass': initial.tolist(), 'finalGasMass': s.mass().tolist(),
              'finalDepositedMass': s.deposited.tolist(),
              'capturedFraction': float(s.deposited.sum()/initial.sum()),
              'samples': rows, 'initialSnapshot': initial_snapshot, 'finalSnapshot': final_snapshot}
    if continue_hold:
        before = s.u.copy()
        clone = Smoke.from_snapshot(s.snapshot())
        assert snapshot_evidence(clone.snapshot())['sha256'] == final_snapshot['sha256']
        target = initial_time+frames/fps+.75
        s.advance_to(target)
        clone.advance_to(target)
        after = snapshot_evidence(s.snapshot())
        assert after['sha256'] == snapshot_evidence(clone.snapshot())['sha256']
        delta = float(np.max(np.abs(s.u-before)))
        assert delta > 0
        assert np.max(np.abs(s.mass()+s.deposited-initial)) < 1e-11
        record['blankHoldContinuation'] = {'seconds': .75, 'targetAbsoluteSeconds': target,
            'sameCompleteSnapshotReplayExact': True, 'maximumVelocityDelta': delta,
            'gasMassRetained': s.mass().tolist(), 'depositedMassRetained': s.deposited.tolist(),
            'completeSnapshot': after}
    return record


def parcel_snapshot_check():
    s = ParcelSmoke.from_fluid(make_demo(shape=(8, 8, 4), count=0), count=2048, seed=702)
    initial_grid, initial_probe = s.mass().copy(), s.parcel_mass().copy()
    s.advance_to(.2)
    saved = snapshot_evidence(s.snapshot())
    clone = ParcelSmoke.from_snapshot(s.snapshot())
    assert saved['sha256'] == snapshot_evidence(clone.snapshot())['sha256']
    s.advance_to(.4)
    clone.advance_to(.4)
    final = snapshot_evidence(s.snapshot())
    assert final['sha256'] == snapshot_evidence(clone.snapshot())['sha256']
    assert np.max(np.abs(s.mass()+s.deposited-initial_grid)) < 1e-11
    assert np.max(np.abs(s.parcel_mass()+s.parcel_deposited-initial_probe)) < 1e-11
    return {'sameCompleteSnapshotIncludingRngHazardReplayExact': True,
            'config': asdict(s.cfg), 'particleCount': len(s.alive),
            'massAuthority': 'continuum and probes independently approximate the same species; NEVER sum their masses',
            'savedSnapshot': saved, 'finalSnapshot': final}


def existing_visual_provenance():
    path = ROOT/'fluid-only.json'
    if not path.exists():
        return {'status': 'unavailable; no visual claim from this qualification'}
    data = json.loads(path.read_text())
    sources_match = all(sha((ROOT/name).read_bytes()) == digest for name, digest in data['sourceHashes'].items())
    binary = ROOT/'fluid-only.bin'
    binary_match = binary.exists() and sha(binary.read_bytes()) == data['dataSha256']
    return {'status': 'existing separately rendered visual data; NOT regenerated by this script',
            'metadataSha256': sha(path.read_bytes()), 'sourceHashesMatchCurrent': sources_match,
            'dataSha256': data['dataSha256'], 'dataBytes': data['dataBytes'], 'binaryVerified': binary_match,
            'config': data['config'], 'sourceHashes': data['sourceHashes'],
            'collectorActive': data['collectorActive'], 'duration': data['duration'],
            'scope': 'reported CPU fluid/probe data + native VKF rendering; no client native fluid solver claim'}


def main():
    sources = source_provenance()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    tested = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT), '-p', 'test*.py', '-v'],
                            capture_output=True, text=True, env=env, timeout=180)
    output = tested.stdout+tested.stderr
    if tested.returncode:
        raise RuntimeError(output)
    count = re.search(r'Ran (\d+) tests in ([\d.]+)s', output)
    assert count
    records = [run_case(Smoke.plumes(Config(shape=shape, collector_flux=0), seed=701), 120, 'closed-plumes-'+str(shape))
               for shape in [(16, 12, 8), (24, 16, 8), (32, 24, 12)]]
    records.append(run_case(make_demo(shape=(24, 16, 8), count=0), 360, 'moving-collector', continue_hold=True))
    probes = parcel_snapshot_check()
    visual = existing_visual_provenance()
    assert sources == source_provenance(), 'Reference sources changed during qualification; rerun required'
    result = {'schema': 'physical-smoke-reference-qualification/2', 'generatedUtc': datetime.now(timezone.utc).isoformat(),
              'backend': 'CPU NumPy/SciPy float64; native rendering is separate; native VKF fluid port NOT implemented',
              'platform': platform.platform(), 'python': sys.version, 'numpy': np.__version__, 'scipy': scipy.__version__,
              'sourceProvenance': sources,
              'tests': {'passed': True, 'count': int(count[1]), 'seconds': float(count[2]), 'output': output},
              'domain': '3D periodic MAC, optional balanced porous collector/clear-air supply with C2 moving mask/lift',
              'timeUnits': 'nondimensional reference; SI calibration requires declared reference scales',
              'snapshotPolicy': 'Complete typed manifests include config, masks, lift bases, transition, fixed clock, all fields and probe RNG/hazard. No partial NPZ or checkpoint archive generated.',
              'limitations': ['coarse LES, not DNS/calibrated air', 'finite-rate capture tail retained', 'fine probes dilute/one-way; no finite-inertia two-way qualification', 'glyph SDF/phase-change coupling missing; see SDF_COUPLING.txt', 'metrics are diagnostics, not evidence of turbulence accuracy', 'GPU f32 needs its own residual/convergence/validation'],
              'records': records, 'probeSnapshotReplay': probes, 'existingFluidOnlyVisual': visual}
    (ROOT/'QUALIFICATION.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print('QUALIFIED', json.dumps([{'case': r['case'], 'p95Ms': r['frameMsP95'],
          'divergence': r['maximumDivergenceResidual'], 'stageDivergence': r['maximumStageDivergenceResidual'],
          'massResidual': r['maximumSpeciesMassResidual'], 'capturedFraction': r['capturedFraction']} for r in records]), flush=True)


if __name__ == '__main__':
    main()
