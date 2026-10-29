#!/usr/bin/env bash
# Build the Thor's SteamOS kernel from pb-os's SM8550 recipe at a pinned
# commit, cross-compiled on x86_64 (WSL Ubuntu + podman) instead of pb-os's
# aarch64 VM. Same sources, same patches, same config fragments; the only
# change to their build.sh is dropping its "must be aarch64" check.
#
#   BASE=~/thor-kernel KNOWN_GOOD=~/thor-kernel/known-good/KERNEL ./build-thor-kernel.sh
#
# BASE holds pb-os/ (a clone of project-barry/pb-os) and
# rocknix-<ref>/ (git clone --depth 1 --branch <ref> ROCKNIX/distribution).
# KNOWN_GOOD is a copy of the Thor's current /boot/KERNEL: its busybox goes
# into the new initramfs and its cmdline is copied onto the new image, so the
# only things that change are the kernel and the DTBs.
#
# Output: $BASE/out/<release>/ with KERNEL (ready for /boot), KERNEL.md5,
# modules-<release>.tar.gz, config-<release>, dtb diffs, config diff, SHA256SUMS.
set -euo pipefail

PBOS_REF="${PBOS_REF:-d272791933f5099b20800599ff30ccd1aad683aa}"   # pb-os main, alpha-v0.5.4.12
ROCKNIX_REF="${ROCKNIX_REF:-20260901}"                              # build.sh's own pin
LOCALVERSION="${LOCALVERSION:--sm8550-ff1}"
# Same DTBs, same order as the Oct 7 KERNEL the Thor boots today (ABL picks by
# model; keeping the list identical keeps its menu and choice identical).
DTBS="${DTBS:-qcs8550-ayn-thor qcs8550-retroidpocket-rp6 qcs8550-retroidpocket-rp6-top-dpad qcs8550-retroidpocket-rpnova}"
BASE="${BASE:-$HOME/thor-kernel}"
KNOWN_GOOD="${KNOWN_GOOD:-$BASE/known-good/KERNEL}"
IMAGE="${IMAGE:-thor-kernel-build:f43}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '[thor-kernel] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

PB="$BASE/pb-os"
KDIR="$PB/external-and-mods/kernel-sm8650"
ROCKNIX_DIR="$BASE/rocknix-$ROCKNIX_REF"
WORK="$BASE/work$LOCALVERSION"
[[ "$(git -C "$PB" rev-parse HEAD)" == "$PBOS_REF" ]] || die "pb-os is not at $PBOS_REF"
[[ -z "$(git -C "$PB" status --porcelain -- external-and-mods/kernel-sm8650 | grep -v build-cross.sh || true)" ]] \
  || die "pb-os kernel dir has local changes"
[[ -d "$ROCKNIX_DIR/.git" ]] || die "no ROCKNIX checkout at $ROCKNIX_DIR"
[[ -f "$KNOWN_GOOD" ]] || die "no known-good KERNEL at $KNOWN_GOOD"
mkdir -p "$WORK"

# 1. busybox from the known-good initramfs (the binary the Thor boots today).
python3 "$HERE/bootimg-tool.py" unpack "$KNOWN_GOOD" "$WORK/known-good" >/dev/null
rm -rf "$WORK/known-good/rd"; mkdir -p "$WORK/known-good/rd"
podman run --rm -v "$WORK:$WORK" "$IMAGE" bash -c \
  "cd '$WORK/known-good/rd' && zcat ../ramdisk.cpio.gz | cpio -id --quiet && file bin/busybox" \
  | grep -q "ARM aarch64.*statically linked" || die "known-good busybox is not static aarch64"
BUSYBOX="$WORK/known-good/rd/bin/busybox"

# 2. build.sh minus its host-arch check (exactly one line goes), and its
# release suffix read from FF_LOCALVERSION: the kernel Makefile appends an
# exported LOCALVERSION to CONFIG_LOCALVERSION, which doubled the suffix.
sed -e '/^\[\[ "\$(uname -m)" == aarch64 \]\] || die /d' \
    -e 's/^LOCALVERSION="\${LOCALVERSION:-\$_localversion}"$/LOCALVERSION="${FF_LOCALVERSION:-$_localversion}"/' \
    "$KDIR/build.sh" >"$KDIR/build-cross.sh"
[[ $(diff "$KDIR/build.sh" "$KDIR/build-cross.sh" | grep -c '^[<>]') == 3 ]] || die "build.sh edits did not match exactly (arch check + LOCALVERSION line)"
grep -qx 'LOCALVERSION="${FF_LOCALVERSION:-$_localversion}"' "$KDIR/build-cross.sh" || die "LOCALVERSION edit missing"
chmod +x "$KDIR/build-cross.sh"

# 2b. Our own kernel patches ($HERE/patches, e.g. 2001-*), applied after pb-os's
# SM8550 series by name order: copied in for this build only and always removed
# again, so pb-os's tree stays clean (the check above refuses local changes).
FF_PATCHES="${FF_PATCHES:-$HERE/patches}"
ADDED=()
remove_ours() { local p; for p in "${ADDED[@]}"; do rm -f -- "$p"; done; }
trap remove_ours EXIT
if [[ -d "$FF_PATCHES" ]]; then
  for p in "$FF_PATCHES"/*.patch; do
    [[ -e "$p" ]] || continue
    t="$KDIR/sm8550/patches/$(basename "$p")"
    [[ ! -e "$t" ]] || die "our patch name is taken in pb-os's series: $t"
    cp -- "$p" "$t"; ADDED+=("$t")
    log "our patch: $(basename "$p")"
  done
fi
# 2c. Our device-tree patches ($HERE/dts-patches). pb-os applies its sm8550/dts/*.patch after it
# copies ROCKNIX's DTS into the tree (the files do not exist while the code patches above run), in
# name order: ours are named zz-* so they apply on top of pb-os's own DTS patches.
FF_DTS_PATCHES="${FF_DTS_PATCHES:-$HERE/dts-patches}"
if [[ -d "$FF_DTS_PATCHES" ]]; then
  for p in "$FF_DTS_PATCHES"/*.patch; do
    [[ -e "$p" ]] || continue
    [[ $(basename "$p") == zz-* ]] || die "our DTS patch must be named zz-* to sort after pb-os's: $p"
    t="$KDIR/sm8550/dts/$(basename "$p")"
    [[ ! -e "$t" ]] || die "our DTS patch name is taken in pb-os's dts dir: $t"
    cp -- "$p" "$t"; ADDED+=("$t")
    log "our DTS patch: $(basename "$p")"
  done
fi

# 2d. Our config options ($HERE/config/steamos-sm8550.config): pb-os's build.sh merges
# steamos.config plus steamos-<soc>.config when present, and checks every option took. pb-os ships
# no sm8550 one, so ours goes in under that name for this build only (removed again like the patches).
FF_CONFIG="${FF_CONFIG:-$HERE/config/steamos-sm8550.config}"
if [[ -f "$FF_CONFIG" ]]; then
  t="$KDIR/steamos-sm8550.config"
  [[ ! -e "$t" ]] || die "pb-os now ships $t: merge ours into it by hand"
  cp -- "$FF_CONFIG" "$t"; ADDED+=("$t")
  log "our config: $(grep -c '^CONFIG_' "$FF_CONFIG") options from $(basename "$FF_CONFIG")"
fi
# 3. Build. CC is only read by build.sh's GCC-15 check; the kernel Makefile
# takes its compiler from ARCH/CROSS_COMPILE.
log "build $PBOS_REF ($LOCALVERSION) in $IMAGE, log $WORK/build.log"
rc=0
podman run --rm -v "$BASE:$BASE" -v "$BUSYBOX:/bin/busybox:ro" \
  -e SOC=sm8550 -e WORK="$WORK" -e ROCKNIX_DIR="$ROCKNIX_DIR" -e ROCKNIX_REF="$ROCKNIX_REF" \
  -e FF_LOCALVERSION="$LOCALVERSION" -e DTBS="$DTBS" -e KERNEL_BUILD_IN_CONTAINER=1 \
  -e ARCH=arm64 -e CROSS_COMPILE=aarch64-linux-gnu- -e CC=aarch64-linux-gnu-gcc \
  "$IMAGE" bash -c "git config --global --add safe.directory '*'; cd '$KDIR' && ./build-cross.sh" \
  >"$WORK/build.log" 2>&1 || rc=$?
grep -E '^\[kernel-|WARN' "$WORK/build.log" | grep -vE '^\[kernel-sm8550\] (patch|skip) ' >&2 || true
[[ $rc == 0 ]] || { tail -30 "$WORK/build.log" >&2; die "build failed (rc $rc), see $WORK/build.log"; }

KREL="7.2.8$LOCALVERSION"
O="$WORK/output/$KREL"
[[ -s "$O/boot/KERNEL" ]] || die "no $O/boot/KERNEL"
D="$BASE/out/$KREL"; rm -rf "$D"; mkdir -p "$D"

# 4. Today's cmdline onto the new image; check it.
python3 "$HERE/bootimg-tool.py" cmdline "$O/boot/KERNEL" "$D/KERNEL" --from "$KNOWN_GOOD"
python3 "$HERE/bootimg-tool.py" info "$D/KERNEL" | tee "$D/KERNEL.info"
grep -qx ID_OK=yes "$D/KERNEL.info" && grep -qx PARTLABEL_ROOT=yes "$D/KERNEL.info" || die "image check failed"
grep -q '^dtb\[0\] .* AYN Thor$' "$D/KERNEL.info" || die "first DTB is not the AYN Thor"
(cd "$D" && md5sum KERNEL | awk '{print $1"  KERNEL"}' >KERNEL.md5)

# 5. Modules, config, and what changed against today's kernel.
tar -C "$O/modules" -czf "$D/modules-$KREL.tar.gz" "$KREL"
cp "$O/config-$KREL" "$D/"
python3 "$HERE/bootimg-tool.py" unpack "$D/KERNEL" "$WORK/new-unpacked" >/dev/null
podman run --rm -v "$BASE:$BASE" -v "$HERE:$HERE:ro" "$IMAGE" bash -c "
  set -e
  for img in known-good new-unpacked; do
    dtc -q -I dtb -O dts -s '$WORK/'\$img/dtb-00-ayn-thor.dtb >'$WORK/'\$img/thor.dts
  done
  diff -u '$WORK/known-good/thor.dts' '$WORK/new-unpacked/thor.dts' >'$D/thor-dtb.diff' || true
  '$WORK/linux-7.2.8/scripts/diffconfig' '$BASE/known-good/config-7.2.8-sm8550-steamos' '$D/config-$KREL' >'$D/config.diff' || true
"
# The semantic DTB diff needs python3-libfdt, which neither the build image nor WSL
# Ubuntu has (a Windows Python install does): run it where it exists.
if python3 -c 'import libfdt' 2>/dev/null; then
  python3 "$HERE/dtb-diff.py" "$WORK/known-good/dtb-00-ayn-thor.dtb" "$WORK/new-unpacked/dtb-00-ayn-thor.dtb" >"$D/thor-dtb.semantic.diff"
else
  log "no python3-libfdt here: run dtb-diff.py on $WORK/{known-good,new-unpacked}/dtb-00-ayn-thor.dtb elsewhere"
fi
(cd "$D" && sha256sum KERNEL "modules-$KREL.tar.gz" "config-$KREL" >SHA256SUMS)
log "pb-os $PBOS_REF, ROCKNIX $ROCKNIX_REF, $(grep -m1 CONFIG_CC_VERSION_TEXT "$D/config-$KREL")"
log "done: $D"
ls -la "$D" >&2
