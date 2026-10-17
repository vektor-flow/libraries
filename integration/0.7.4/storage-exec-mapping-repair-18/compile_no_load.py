from pathlib import Path
import hashlib,json,resource,subprocess,time
H=Path(__file__).resolve().parent
resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
records=[]
for name,src in [('v1',Path('/etc/apparmor.d/vkf-storage-private-v1')),('v2',H/'system-setup/vkf-storage-private-v2'),('bwrap',Path('/etc/apparmor.d/bwrap-userns-restrict')),('userns',Path('/etc/apparmor.d/unprivileged_userns'))]:
 argv=['/usr/sbin/apparmor_parser','--config-file=/dev/null','--stdout','--skip-kernel-load','--skip-cache','--jobs=1','--max-jobs=1','--zstd-compress-level=0','--base=/etc/apparmor.d',str(src)]
 start=time.monotonic();p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:stdout,stderr=p.communicate(timeout=25)
 except subprocess.TimeoutExpired:p.kill();stdout,stderr=p.communicate();raise
 (H/'evidence'/f'{name}.compiled').write_bytes(stdout);(H/'evidence'/f'{name}.parser.stderr').write_bytes(stderr)
 records.append(dict(argv=argv,pid=p.pid,returncode=p.returncode,seconds=time.monotonic()-start,bytes=len(stdout),sha256=hashlib.sha256(stdout).hexdigest(),child_absent=not Path(f'/proc/{p.pid}').exists(),stderr=stderr.decode()))
 assert p.returncode==0 and stdout
(H/'compile-results.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
