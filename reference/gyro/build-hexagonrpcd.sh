#!/bin/bash
# Build hexagonrpcd + sscregistrygen for the Thor's gyro, natively on the
# Thor (it has gcc, meson, ninja, json-c). Source: linux-msm/hexagonrpc at
# commit dd9ac70 (https://github.com/linux-msm/hexagonrpc, passed in as a
# `git archive` tar made with Linux git: Windows git's autocrlf turns the
# sources into CRLF and the patches fail), plus pb-os's eight patches
# (upstream-pbos-d272791/hexagonrpc-patches: sensor registry reverse
# interface, static PD, writable hexagonfs, large callbacks, ...). Same
# recipe as pb-os external-and-mods/pbos-motion/build.sh, minus their daemon.
#
#   [HEXAGONRPCD_VERBOSE=true] build-hexagonrpcd.sh hexagonrpc-dd9ac70.tar PATCH_DIR OUT_DIR
set -euo pipefail
HEXAGONRPC_REF=dd9ac70c026e1bad93e8cffa3801255b8ceb551e
TAR="${1:?hexagonrpc tar}"; PATCHES="${2:?patch dir}"; OUT="${3:?output dir}"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
tar -C "$work" -xf "$TAR"
[[ -f "$work/hexagonrpc/meson.build" ]] || { echo "not a hexagonrpc tree" >&2; exit 1; }
if file "$work/hexagonrpc/meson.build" | grep -q CRLF; then
  echo "CRLF in the source tar: make it with Linux git archive" >&2; exit 1
fi
for p in "$PATCHES"/*.patch; do
  patch -d "$work/hexagonrpc" -p1 -s --no-backup-if-mismatch <"$p" || { echo "patch failed: $p" >&2; exit 1; }
done
# libhexagonrpc static, so hexagonrpcd carries it (pb-os does the same).
sed -i "s/^libhexagonrpc = shared_library(/libhexagonrpc = library(/" "$work/hexagonrpc/libhexagonrpc/meson.build"
grep -q "^libhexagonrpc = library(" "$work/hexagonrpc/libhexagonrpc/meson.build" || { echo "cannot make libhexagonrpc static" >&2; exit 1; }
(cd "$work" && meson setup --buildtype=release --default-library=static -Dhexagonrpcd_verbose="${HEXAGONRPCD_VERBOSE:-false}" hexagonrpc out >/dev/null \
  && ninja -C out hexagonrpcd/hexagonrpcd tools/sscregistrygen >/dev/null \
  && strip out/hexagonrpcd/hexagonrpcd out/tools/sscregistrygen)
install -D -m0755 "$work/out/hexagonrpcd/hexagonrpcd" "$OUT/hexagonrpcd"
install -D -m0755 "$work/out/tools/sscregistrygen" "$OUT/sscregistrygen"
echo "hexagonrpc $HEXAGONRPC_REF + $(ls "$PATCHES"/*.patch | wc -l) patches, verbose=${HEXAGONRPCD_VERBOSE:-false}" >"$OUT/BUILD-INFO"
(cd "$OUT" && sha256sum hexagonrpcd sscregistrygen | tee -a BUILD-INFO)
