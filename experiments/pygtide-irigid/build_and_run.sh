#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 EMPTY_WORK_DIRECTORY" >&2
  exit 2
fi

work=$1
if [[ -e "$work" ]]; then
  echo "refusing existing path: $work" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/../.." && pwd)
git clone --branch v0.9.7 --single-branch \
  https://github.com/hydrogeoscience/pygtide.git "$work"
git -C "$work" checkout --detach e2587918bbeba27bd3464da1002396393856cd03
test "$(git -C "$work" rev-parse HEAD)" = e2587918bbeba27bd3464da1002396393856cd03
(cd "$work" && sha256sum -c \
  "$repo_root/experiments/pygtide-irigid/UPSTREAM_SHA256SUMS")
git -C "$work" apply "$repo_root/experiments/pygtide-irigid/pygtide_irigid_v0_9_7.patch"
meson setup "$work/build" "$work"
meson compile -C "$work/build"
extension=$(find "$work/build" -maxdepth 1 -type f -name 'etpred*.so' -print -quit)
test -n "$extension"
cp "$extension" "$work/pygtide/etpred.so"

PYTHONPATH="$work" python \
  "$repo_root/experiments/pygtide-irigid/investigate_pygtide_irigid.py"
