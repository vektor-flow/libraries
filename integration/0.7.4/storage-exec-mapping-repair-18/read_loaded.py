"""Read-only raw policy inspection. No parser/load/mutation."""
from pathlib import Path
import hashlib,json
root=Path('/sys/kernel/security/apparmor/policy/profiles');records=[]
for p in root.iterdir():
 if not p.name.startswith(('bwrap.','unpriv_bwrap.','unprivileged_userns.','vkf-storage-')):continue
 data=(p/'raw_data').read_bytes()
 records.append(dict(path=str(p),name=(p/'name').read_text().strip(),mode=(p/'mode').read_text().strip(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))
print(json.dumps(records))
