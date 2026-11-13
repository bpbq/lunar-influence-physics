#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="$(mktemp -d /tmp/lipe-moonshiner.XXXXXX)"
cleanup() {
  case "$work_dir" in
    /tmp/lipe-moonshiner.*) rm -rf -- "$work_dir" ;;
    *) printf 'Refusing to remove unexpected path: %s\n' "$work_dir" >&2 ;;
  esac
}
trap cleanup EXIT

git clone --quiet https://github.com/cran/REdaS.git "$work_dir/REdaS"
git -C "$work_dir/REdaS" checkout --quiet be50ce2c5e210817192dcb5859ec4da34a097abb
git clone --quiet https://github.com/cran/suncalc.git "$work_dir/suncalc"
git -C "$work_dir/suncalc" checkout --quiet 9c1cde30060c86c5e62a366609e1bd01c92894b8
git clone --quiet https://github.com/cran/MoonShineR.git "$work_dir/MoonShineR"
git -C "$work_dir/MoonShineR" checkout --quiet 9307aadfa003315d455bbe491f55bcd6fa06e968

image="rocker/tidyverse@sha256:4813816ad695004b738ccfff8513ce43f017e6fe78fb273aafd0bee4d4e1070a"
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS \
  -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock run --rm \
  --mount "type=bind,src=$work_dir/REdaS,dst=/src/REdaS,readonly" \
  --mount "type=bind,src=$work_dir/suncalc,dst=/src/suncalc,readonly" \
  --mount "type=bind,src=$work_dir/MoonShineR,dst=/src/MoonShineR,readonly" \
  --mount "type=bind,src=$repo_root/scripts,dst=/src/scripts,readonly" \
  --mount "type=bind,src=$repo_root/tests/validation/data,dst=/output" \
  "$image" bash -lc \
  'R CMD INSTALL /src/REdaS /src/suncalc /src/MoonShineR >/tmp/install.log && Rscript /src/scripts/generate_moonshiner_fixture.R /output/moonshiner_1_2_0.csv'
