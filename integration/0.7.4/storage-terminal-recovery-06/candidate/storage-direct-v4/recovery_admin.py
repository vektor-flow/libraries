#!/usr/bin/env python3
"""Coordinator-only CLI. Inspect/observe never release. Recover is exact and single-use."""
import argparse
import fcntl
import json
import os
from pathlib import Path
from storage_admission import Ledger
from storage_paths import directory, pinned_json, require
import terminal_recovery as recovery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['observe', 'recover', 'inspect', 'rotate', 'transition-plan'])
    parser.add_argument('--authority-sha256', required=True)
    parser.add_argument('--transition')
    parser.add_argument('--transition-sha256')
    parser.add_argument('--worker', choices=['A','F'])
    parser.add_argument('--to-owner')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    expected = Path(recovery.ANCHORS['state']['path']).parent.parent/'storage-direct-v4'
    require(here == expected, 'install only into reviewed versioned successor path')
    ledger = Ledger(here/'direct-state-v4.json', here.parent/'capacity.lock',
        recovery_pin=dict(path=str(here/'recovery-authority.json'), sha256=args.authority_sha256))
    recovery.authority(ledger.recovery_pin, ledger.state, ledger.lock)
    if args.command == 'observe':
        # Existing lock only; no filesystem creation, state change or live execution.
        with directory(ledger.lock.parent) as parent:
            fd = os.open(ledger.lock.name, os.O_RDONLY|os.O_NOFOLLOW, dir_fd=parent)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                require(os.fstat(fd).st_ino == os.stat(ledger.lock.name, dir_fd=parent,
                        follow_symlinks=False).st_ino, 'lock replaced')
                baseline, r = recovery.historical()
                proof = recovery.observe(r)
                recovery.validate_proof(r, proof)
                require(recovery.exact(baseline, recovery.historical()[0]), 'changed historical state')
                result = dict(observation=proof, ram_released=False, passed=False)
            finally:
                os.close(fd)
    elif args.command == 'recover':
        result = recovery.recover(ledger)
    elif args.command == 'inspect':
        data = ledger.snapshot()
        result = dict(recovery=data['recovery_events'], owners={k:ledger.owner(data,k) for k in data['lanes']},
            active_ram=sum(r['ram_bytes'] for r in ledger.active_rows(data)),
            charged={k:rec['policy']['historical_charge']+sum(r['phase_bytes'] for r in data['phases'].values()
                if r['worker']==k) for k,rec in data['lanes'].items()})
    elif args.command == 'transition-plan':
        require(args.worker and args.to_owner, 'fresh worker owner required')
        data = ledger.snapshot(); rec = data['lanes'][args.worker]
        require(not rec['transitions'] and args.to_owner != rec['policy']['owner'], 'initial successor owner only')
        result = dict(version='direct-directory-v2', worker=args.worker, coordinator=rec['policy']['coordinator'],
            policy=rec['pin'], previous=None, from_owner=rec['policy']['owner'], to_owner=args.to_owner,
            phase_sequence=len(data['phases']))
        if args.worker == 'F':
            require(set(data['phases']) == {recovery.KEY}, 'prepare F transition before fresh phases')
            result.update(kind='recovered-terminal-failure', prior_phase=recovery.KEY,
                recovery_event=data['recovery_events'][0]['sha256'])
        else:
            require(not any(r['worker']=='A' for r in data['phases'].values()), 'A already used')
            result.update(kind='enrolled-unused', enrollment=recovery.ANCHORS['state'])
    else:
        require(args.transition and args.transition_sha256, 'pinned transition required')
        pin = dict(path=args.transition, sha256=args.transition_sha256)
        t = pinned_json(pin)
        require(t['kind'] in ('enrolled-unused','recovered-terminal-failure'), 'exact owner transitions only')
        ledger.rotate_owner(pin, verify_join=lambda *args:False)
        result = dict(owner_transition=pin, worker=t['worker'], owner=t['to_owner'])
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
