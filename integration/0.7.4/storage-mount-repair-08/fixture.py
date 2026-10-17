"""Fresh grant only. This file was NOT executed in a live sandbox by repair08."""
import json
import os
from pathlib import Path
import stat
import sys
import time
from effective_storage import need, observe, observe_fd, open_path, qualify


def main():
    mode, attempt, outside, host_pid_ns, host_net_ns = sys.argv[1:]
    need(mode in ('success', 'nonzero', 'timeout'), 'unknown mode')
    start = time.monotonic()
    need(os.readlink('/proc/self/ns/pid') != host_pid_ns, 'PID namespace')
    need(os.readlink('/proc/self/ns/net') != host_net_ns, 'network namespace')
    need(observe('/').readonly and observe('/dev/shm').readonly, 'root/shm readonly')
    # No outside write-open: effective mount flags establish EROFS without a
    # write-permission probe. live07's actual EROFS result remains historical.
    need(observe(outside).readonly, 'outside source not readonly')
    # Preserve exact namespace evidence even if a fail-closed check rejects it.
    print(json.dumps(dict(stage='mount-snapshot',
        mountinfo=Path('/proc/self/mountinfo').read_text(errors='surrogateescape'))), flush=True)
    proof = qualify(attempt)
    cwd = observe(attempt+'/cwd')
    need(cwd.mount_id == proof['attempt_mount_id'] and not cwd.readonly
         and stat.S_ISDIR(cwd.mode), 'cwd outside charged mount')
    d = open_path(attempt+'/cwd')
    try:
        need(observe_fd(d) == cwd, 'cwd replaced')
        fd = os.open('payload.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=d)
        with os.fdopen(fd, 'wb') as f:
            f.write(b'fresh storage qualification\n'*128)
            f.flush(); os.fsync(f.fileno())
        syncfd = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, dir_fd=d)
        try:
            os.fsync(syncfd)
        finally:
            os.close(syncfd)
    finally:
        os.close(d)
    after = qualify(attempt)
    need(after == proof, 'topology changed during payload')
    print(json.dumps(dict(mode=mode, pid=os.getpid(), pid_ns=os.readlink('/proc/self/ns/pid'),
        net_ns=os.readlink('/proc/self/ns/net'), outside_readonly=True,
        effective_storage=proof, elapsed_seconds=time.monotonic()-start)), flush=True)
    if mode != 'timeout':
        time.sleep(0.35)
    if mode == 'timeout':
        child = os.fork()
        print(json.dumps(dict(namespace_pid=os.getpid(), namespace_child=child)), flush=True)
        time.sleep(30)
    elif mode == 'nonzero':
        sys.exit(23)

if __name__ == '__main__':
    main()
