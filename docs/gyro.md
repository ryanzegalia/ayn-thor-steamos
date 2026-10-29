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

It's a Python daemon that runs from boot. It reads accel and gyro at 200 Hz in the controller's frame (x right, y up the screen, z out of the screen). It learns the gyro's zero while the Thor lies still, and turns sensors off around suspend. Then it sends the motion two ways:

- **To emulators over DSU** (the cemuhook protocol) on `127.0.0.1:26760`. [thor-motion-config](../reference/gyro/thor-motion-config) points Azahar (3DS), Eden (Switch) and Dolphin (Wii and GameCube) at it. It skips an emulator that's running and keeps backups.
- **To InputPlumber** as a uinput motion device, `Thor Motion Sensors`, which my InputPlumber build adds to the Thor's controller.

## What works

- **The 3DS emulator (Azahar) on SteamOS.** The gyro moves the view in Ocarina of Time 3D. I first noticed it because the view crept on its own when the Thor was in my hands. The zero only learns while the Thor lies still, and a warm sensor and hand tremor both reach the aim. So on 2026-10-24 I added in-hand drift tracking to the DSU feed: it cancels steady drift under 1°/s with an 8-second time constant, capped at 1.5°/s, and softly damps rates under 1°/s, so a still hand gives a still view and a real turn passes through. Environment variables `THOR_GYRO_DRIFT` and `THOR_GYRO_TIGHTEN` tune it, and `0` turns either off. The feed Steam gets keeps the plain zeroed values.
- **The sensor itself.** With the pieces above, the sensor hub publishes QMI service 400 ([qrtr-lookup.py](../reference/gyro/qrtr-lookup.py) lists it). [thor-imu-probe.py](../reference/gyro/thor-imu-probe.py) asks for 200 Hz and gets accel and gyro at about 218 Hz. Lying flat, the accelerometer reads `(0.80, -1.97, 10.52)` m/s², about 1 g, and the gyro reads about zero. The probe is plain Python with hand-encoded protobuf messages: the same messages pb-os's `pbos-motiond` sends, written from scratch. [dsu-probe.py](../reference/gyro/dsu-probe.py) checks the DSU feed.
- **Start order matters.** The helpers have to attach early in boot, after the sound card appears. Attaching about 10 minutes after boot never brought service 400 up until a reboot. After a reboot with the helpers attached 23 seconds in, it appeared within 20 seconds. `thor-sensors.service` handles this.

## What isn't done

- **Gyro through Steam Input.** On the default handheld identity, Steam's Test Device Inputs shows no gyro, even though the pad's reports carry motion ([deck-imu-peek.py](../reference/gyro/deck-imu-peek.py) shows it). On the Switch Pro identity, the pad's reports carry the motion too (the accelerometer reads about +1.07 g lying flat, after I fixed a unit conversion that had it pinned at +8 g), but I haven't confirmed it on Steam's test screen or in a game. That needs two more commits on my InputPlumber build, which aren't in this repo yet. The Switch Pro identity also has on/off triggers ([switch-pro-identity.md](switch-pro-identity.md)), so I won't make it the default just for gyro.
- **Eden and Dolphin.** `thor-motion-config` points them at the same feed, but I've only confirmed the gyro in Azahar.
- **The drift tracking applies to every DSU emulator,** but I've only tried it in Ocarina of Time 3D.

## The CPU it costs (not fixed yet)

`thor-motiond` streams at 200 Hz all the time, from boot, whether anything uses the motion or not. That isn't a kernel issue: it's my Python daemon decoding every sample. Measured on my Thor:

- About 3.5% of one core on average: 2,971 CPU-seconds since its last start about 23.6 hours earlier, read 2026-10-29.
- About 16% of one little core next to a light game.
- About 0.1 W at idle (2.59 W on, 2.49 W off, 2.62 W on again, 90 s each).

The plan, not built yet: stream at a low rate when nothing is listening, and at full rate only while an emulator is connected over DSU or a Switch Pro game is running. Or move the hot loop out of Python. Until then, `systemctl stop thor-motiond` is the off switch. Restarting it is safe: InputPlumber re-adds the motion device.

## Using it

See [reference/gyro/README.md](../reference/gyro/README.md) for what each file is and the order I installed them in. If you're working on Thor gyro yourself, look at pb-os too. It has been adding its own Thor gyro support.
