# Thor kernel: build and swap files

These are the files I used to build and install my Thor's kernel on SteamOS. The story, the proof and the limits are in [docs/kernel.md](../../docs/kernel.md). Read that first.

Nothing here runs by itself. The scripts are written for my own Thor and my own build machine, and the build script has a few paths and names you will need to set.

| File | What it is |
|---|---|
| `patches/2001..2003` | My three kernel patches (battery status, GPU thermal trip, PCIe wake). |
| `patches/2004..2008` | Five patches from Armada OS, copied byte for byte (only the first line, my note about where they came from, is mine). Each keeps its original author line. |
| `dts-patches/zz-ff-2004-thor-lid-wakes-on-both-edges.patch` | My device-tree patch so the lid wakes the Thor on both edges. |
| `config/steamos-sm8550.config` | One kernel option on top of pb-os's config: `CONFIG_USERFAULTFD=y`. |
| `build-thor-kernel.sh` | Builds the kernel by running pb-os's own `build.sh` at a pinned commit, cross-compiled on x86_64 inside the container. Needs a pb-os clone, a ROCKNIX clone and a copy of the Thor's current `/boot/KERNEL` (see the header). |
| `Containerfile` | The Fedora 43 build image with the aarch64 cross compiler. |
| `bootimg-tool.py` | Reads, unpacks and repacks the Android boot image the Thor's bootloader loads, and copies the kernel command line from the old image to the new one. |
| `dtb-diff.py` | Compares two device-tree blobs ignoring phandle numbering. Needs python3-libfdt. |
| `thor-kernel-check` | Read-only health snapshot of the SteamOS side, one `key=value` per line, so you can diff two kernels. Set `PING_HOST` to a host on your network first (the original pinged a server of mine). |
| `thor-kernel-install` | On the Thor: checks a built kernel, adds its modules, saves a known-good copy, swaps the one boot file. Never reboots. |
| `thor-kernel-rollback` | On the Thor: puts the saved known-good kernel back. |
| `thor-kernel-rollback-android.sh` | The same rollback, run from Android, for when SteamOS will not boot. It mentions `/data/adb/thor-bootmode.sh`, my own helper that switches the boot target. It is not in this repo. |

Scrubbing: I removed my network addresses, host names, local paths and internal notes from the comments. Behavior is unchanged except that the ping target in `thor-kernel-check` is now the `PING_HOST` variable.

The patches are patches to the Linux kernel and are GPL-2.0, like the kernel. The scripts are mine; see the repo's LICENSE file.
