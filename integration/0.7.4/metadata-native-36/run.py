import pathlib,subprocess,sys,json,time
OUT=pathlib.Path(__file__).resolve().parent
name,script,*args=sys.argv[1:];cmd=['/usr/bin/python3','-I','-B',str(OUT/script),*args]
start=time.monotonic()
with (OUT/(name+'.stdout')).open('xb') as out,(OUT/(name+'.stderr')).open('xb') as err:r=subprocess.run(cmd,stdout=out,stderr=err)
result=dict(argv=cmd,exit=r.returncode,seconds=time.monotonic()-start,subprocess_joined=True)
with (OUT/(name+'-runner.json')).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result));print((OUT/(name+'.stdout')).read_text()[-3000:]);print((OUT/(name+'.stderr')).read_text()[-5000:]);raise SystemExit(r.returncode)
