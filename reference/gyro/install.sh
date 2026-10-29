#!/bin/bash
# Install the Thor gyro stack on SteamOS from a staged copy of this folder
# plus the hexagonrpcd build (build-hexagonrpcd.sh output).
#
#   install.sh STAGE BIN_DIR           install + enable + start
#   install.sh --remove                stop, disable, take it out (keeps the
#                                      registry in /var/lib/thor-sensors)
#
# Everything lands at new paths (nothing of pb-os or SteamOS is replaced):
#   /usr/lib/thor-sensors/   hexagonrpcd sscregistrygen thor-sensors thor-motiond thor-imu-probe.py
#   /usr/share/thor-sensors/ AYN's stock sensor config (upstream-pbos-d272791/share)
#   /etc/systemd/system/     thor-sensors.service thor-motiond.service
# Needs: kernel with FastRPC sensors-PD (7.2.8-sm8550-ff1), and our
# InputPlumber fork with the evdev IMU source to reach Steam.
set -euo pipefail
[[ $EUID == 0 ]] || exec sudo "$0" "$@"
LIB=/usr/lib/thor-sensors SHARE=/usr/share/thor-sensors U=/etc/systemd/system
UNITS=(thor-motiond.service thor-sensors.service)

if [[ "${1:-}" == --remove ]]; then
  systemctl disable --now "${UNITS[@]}" 2>/dev/null || true
  rm -f "$U/thor-sensors.service" "$U/thor-motiond.service"
  rm -rf "$LIB" "$SHARE"
  systemctl daemon-reload
  echo "removed (registry kept in /var/lib/thor-sensors)"
  exit 0
fi

S="${1:?stage dir (this folder)}"; B="${2:?hexagonrpcd build dir}"
for f in "$B/hexagonrpcd" "$B/sscregistrygen" "$S/thor-sensors" "$S/thor-motiond" "$S/thor-imu-probe.py" \
         "$S/thor-sensors.service" "$S/thor-motiond.service" "$S/upstream-pbos-d272791/share/kailua/sensors/sns_reg.conf"; do
  [[ -s "$f" ]] || { echo "missing $f" >&2; exit 1; }
done
(cd "$S/upstream-pbos-d272791" && sha256sum -c --quiet SHA256SUMS) || { echo "vendored inputs do not match SHA256SUMS" >&2; exit 1; }

install -d "$LIB" "$SHARE"
install -m0755 "$B/hexagonrpcd" "$B/sscregistrygen" "$S/thor-sensors" "$S/thor-motiond" "$LIB/"
install -m0644 "$S/thor-imu-probe.py" "$LIB/"
rm -rf "$SHARE/kailua" "$SHARE/thor"
cp -r "$S/upstream-pbos-d272791/share/kailua" "$S/upstream-pbos-d272791/share/thor" "$SHARE/"
chmod -R a+rX "$SHARE"
install -m0644 "$S/thor-sensors.service" "$S/thor-motiond.service" "$U/"
systemctl daemon-reload
systemctl enable thor-sensors.service thor-motiond.service
echo "installed; start now with: systemctl start thor-sensors.service (best right after boot)"
(cd "$LIB" && sha256sum hexagonrpcd sscregistrygen thor-sensors thor-motiond thor-imu-probe.py)
