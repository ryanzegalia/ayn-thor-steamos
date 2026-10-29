# Gyro files

What runs on my Thor to read the motion sensor and feed it to emulators. How it works and what's proven: [docs/gyro.md](../../docs/gyro.md). On 29 October 2026, `thor-motiond` (the on-only-when-wanted version), `thor-sensors` and both service files were byte-for-byte the copies on my Thor, apart from one comment.

| File | What | License |
|---|---|---|
| `thor-motiond`, `thor-motiond.service` | The motion daemon: sensor hub to DSU (emulators) and to a uinput motion device (InputPlumber). Runs as a system service, and only reads the sensor while a DSU client or the Switch Pro identity wants it. State in `/run/thor-motiond.mode`. | MIT |
| `tests/test-thor-motiond.py` | Tests for when the streams start and stop, and the rate-aware zero and drift (`python3 tests/test-thor-motiond.py -v`, no sensor needed). | MIT |
| `thor-motion-config` | Points Azahar, Eden and Dolphin at the DSU feed. Run once, with the emulators closed. | MIT |
| `thor-sensors`, `thor-sensors.service` | Builds the sensor registry and runs the two `hexagonrpcd` listeners early in boot. A port of pb-os's `sm8550-sensors`, which comes from MaSi's SteamOS-ARM-SM8550. | GPL-2.0 (pb-os's license) |
| `build-hexagonrpcd.sh` | Builds `hexagonrpcd` and `sscregistrygen` on the Thor from linux-msm/hexagonrpc `dd9ac70` plus the patches below. | MIT |
| `hexagonrpc-patches/` | pb-os's eight patches to hexagonrpc, unchanged from pb-os commit `d272791` (checked against pb-os's SHA256SUMS). | GPL-3.0 (hexagonrpc's license), by pb-os |
| `install.sh` | Installs the runtime to `/usr/lib/thor-sensors`, `/usr/share/thor-sensors` and `/etc/systemd/system`. | MIT |
| `thor-imu-probe.py`, `qrtr-lookup.py`, `dsu-probe.py`, `deck-imu-peek.py` | Checks: read the sensor hub directly, list QRTR services (400 = sensors), read the DSU feed, look for motion inside the Steam pad's reports. | MIT |

**Not included: AYN's stock sensor configuration and DSP library.** `install.sh` expects them in a folder named `upstream-pbos-d272791/share/` (pb-os carries them at that commit). They're AYN's proprietary files, so get them from pb-os or your own Thor's firmware, never from a re-upload.

Order I did it in: build the kernel ([kernel.md](../../docs/kernel.md)), then `build-hexagonrpcd.sh`, then `install.sh`, then reboot so the sensor helpers attach early, then check with `qrtr-lookup.py 400` and `thor-imu-probe.py`, then `thor-motion-config`.
