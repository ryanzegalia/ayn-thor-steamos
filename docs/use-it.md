# Using these files on your own Thor

Everything here is shared to help. Take the pieces you want. This page says what I actually did with each one on my Thor, so you (or your AI) can repeat it or adapt it. Where I haven't tested something, I say so.

Before you start: this is all on pb-os's SteamOS with Decky Loader, on my Thor. Back up anything you replace. Know how to get back to a working system, too: for the Thor, that means booting Android from the boot menu.

## Just the art

The drawings and icons in [art/](../art/) are plain SVG, CC BY 4.0. Use them in your own plugin, theme, website or project. Credit "Ryan Zegalia" and link back here. Every control in the drawings has a stable id, so you can light it up from code ([art/README.md](../art/README.md)).

## ThorLook: the Thor drawn in Steam

What I did:

1. `python3 reference/thorlook/build.py`. It writes `reference/thorlook/decky/dist/index.js` with the art embedded, and needs no Node build.
2. Copy the plugin folder (`dist/index.js`, `main.py`, `plugin.json`, `package.json`) to `~/homebrew/plugins/ThorLook/` on the Thor, owned by root (that's how I installed it). On a first install, Decky picks it up as soon as the folder appears. I staged it beside the folder and renamed it in, so Decky never saw a half-copied folder.
3. Updating an installed copy needs a Decky restart, which reloads Steam's UI. Do it with no game running.

Check: open Steam's controller settings, or Test Device Inputs. Steam's JS console logs `[ThorLook] patched N rule(s)`, and a `<style id="thorlook-style">` appears in the Game Mode window.

Tested only with my patched InputPlumber running, on both identities. I haven't run it against a stock InputPlumber.

## FatterPad: per-game layouts and Nintendo mode

What I did: [reference/fatterpad/install.sh](../reference/fatterpad/install.sh), run as the `steamos` user. No root is needed. It installs `fatterpad-abxy` and `prompts-db` to `~/.local/bin`, their systemd user units, and the `environment.d` file that sets `PROTON_ENABLE_HIDRAW`, then enables them. The daemon uses Python's `dbus` and `yaml` modules and `xprop`, which were already on my pb-os image. The Quick Access panel is a Decky plugin folder like ThorLook (`reference/fatterpad/decky/`). Its `dist/index.js` is already built.

Nintendo mode needs the Switch Pro identity, so it needs the InputPlumber patches below. On an InputPlumber without the `switch-pro` target, FatterPad reports the identity as unsupported and leaves the pad as the handheld. I've only run FatterPad with the patches installed.

## The Switch Pro identity: InputPlumber patches

What I did on the Thor:

1. Got InputPlumber's source at v0.81.0. I applied pb-os's two haptics patches (from pb-os's InputPlumber build), then my five from [reference/inputplumber/patches/](../reference/inputplumber/patches/) with `git am`.
2. Built it on the Thor itself with `cargo build --release` (Rust 1.93.1).
3. Installed it with [thor-ip-fork](../reference/tools/thor-ip-fork): `thor-ip-fork on <path to target/release/inputplumber>`. It copies the binary to `/var/lib/thor-inputplumber/` and points the `inputplumber` service at it with a systemd drop-in. The stock `/usr/bin/inputplumber` is never touched, and `thor-ip-fork off` goes back to it. It won't restart InputPlumber while a game is running.
4. Switched the identity with `fatterpad-abxy identity switch-pro`, or straight over D-Bus ([switch-pro-identity.md](switch-pro-identity.md)).
5. Checked it with [thor-pro-probe](../reference/tools/thor-pro-probe) (expect `bound=nintendo` and a few hundred reports a second) and [thor-steam-pads](../reference/tools/thor-steam-pads) (expect `type=38 ... nintendo=True`).

## Gyro for emulators

What I did, in order: built my kernel ([kernel.md](kernel.md)), built `hexagonrpcd` on the Thor, installed the sensor helpers and the motion daemon, rebooted so the helpers attach early, checked the sensor hub, then pointed the emulators at the DSU feed. The files and steps are in [reference/gyro/README.md](../reference/gyro/README.md). AYN's own sensor files aren't in this repo. It works in Azahar (3DS) on my Thor, and I haven't confirmed Eden or Dolphin yet.

## The kernel

See [kernel.md](kernel.md). It covers what each patch does, where it came from, how I built and swapped the kernel, and how to roll back.

## Giving this to your AI

Point it at [AGENTS.md](../AGENTS.md) first, and tell it what you're running: your Thor model, your pb-os version, your InputPlumber version (`inputplumber --version`) and whether you use Decky. The docs say which versions I tested on. Ask it to check its plan against those before it changes anything on your device.
