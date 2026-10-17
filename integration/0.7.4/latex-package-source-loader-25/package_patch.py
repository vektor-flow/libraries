from pathlib import Path
import difflib
H=Path(__file__).resolve().parent
parts=[]
for p in sorted((H/'candidate').rglob('*')):
 if p.is_file():
  rel=p.relative_to(H/'candidate').as_posix()
  parts.append(f'diff --git a/{rel} b/{rel}\nnew file mode 100644\n')
  parts.extend(difflib.unified_diff([],p.read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+rel))
(H/'package-source-foundation.patch').write_text(''.join(parts))
