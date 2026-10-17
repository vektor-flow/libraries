from pathlib import Path
import difflib
h=Path(__file__).resolve().parent;r=h.parents[2];patch=[]
for p in sorted((h/'candidate').rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(h/'candidate').as_posix();old=r/rel
 patch.append(f'diff --git a/{rel} b/{rel}\n')
 if not old.exists():patch.append('new file mode 100644\n')
 patch.extend(difflib.unified_diff(old.read_text().splitlines(True) if old.exists() else [],p.read_text().splitlines(True),fromfile='a/'+rel if old.exists() else '/dev/null',tofile='b/'+rel))
(h/'selection-implementation.patch').write_text(''.join(patch))
