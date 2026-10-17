"""Exact root-operated live14 recovery. No arbitrary phase, proof, reset or launch."""
import argparse
import json
from pathlib import Path
import time
import terminal_recovery as recovery
from storage_admission import Ledger
from storage_paths import require


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('observe','recover','inspect','rotate-f'))
    p.add_argument('--authority', type=Path, required=True)
    p.add_argument('--authority-sha256', required=True)
    p.add_argument('--transition', type=Path)
    p.add_argument('--transition-sha256')
    a = p.parse_args()
    pin = dict(path=str(a.authority), sha256=a.authority_sha256)
    recovery.live14_authority(pin, recovery.LIVE14_STATE, recovery.LIVE14_LOCK)
    ledger = Ledger(recovery.LIVE14_STATE, recovery.LIVE14_LOCK, recovery_pin=pin)
    if a.command == 'recover':
        result = recovery.recover_live14(ledger)
    elif a.command == 'rotate-f':
        require(a.transition is not None and a.transition_sha256, 'reviewed transition pin required')
        transition = dict(path=str(a.transition), sha256=a.transition_sha256)
        t = recovery.protected_pin(transition)
        require(t['worker'] == 'F' and t['kind'] == 'live14-recovered-terminal-failure', 'exact F transition only')
        ledger.rotate_owner(transition, verify_join=lambda *_: False)
        result = dict(result='F-owner-chain-appended', transition=transition, owner_publication=False)
    else:
        with ledger.transaction() as data:
            if a.command == 'observe':
                baseline, r, _, _ = recovery.live14_sources()
                require(recovery.exact(data, baseline), 'exact prerecovery snapshot required')
                recovery.live14_current_owner()
                start = time.monotonic()
                proof = recovery.observe_live14(r); recovery.validate_live14_proof(r, proof)
                require(time.monotonic()-start <= 5.0, 'stale read-only proof')
                result = dict(result='diagnostic-only', ram_released=False, passed=False, observation=proof)
            else:
                result = dict(state=data, released=sorted(ledger.released(data)),
                    active_ram_intent=sum(r['ram_bytes'] for r in ledger.active_rows(data)))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
