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
task_source='/home/viktor/Projects/Vektor Flow/.worktrees/gpu-math-20261014-libraries/integration/0.7.4/storage-policy-setup-11/system-setup/vkf-storage-private-v1'

[[ ! -e "$task_dir" && ! -L "$task_dir" && ! -e "$task_policy" && ! -L "$task_policy" ]]
task_loaded=$(cat /sys/kernel/security/apparmor/profiles)
if /usr/bin/rg -q '^vkf-storage-(private|pre)-v1 ' <<< "$task_loaded"; then
  echo 'Existing setup profile: stop, do not replace' >&2; exit 1
fi
check_hash /usr/bin/unshare "$task_binary_sha"
check_hash "$task_source" "$task_policy_sha"
# Do not follow or adjust existing shared parent paths.
/usr/bin/python3.14 -I -B - <<'CHECK'
import os,stat
from pathlib import Path
for name in ['/usr','/usr/local','/usr/local/libexec','/etc','/etc/apparmor.d','/usr/bin/unshare']:
 p=Path(name)
 if name=='/usr/local/libexec' and not p.exists():continue
 s=p.lstat()
 assert not stat.S_ISLNK(s.st_mode) and s.st_uid==0 and not s.st_mode & 0o022,name
s=Path('/usr/bin/unshare').stat()
assert stat.S_ISREG(s.st_mode) and not s.st_mode & 0o6000
assert 'security.capability' not in os.listxattr('/usr/bin/unshare')
CHECK
if [[ ! -d /usr/local/libexec ]]; then install -d -o root -g root -m 0755 /usr/local/libexec; fi
install -d -o root -g root -m 0755 "$task_dir"
install -o root -g root -m 0600 /usr/bin/unshare "$task_binary"
check_hash "$task_binary" "$task_binary_sha"
install -o root -g root -m 0644 "$task_source" "$task_policy"
check_hash "$task_policy" "$task_policy_sha"
/usr/sbin/apparmor_parser --add --skip-cache --jobs=1 --max-jobs=1 --base=/etc/apparmor.d "$task_policy"
/usr/bin/rg -q '^vkf-storage-private-v1 \(enforce\)$' /sys/kernel/security/apparmor/profiles
/usr/bin/rg -q '^vkf-storage-pre-v1 \(enforce\)$' /sys/kernel/security/apparmor/profiles
# Last mutation exposes only the reviewed binary after its policy is loaded.
chmod 0755 "$task_binary"
echo 'Dedicated setup installed; no workload authorized or launched'
