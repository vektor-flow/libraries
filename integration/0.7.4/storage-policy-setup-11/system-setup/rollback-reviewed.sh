#!/bin/bash
# REVIEW ONLY. Not executed by storage-policy-setup-11.
# Root must independently prove quiescence and accept the exact candidate first.
set -euo pipefail
PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ $(id -u) == 0 ]] || { echo 'Root system setup review required' >&2; exit 1; }
task_dir=/usr/local/libexec/vkf-storage-private-v1
task_binary="$task_dir/unshare"
task_policy=/etc/apparmor.d/vkf-storage-private-v1
task_policy_sha=a6a82dd0c9f50c296e88933645e8a8487b947dd4de6ff6e66acee2541e1a17a4
task_binary_sha=41c65e55107cbbb1a1f6994784a938dd7dbbe255d1fea6b7a58ec96eabe382ef
check_hash() { [[ $(sha256sum -- "$1" | cut -d ' ' -f 1) == "$2" ]]; }

# Full rollback for an installed candidate; partial/ambiguous install needs review.
# No chmod/removal occurs until identity and exact bytes are checked.
/usr/bin/python3.14 -I -B - <<'CHECK'
import stat
from pathlib import Path
for name in ['/usr/local/libexec/vkf-storage-private-v1',
             '/usr/local/libexec/vkf-storage-private-v1/unshare',
             '/etc/apparmor.d/vkf-storage-private-v1']:
 p=Path(name)
 for ancestor in (p,*p.parents):
  s=ancestor.lstat()
  assert not stat.S_ISLNK(s.st_mode) and s.st_uid==0 and not s.st_mode & 0o022,str(ancestor)
assert {p.name for p in Path('/usr/local/libexec/vkf-storage-private-v1').iterdir()}=={'unshare'}
CHECK
check_hash "$task_binary" "$task_binary_sha"
check_hash "$task_policy" "$task_policy_sha"
chmod 0600 "$task_binary"
rm -- "$task_binary"
/usr/sbin/apparmor_parser --remove --skip-cache --jobs=1 --max-jobs=1 --base=/etc/apparmor.d "$task_policy"
task_loaded=$(cat /sys/kernel/security/apparmor/profiles)
if /usr/bin/rg -q '^vkf-storage-(private|pre)-v1 ' <<< "$task_loaded"; then
  echo 'Profile removal incomplete; stop' >&2; exit 1
fi
rm -- "$task_policy"
rmdir -- "$task_dir"
echo 'Only dedicated setup removed; holds, ledger and budget untouched'
