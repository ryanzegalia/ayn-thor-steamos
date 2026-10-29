# Gyro on SteamOS

The Thor's gyro works for the 3DS emulator on my SteamOS. Steam Input doesn't use it yet. This page covers how the motion gets from the chip to an emulator, what I proved, and what's still open.

## Where the sensor is

The Thor's accelerometer and gyroscope (an SH5001) aren't on a bus Linux can see. They sit behind the Snapdragon's ADSP, in Qualcomm's sensor hub (SSC). There's no IIO driver for them. To read them from Linux you need:

1. **A kernel with the FastRPC sensors process enabled.** The SM8550 kernel tree behind pb-os ([MaSi's SteamOS-ARM-SM8550](https://github.com/MaSieS4Fun/SteamOS-ARM-SM8550)) has a FastRPC sensors patch and Thor device-tree pieces for this, and pb-os's kernel sources carry them. On the kernel my image first came with, `dmesg` said `no reserved DMA memory for FASTRPC` and the sensor hub never came up. My kernel is pb-os's recipe, built myself, with them ([kernel.md](kernel.md)).
2. **The Thor's stock ADSP firmware.** It's already on the device. I didn't change any firmware.
3. **`hexagonrpcd`** from [linux-msm/hexagonrpc](https://github.com/linux-msm/hexagonrpc) (commit `dd9ac70`), with pb-os's eight patches, serving the sensors process. I built it on the Thor itself ([build-hexagonrpcd.sh](../reference/gyro/build-hexagonrpcd.sh), patches in [reference/gyro/hexagonrpc-patches/](../reference/gyro/hexagonrpc-patches/)).
4. **A sensor registry** generated from AYN's stock sensor config. My [thor-sensors](../reference/gyro/thor-sensors) does this. It's a port of pb-os's `sm8550-sensors`. AYN's config files come from the device's own firmware and aren't in this repo.
5. **A client** that talks to the sensor hub (QMI service 400 over QRTR) and asks for accelerometer and gyro samples. Mine is [thor-motiond](../reference/gyro/thor-motiond).

## What thor-motiond does

It's a Python daemon that runs from boot, but it **only reads the sensor while something can use the motion**: an emulator connected to its DSU feed, or the Switch Pro identity (the one identity Steam reads gyro from on my Thor). It reads accel and gyro at 200 Hz in the controller's frame (x right, y up the screen, z out of the screen). It learns the gyro's zero while the Thor lies still, saves it, and turns the sensors off around suspend. Then it sends the motion two ways:

- **To emulators over DSU** (the cemuhook protocol) on `127.0.0.1:26760`. [thor-motion-config](../reference/gyro/thor-motion-config) points Azahar (3DS), Eden (Switch) and Dolphin (Wii and GameCube) at it. It skips an emulator that's running and keeps backups.
- **To InputPlumber** as a uinput motion device, `Thor Motion Sensors`, which my InputPlumber build adds to the Thor's controller.

## What works

- **The 3DS emulator (Azahar) on SteamOS.** The gyro moves the view in Ocarina of Time 3D, and on 2026-10-29, with the on-only-when-wanted daemon below, it aimed "very smoothly" in my hands. I first noticed it because the view crept on its own when the Thor was in my hands. The zero only learns while the Thor lies still, and a warm sensor and hand tremor both reach the aim. So on 2026-10-24 I added in-hand drift tracking to the DSU feed: it cancels steady drift under 1°/s with an 8-second time constant, capped at 1.5°/s, and softly damps rates under 1°/s, so a still hand gives a still view and a real turn passes through. Environment variables `THOR_GYRO_DRIFT` and `THOR_GYRO_TIGHTEN` tune it, and `0` turns either off. The feed Steam gets keeps the plain zeroed values.
- **The sensor itself.** With the pieces above, the sensor hub publishes QMI service 400 ([qrtr-lookup.py](../reference/gyro/qrtr-lookup.py) lists it). [thor-imu-probe.py](../reference/gyro/thor-imu-probe.py) asks for 200 Hz and gets accel and gyro at about 218 Hz. Lying flat, the accelerometer reads `(0.80, -1.97, 10.52)` m/s², about 1 g, and the gyro reads about zero. The probe is plain Python with hand-encoded protobuf messages: the same messages pb-os's `pbos-motiond` sends, written from scratch. [dsu-probe.py](../reference/gyro/dsu-probe.py) checks the DSU feed.
- **Start order matters.** The helpers have to attach early in boot, after the sound card appears. Attaching about 10 minutes after boot never brought service 400 up until a reboot. After a reboot with the helpers attached 23 seconds in, it appeared within 20 seconds. `thor-sensors.service` handles this.

## What isn't done

- **Gyro through Steam Input.** On the default handheld identity, Steam's Test Device Inputs shows no gyro, even though the pad's reports carry motion ([deck-imu-peek.py](../reference/gyro/deck-imu-peek.py) shows it). On the Switch Pro identity, the pad's reports carry the motion too (the accelerometer reads about +1.07 g lying flat, after I fixed a unit conversion that had it pinned at +8 g), but I haven't confirmed it on Steam's test screen or in a game. That needs two more commits on my InputPlumber build, which aren't in this repo yet. The Switch Pro identity also has on/off triggers ([switch-pro-identity.md](switch-pro-identity.md)), so I won't make it the default just for gyro.
- **Eden and Dolphin.** `thor-motion-config` points them at the same feed, but I've only confirmed the gyro in Azahar.
- **The drift tracking applies to every DSU emulator,** but I've only tried it in Ocarina of Time 3D.

## On only when something uses it

My first version streamed at 200 Hz all the time, from boot, whether anything used the motion or not. That cost about 3.7% of one core in the menus (the Thor has 8), about 16% of one little core next to a light game, and about 0.1 W at idle (2.59 W on, 2.49 W off, 2.62 W on again, 90 s each). It's my Python daemon decoding every sample, not a kernel issue.

Since 2026-10-29 it streams only when something can use the motion:

- **An emulator connects to the DSU feed:** the streams start at once. A DSU client got 214 packets a second over its first 4 seconds.
- **The Switch Pro identity appears** (its HID device `057e:2009` exists): the streams start within 2 seconds. That's what FatterPad switches to for Nintendo-mode games, and it's the only identity Steam reads gyro from here. This trigger is covered by tests, but I haven't watched it happen live yet.
- **Nothing wants it for 5 seconds:** the streams stop. The `hexagonrpcd` helpers and the uinput device stay up, and the saved zero carries over to the next start.
- The current state is in `/run/thor-motiond.mode` (`0 off -`, `200 active dsu` or `200 active switch-pro`), and each change is logged.

Measured over 60 seconds in the menus with no game: 3.7% of a core always-on, **0.04% now**. One thing I learned on the way: **the sensor hub won't go below about 110 Hz.** Asking it for 5, 10, 25, 50 or 100 Hz all delivered about 110 a second (200 delivers about 218). So a "slow" stream only halves the cost, and stopping it is what actually saves it. `THOR_MOTION_IDLE_HZ` picks the idle behaviour: `0` (the default) is off, `1` to `199` is the slow stream (only that many reports a second are passed on to InputPlumber), and `200` is the old always-on. The zero learning and drift tracking use the rate the hub actually delivers. Tests: [reference/gyro/tests/test-thor-motiond.py](../reference/gyro/tests/test-thor-motiond.py).

Restarting the daemon is safe: InputPlumber re-adds the motion device.

## Using it

See [reference/gyro/README.md](../reference/gyro/README.md) for what each file is and the order I installed them in. If you're working on Thor gyro yourself, look at pb-os too. It has been adding its own Thor gyro support.
