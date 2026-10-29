# The Thor's kernel: what I run and what I changed

My Thor runs a kernel I build myself from pb-os's own kernel recipe, plus eight small patches and one config option. This page says what that is, why I did it, where every patch came from, and what I actually checked on the device.

The rule I held myself to: if I didn't see it work on the Thor, the page says so or leaves it out. Every "measured" below is something I measured on my own Thor. Where a result has a caveat, the caveat is in the same cell.

The files are in [reference/kernel/](../reference/kernel/). The kernel image itself is not in this repo. You build it.

## What it is

- **The recipe is pb-os's.** pb-os keeps its SM8550 kernel build in `external-and-mods/kernel-sm8650/` ([project-barry/pb-os](https://github.com/project-barry/pb-os)). I build that recipe at commit `d272791` (the `alpha-v0.5.4.12` tag), with ROCKNIX's `20260901` tag as the source it pulls from. The kernel is Linux 7.2.8. I use my own release suffix, `-sm8550-ffN`, so I can tell my builds apart. The current one is `7.2.8-sm8550-ff6`.
- **I build it myself instead of using pb-os's prebuilt kernel or flashing their update.** I take pb-os changes one at a time. I build on an x86_64 PC in a Fedora 43 container with an aarch64 cross compiler. The only change to pb-os's `build.sh` is that the build script deletes its "must be running on aarch64" check, and the suffix line. The build script checks that exactly those edits are all that changed.
- **The tree underneath is not mine either.** pb-os's kernel builds on [MaSi's SteamOS-ARM-SM8550](https://github.com/MaSieS4Fun/SteamOS-ARM-SM8550) and on [ROCKNIX](https://github.com/ROCKNIX/distribution). Both are credited at the bottom.

## Why I built it

The kernel my pb-os image first came with was pb-os's prebuilt one from 2026-10-07 (`7.2.8-sm8550-steamos`). I wanted three things that only a newer recipe gave me.

| I wanted | What I saw | Evidence |
|---|---|---|
| **Rumble** that works on the Thor's linear resonant actuator (LRA) | On the first kernel boot of my build (`ff1`, 2026-10-19), my read-only health snapshot differed from the old kernel's in the haptics line (`use_erm no`, `vmax 1300`). I played three rumble pulses and they felt great to me. | Measured: `thor-kernel-check` diff between the two kernels. The feel is my own judgment, one session. |
| A **charge stop** (hold the battery, ideally near 80%) | The old kernel had no charge-control files; `charge_control_end_threshold` accepted a write and read back 0. The recipe at `d272791` carries pb-os's patch 0545, which adds `retroid_charge_now` and `retroid_limit_capacity`. On my build, `retroid_charge_now 0` took the battery to 0 A while USB powered the Thor and `1` charged it again in about 2 seconds. `retroid_limit_capacity 1` stopped charging too. | Measured on the charger at 100%, 2026-10-19. |
| The **kernel half of gyro** (FastRPC for the sensor hub) | On the old kernel `dmesg` said `no reserved DMA memory for FASTRPC` and the sensor hub never came up. On my build the health snapshot shows the FastRPC sensors process enabled, and with the userspace pieces in [gyro.md](gyro.md) the sensor hub streams and the gyro works in the 3DS emulator. | Measured. Steam Input doesn't use the gyro yet, see [gyro.md](gyro.md). |

Two caveats on that table. The stop at exactly 80% over a full day was not proven (see "Not proven"). And I did not compare against a pb-os kernel newer than 2026-10-07 apart from building it, so I can't say what pb-os's current prebuilt does.

## How the Thor boots it

- The bootloader (ABL) loads **one file**, `/boot/KERNEL`. It lives on the vfat partition with the GPT name `ROCKNIX`.
- That file is an Android boot image (v0). It holds the compressed kernel, the device-tree blobs appended to it, and a small busybox initramfs that mounts the real root (`root=PARTLABEL=STORAGE`). The bootloader picks the device tree by model.
- Kernel modules live on the root filesystem in `/usr/lib/modules/<release>`. **The image and its modules must come from the same build.** A mismatch is a known way to get a black screen. I follow the rule and never tried a mismatch on purpose.
- Firmware is on the root filesystem and is not part of a kernel swap.
- My build keeps the old image's four device trees in the same order, copies the old image's command line over byte for byte, and reuses the old image's busybox. So the only things that change are the kernel and the device trees. The Thor's device tree came out byte-identical between ff5 and ff6.

Swapping is replacing that one file, after adding the new modules directory next to the old one. Nothing existing is overwritten.

## The patches

Everything here applies to the Linux kernel, so all of it is GPL-2.0, the kernel's license. The five Armada patches are copied unchanged from Armada OS (I compared them byte for byte with the upstream files at the commit named below); the three numbered 2001 to 2003 and the device-tree patch are mine.

Armada OS: [armada-os/armada](https://github.com/armada-os/armada), commit `1ed5b2b39e1395bd4ab9f335a428faafd8298c80`, folder `packages/kernel/patches/`. Its license file says Armada's own software is GPL-2.0-or-later and bundled works keep their own licenses.

| # | What it changes | Where it came from | License | Proof on my Thor |
|---|---|---|---|---|
| [2001](../reference/kernel/patches/2001-power-supply-qcom_battmgr-held-battery-not-charging.patch) | When a charge switch holds the battery on the charger, the battery firmware reports "discharging" at 0 A. This reports "Not charging" instead (only while a switch holds it and USB is online). | Mine. Builds on pb-os's patch 0545. | GPL-2.0 | Before: Steam read the Thor as unplugged and its 15-minute battery idle timer put it to sleep on the charger (two suspends with no power key, 2026-10-20). After: the battery shows "Not charging", and Steam's plugged-in idle sleep then fired 1,804 s after the only input, as its charger setting says. I did not capture Steam's power-source value after the patch by itself. |
| [2002](../reference/kernel/patches/2002-arm64-dts-qcom-sm8550-gpu-passive-trip-factory-95c.patch) | Moves the GPU's passive thermal trip from 85 C to 95 C, which is what the Thor's own Android device tree uses. Hot (90 C) and critical (110 C) trips are unchanged. | Mine, from AYN's Android device tree values. | GPL-2.0 | Measured before: at 85 C the GPU flapped between 615 and 680 MHz under load with the fan at full. Measured after, 10-minute GPU test: peak 95.5 C at full fan, 680 MHz for 38.5% of the last 5 minutes, 28.4 fps against 20.3 before. Caveat: I changed fan and CPU settings in the same round, so the fps gain is not this patch alone. The GPU now sits on the 95 C trip. |
| [2003](../reference/kernel/patches/2003-pci-qcom-root-port-wake-irq.patch) | Arms the PCIe Root Port's WAKE# line as a system wake interrupt, so the Wi-Fi chip's wake-on-WLAN can wake the SoC. | Mine. Version 1 leaked the wake interrupt when the probe retried; this is version 2. | GPL-2.0 | Before: only the RTC alarm woke the Thor. After, on the charger with the magic packet armed: deep sleep woke about 1 s after the packet, 5 of 5 (two more rounds skipped because the charger's plug-in woke it first). On battery I switch wake-on-WLAN off from userspace; that part is not the kernel. |
| [zz-ff-2004](../reference/kernel/dts-patches/zz-ff-2004-thor-lid-wakes-on-both-edges.patch) | Device tree: the lid sensor wakes the Thor on both edges, not just on open. | Mine. Reverts, for the Thor only, a pb-os change (`788b192`, which came from Armada) that made it wake only on open. ROCKNIX's Thor device tree uses the both-edges form. | GPL-2.0 | Before: a Thor put to sleep with the lid open could not be woken by the lid at all. After, one run on battery (about 20 minutes): power-key sleep with the lid open, deep sleep, lid closed (it went back to sleep), lid opened (it woke); and lid closed for 8 minutes, then opened (it woke). I did not repeat it enough times to give a rate. |
| [2004](../reference/kernel/patches/2004-armada-0078-drm-msm-dpu-fix-vblank-timestamps-on-command-mode-panels.patch) | Reads the right counter for vblank timestamps on command-mode panels, so page-flip timestamps match the panel. | Armada OS patch 0078, by Armada. | GPL-2.0 | Measured, same gamescope build, same game, only the kernel changed: a 60 fps cap on the 120 Hz panel gave 68.5 and 70.1 flips/s on ff5 and 59.7 and 59.7 on ff6, with 97 to 98% of frames held exactly two refreshes. |
| [2005](../reference/kernel/patches/2005-armada-0619-drm-msm-map-submitqueue-priority-onto-high-low.patch) | Fixes the GPU submit-queue priority mapping, so a game's queue no longer outranks the compositor's. | Armada OS patch 0619, by virtudude (author line in the file). | GPL-2.0 | Running since 2026-10-25. I did not measure its effect separately. |
| [2006](../reference/kernel/patches/2006-armada-0620-drm-msm-a6xx-hfi-irq-clears-only-the-cm3-fault.patch) | The Adreno GMU's HFI interrupt handler clears only the one bit it handles, so a poll for a reply doesn't lose the answer. | Armada OS patch 0620, by gennro. | GPL-2.0 | Running since 2026-10-25. The failure it fixes never happened to me, so I can't say it fixed anything on my Thor. See the sleep test below. |
| [2007](../reference/kernel/patches/2007-armada-0621-drm-msm-a6xx-bound-the-gmu-wait-for-a-fault-devcoredump.patch) | Puts a 2 second limit on a wait that could deadlock the GPU recovery. | Armada OS patch 0621, by gennro. | GPL-2.0 | Same as 2006. |
| [2008](../reference/kernel/patches/2008-armada-0622-drm-msm-a6xx-mask-the-hfi-interrupt-before-booting-the-gmu.patch) | Masks the HFI interrupt before the GMU boots. | Armada OS patch 0622, by Armada. | GPL-2.0 | Same as 2006. |

For 2006 to 2008 together: after installing ff6 I did 3 rtcwake deep-sleep cycles at idle and then 10 more with a game running. Every cycle woke, the game stayed up, and `dmesg` showed no `gmu`, `hfi`, `a6xx` or `adreno` errors. That shows the patches didn't break anything. It doesn't show they fixed a hang, because I never saw the hang.

**Config:** [`CONFIG_USERFAULTFD=y`](../reference/kernel/config/steamos-sm8550.config) (plus three options it selects). The pb-os, ROCKNIX and Armada configs all leave it off. Proton's write watches can use it instead of one signal per page. Measured with a small test program on ff6: a first write to a watched page cost about 2.2 us, and about 0.5 to 0.7 us with my userspace shim using the kernel's tracking. With the shim on in a real game (Dead Cells) every Wine process held a userfaultfd, and a 10-minute soak stayed up with the top panel at 116 to 119 flips/s. I tried one game; I have not tested the rest.

## Safety notes

- **Image and modules from the same build, always.** `thor-kernel-install` adds the new modules directory first and leaves the running kernel's modules where they are.
- **Never change firmware in a kernel swap.** The Thor's ADSP firmware also runs audio, the battery manager and USB-C, so I left all firmware alone.
- **Save the known-good kernel before swapping.** `thor-kernel-install` copies the current `/boot/KERNEL` to `KERNEL.known-good` (with an md5 file). It only swaps on a charger with the battery over 50% and no game running, and it never reboots by itself. Mine are also kept off the Thor.
- **Rollback from SteamOS:** `thor-kernel-rollback --reboot` puts `KERNEL.known-good` back and checks the md5.
- **Rollback from Android, if SteamOS won't boot:** power off, Vol Up + Power opens the bootloader menu, pick Android, then run `thor-kernel-rollback-android.sh`. Then switch the boot target back.
- **What I rehearsed:** the Android rollback, on 2026-10-19 before the first swap. `--check` and `--force` ran: it rewrote the same bytes and I read them back correctly, and a read-only filesystem check of the boot partition was clean. I did **not** rehearse a kernel that fails to boot, so the "SteamOS won't start, go through the bootloader menu" path is unproven. I also have no log showing the SteamOS-side rollback script restoring a kernel; treat that script as unrehearsed.
- **Everything I swapped booted.** Every build I installed came up (ff6 after 3 warm reboots and 3 sleep cycles, and its health snapshot matched ff5's apart from the release name), so I haven't needed either rollback in anger.
- **Do not trust my cmdline.** Mine mounts `root=PARTLABEL=STORAGE`. Copy yours from your own `/boot/KERNEL`, as `bootimg-tool.py` does.

## Not proven, not done

- **Holding the battery at exactly 80% for a whole day on the charger.** The stop mechanism works (charging stops and restarts on command, and I saw 0 A at 99% after a reboot), but I haven't run the full-day test.
- **Holding 80% while the Thor is powered off.** It fails. I shut down at 88% on the charger and it booted at 99% with no boot in between. The bootloader or power chip charges a switched-off Thor to full. Only a running OS (awake, or Steam's Sleep on the charger) holds the limit.
- **2005 to 2008 individually.** Running, not separately measured; the GPU hang fixes were never triggered.
- **Gyro through Steam Input.** The kernel half works, and the gyro reaches the 3DS emulator. Steam Input doesn't use it yet, see [gyro.md](gyro.md).
- **Lid wake as a rate.** One run, not a repeated count.
- **A cold boot of ff6.** I used warm reboots and sleep cycles.
- **Whether pb-os's newer prebuilt kernel does any of this better.** I haven't run it.
- **The Android side.** I don't touch Android's kernel. Only SteamOS's boot file changes.

## Credits

- [pb-os](https://github.com/project-barry/pb-os) by Project Barry: the kernel recipe, the config I build on, and patch 0545 (the charge-control files). The part I use is under its own licenses; the repo's license file says components keep theirs.
- [MaSi's SteamOS-ARM-SM8550](https://github.com/MaSieS4Fun/SteamOS-ARM-SM8550): the SM8550 kernel tree behind pb-os's kernel, including the FastRPC sensors patch.
- [ROCKNIX](https://github.com/ROCKNIX/distribution): the source pb-os's build pulls from (tag `20260901`) and the Thor device tree's lid wake setting I matched.
- [Armada OS](https://github.com/armada-os/armada): patches 2004 to 2008, copied unchanged with their original authors (Armada, virtudude, gennro).
- [SteamOS-ARM-Port](https://github.com/hashtagbasit/SteamOS-ARM-Port) by hashtagbasit: pb-os's ancestor, for the gyro research.
- The Linux kernel developers, whose code all of this is.

I couldn't confirm a single license file for each of these repos through GitHub's license detector, which reports "other" for all of them. pb-os's LICENSE says each component keeps its own license, and Armada's LICENSE.md says its own software is GPL-2.0-or-later. Check the repos yourself before you reuse their files. Every project and what I took from it is also in [CREDITS.md](../CREDITS.md).
