"""Single invocation, actual child identity/output/join receipt; no retry."""
import json,os,sys,time,subprocess
from pathlib import Path
from preflight import OUT,save,proc
name=sys.argv[1];args=sys.argv[2:];script=OUT/name
assert script.parent==OUT and script.is_file()
command=['/usr/bin/python3','-B',str(script),*args]
start=time.monotonic();child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
identity=proc(child.pid)
stdout,stderr=child.communicate(timeout=115)
observed=proc(child.pid)
assert observed is None or observed['starttime']!=identity['starttime']
record=dict(command=command,identity=identity,exit=child.returncode,stdout=stdout,stderr=stderr,seconds=time.monotonic()-start,joined=True,observed=observed)
save(name+'-'+('-'.join(args) or 'run')+'-execution.json',record)
print(stdout,end='');print(stderr,end='',file=sys.stderr)
raise SystemExit(child.returncode)
