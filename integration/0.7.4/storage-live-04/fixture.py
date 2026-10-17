import errno, json, os, pathlib, sys, time

mode, attempt, outside, host_pid_ns, host_net_ns = sys.argv[1:]
root = pathlib.Path(attempt)
start = time.monotonic()
assert os.readlink('/proc/self/ns/pid') != host_pid_ns
assert os.readlink('/proc/self/ns/net') != host_net_ns
assert os.statvfs('/').f_flag & os.ST_RDONLY
assert os.statvfs('/dev/shm').f_flag & os.ST_RDONLY
assert not (os.statvfs(root).f_flag & os.ST_RDONLY)
try:
    fd = os.open(outside, os.O_WRONLY)
except OSError as exc:
    assert exc.errno == errno.EROFS, repr(exc)
    denied = exc.errno
else:
    os.close(fd)
    raise AssertionError('Outside fixture permits write-open')
rows = [x.split() for x in pathlib.Path('/proc/self/mountinfo').read_text().splitlines()]
rw_storage = [r[4].replace('\\040',' ') for r in rows if 'rw' in r[5].split(',')
              and r[r.index('-')+1] not in ('proc','tmpfs','devpts')]
assert rw_storage == [attempt], rw_storage
with (root/'cwd'/'payload.bin').open('xb') as f:
    f.write(b'v2 qualification\n'*128); f.flush(); os.fsync(f.fileno())
report = dict(mode=mode, pid=os.getpid(), pid_ns=os.readlink('/proc/self/ns/pid'),
              net_ns=os.readlink('/proc/self/ns/net'), outside_write_errno=denied,
              writable_storage_mounts=rw_storage, elapsed_seconds=time.monotonic()-start)
print(json.dumps(report), flush=True)
if mode == 'timeout':
    child = os.fork()
    print(json.dumps(dict(namespace_pid=os.getpid(), namespace_child=child)), flush=True)
    time.sleep(30)
elif mode == 'nonzero':
    sys.exit(23)
elif mode != 'success':
    raise AssertionError(mode)
