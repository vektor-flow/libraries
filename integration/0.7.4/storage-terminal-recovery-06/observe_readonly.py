"""Real bounded read-only custody sample under the EXISTING capacity.lock."""
import fcntl
import json
import os
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'candidate/storage-direct-v4'))
import terminal_recovery as r
from storage_paths import directory, require
lock=Path(r.ANCHORS['state']['path']).parent.parent/'capacity.lock'
start=time.monotonic()
with directory(lock.parent) as parent:
    fd=os.open(lock.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX)
        require(os.fstat(fd).st_ino==os.stat(lock.name,dir_fd=parent,follow_symlinks=False).st_ino,'lock replaced')
        base,phase=r.historical();proof=r.observe(phase);r.validate_proof(phase,proof)
        require(r.exact(base,r.historical()[0]),'changed historical source')
    finally:os.close(fd)
print(json.dumps(dict(observation=proof,seconds=time.monotonic()-start,ram_released=False,
    operational_mutation=False,passed=False,state_pin=r.ANCHORS['state']),indent=2))
