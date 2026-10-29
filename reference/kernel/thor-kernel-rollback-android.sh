#!/system/bin/sh
# Android side: put the known-good SteamOS kernel back when SteamOS will not
# boot (reach Android by hand: hold Power off; Vol Up + Power from off -> ABL
# menu -> Android -> Start). Installed as /data/adb/thor-kernel-rollback.sh.
#
#   su -c sh /data/adb/thor-kernel-rollback.sh --check    read-only mount, md5s
#   su -c sh /data/adb/thor-kernel-rollback.sh            KERNEL.known-good -> KERNEL
#   su -c sh /data/adb/thor-kernel-rollback.sh --force    same, even if already equal
#                                                         (rehearses the write path)
#
# Finds the ABL boot partition by its GPT name (ROCKNIX, vfat, sda18 on this
# Thor), never by number. Touches only KERNEL and KERNEL.md5 on it. Then
# switch back with /data/adb/thor-bootmode.sh set linux --reboot (or the
# power menu's SteamOS button). SteamOS twin: thor-kernel-rollback.
MNT=/data/local/tmp/thor-rocknix

die() { echo "thor-kernel-rollback: $*" >&2; [ -n "$mounted" ] && umount "$MNT" 2>/dev/null; exit 1; }
md5of() { md5sum "$1" | cut -d' ' -f1; }
mounted=""

[ "$(id -u)" = 0 ] || die "run as root: su -c sh $0 $*"
case "${1:-}" in --check|--force|"") ;; *) die "usage: $0 [--check|--force]" ;; esac

dev=""
for u in /sys/class/block/*/uevent; do
  if grep -qx "PARTNAME=ROCKNIX" "$u"; then d="${u%/uevent}"; dev="/dev/block/${d##*/}"; break; fi
done
[ -n "$dev" ] || die "no partition named ROCKNIX"
[ -b "$dev" ] || die "$dev is not a block device"
if grep -q "^$dev " /proc/mounts; then die "$dev is already mounted"; fi

mkdir -p "$MNT"
if [ "${1:-}" = --check ]; then opts=ro; else opts=rw; fi
mount -t vfat -o "$opts" "$dev" "$MNT" || die "mount $dev failed"
mounted=1
echo "ROCKNIX = $dev mounted $opts at $MNT"

[ -f "$MNT/KERNEL.known-good" ] && [ -f "$MNT/KERNEL.known-good.md5" ] || die "no KERNEL.known-good (+.md5)"
good=$(cut -d' ' -f1 "$MNT/KERNEL.known-good.md5")
[ "$(md5of "$MNT/KERNEL.known-good")" = "$good" ] || die "KERNEL.known-good does not match its md5: not touching anything"
cur=$(md5of "$MNT/KERNEL")
echo "KERNEL            $cur  ($(stat -c %s "$MNT/KERNEL") B)"
echo "KERNEL.known-good $good  ($(stat -c %s "$MNT/KERNEL.known-good") B, md5 ok)"

if [ "${1:-}" = --check ]; then
  [ "$cur" = "$good" ] && echo "STATE=known-good" || echo "STATE=other"
elif [ "$cur" = "$good" ] && [ "${1:-}" != --force ]; then
  echo "KERNEL is already the known-good one"
else
  cp "$MNT/KERNEL.known-good" "$MNT/KERNEL.rollback-tmp" || die "copy failed"
  sync
  [ "$(md5of "$MNT/KERNEL.rollback-tmp")" = "$good" ] || { rm -f "$MNT/KERNEL.rollback-tmp"; die "copy did not verify"; }
  mv -f "$MNT/KERNEL.rollback-tmp" "$MNT/KERNEL" || die "rename failed"
  echo "$good  KERNEL" >"$MNT/KERNEL.md5"
  sync
  echo "restored KERNEL = known-good ($good)"
fi
umount "$MNT" || die "umount failed"
mounted=""
if [ "${1:-}" != --check ]; then
  # Read back from a fresh read-only mount, not the page cache.
  mount -t vfat -o ro "$dev" "$MNT" || die "re-mount failed"
  mounted=1
  [ "$(md5of "$MNT/KERNEL")" = "$good" ] || die "KERNEL does not read back as $good"
  umount "$MNT"; mounted=""
  echo "read back OK. Next: /data/adb/thor-bootmode.sh set linux --reboot"
fi
exit 0
