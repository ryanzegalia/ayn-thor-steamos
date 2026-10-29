# Gyro on SteamOS: what I got working

This page is only partly done, and it says so. The sensor reads fine on my Thor. Getting motion into games isn't proven yet, so the parts that would do that aren't in this repo.

## Where the sensor is

The Thor's accelerometer and gyroscope (an SH5001) aren't on a bus Linux can see. They sit behind the Snapdragon's ADSP, in Qualcomm's sensor hub (SSC). There's no IIO driver for them. To read them from Linux you need:

1. **A kernel with the FastRPC sensors process enabled.** The SM8550 kernel tree behind pb-os ([MaSi's SteamOS-ARM-SM8550](https://github.com/MaSieS4Fun/SteamOS-ARM-SM8550)) has a FastRPC sensors patch and Thor device-tree pieces for this, and pb-os's kernel sources carry them. On the kernel my image first came with, `dmesg` said `no reserved DMA memory for FASTRPC` and the sensor hub never came up. My kernel is pb-os's recipe built myself, with them ([kernel.md](kernel.md)).
2. **The Thor's stock ADSP firmware.** It's already on the device. I didn't change any firmware.
3. **`hexagonrpcd`** from [linux-msm/hexagonrpc](https://github.com/linux-msm/hexagonrpc), with pb-os's eight patches, serving the sensors process. I built it on the Thor itself.
4. **A sensor registry** generated from AYN's stock sensor config (`sscregistrygen`, the way pb-os's `sm8550-sensors` does it). The config comes from the device's own firmware and must not be redistributed.
5. **A client** that talks to the sensor hub (QMI service 400 over QRTR) and asks for accelerometer and gyro samples.

## What I proved

- With those pieces, the sensor hub publishes QMI service 400. [qrtr-lookup.py](../reference/gyro/qrtr-lookup.py) lists it.
- [thor-imu-probe.py](../reference/gyro/thor-imu-probe.py), my own client, asks for 200 Hz and gets accelerometer and gyro samples at about 218 Hz. Lying flat, the accelerometer reads `(0.80, -1.97, 10.52)` m/s², about 1 g, and the gyro reads about zero. The probe is plain Python with hand-encoded protobuf messages: the same messages pb-os's `pbos-motiond` sends, written from scratch.
- **Start order matters.** The helpers have to attach early in boot, after the sound card appears. Attaching about 10 minutes after boot never brought service 400 up until a reboot. After a reboot with the helpers attached 23 seconds in, it appeared within 20 seconds.
- **My motion daemon streams all the time, even when nothing uses it.** It asks for accel and gyro at 200 Hz from boot. Measured on my Thor: about 0.1 W at idle (2.59 W on, 2.49 W off, 2.62 W on again, 90 s each), and about 16% of one little core next to a light game. That's small but not zero. Streaming only while a game that uses motion is running is still on my to-do list.

## What Steam does with it

I fed the motion into InputPlumber as a motion-sensor source of the Thor's composite device. That needs two more commits on my InputPlumber fork, which aren't in this repo. What I saw:

- On the default handheld identity (`28de:12f0`), Steam's Test Device Inputs shows **no gyro**, even though the pad's reports carry motion.
- On the Switch Pro identity, the pad's reports carry the motion. The accelerometer reads about +1.07 g lying flat, once I fixed a unit conversion that had it pinned at +8 g. I haven't confirmed motion on Steam's test screen or in a game.

The Switch Pro identity has on/off triggers ([switch-pro-identity.md](switch-pro-identity.md)), so making it the default just for gyro wasn't acceptable to me.

## Not proven, not here

- Gyro in a game through Steam Input.
- Motion for emulators over DSU (cemuhook). My daemon serves it, but I haven't checked the axis signs or seen it work in an emulator.
- My motion daemon and the two InputPlumber motion commits. They go in once the above works.

If you're working on Thor gyro yourself, look at pb-os. It has been adding its own Thor gyro support.
