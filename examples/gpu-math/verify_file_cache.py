"""Root-only cache control and mincore verification; never runs the benchmark."""
import os,sys,json,pathlib,mmap,ctypes
if os.geteuid()!=0:raise RuntimeError('Root is required for reliable mincore on root-owned read-only files')
files=json.loads(pathlib.Path(sys.argv[1]).read_text());libc=ctypes.CDLL(None,use_errno=True);pagesize=os.sysconf('SC_PAGE_SIZE')
def residency(path):
 size=path.stat().st_size
 if not size:return {'pages':0,'resident':0}
 with open(path,'rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_COPY)as mm:
  n=(size+pagesize-1)//pagesize;vec=(ctypes.c_ubyte*n)();address=ctypes.addressof(ctypes.c_char.from_buffer(mm))
  if libc.mincore(ctypes.c_void_p(address),ctypes.c_size_t(size),vec):raise OSError(ctypes.get_errno(),'mincore')
  return {'pages':n,'resident':sum(v&1 for v in vec)}
paths=[pathlib.Path(p)for p in files if pathlib.Path(p).is_file()]
before={str(p):residency(p)for p in paths}
os.sync()
with open('/proc/sys/vm/drop_caches','w')as stream:stream.write('3\n')
after={str(p):residency(p)for p in paths}
print(json.dumps({'effectiveUid':os.geteuid(),'method':'sync; write 3 to /proc/sys/vm/drop_caches; root mincore without reading input contents','before':before,'after':after}))
