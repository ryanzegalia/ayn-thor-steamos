# Credits

Everything this runs on was made by other people. This page lists each project, its license, whether this repo includes anything from it, and what I took or changed.

"Included" means files from that project, or patches to it, are in this repo. "Used" means it runs on my Thor and nothing of it is here. "Reference" means I read it to learn how something works, and wrote my own code.

## The platform

| Project | By | License | In this repo | What I took or changed |
|---|---|---|---|---|
| [pb-os](https://github.com/project-barry/pb-os) | Project Barry (lavachemist and contributors) | GPL-2.0 for its own software (its LICENSE file). Vendored trees keep their own licenses. | Used | The SteamOS image my Thor runs, including its InputPlumber config for the Thor (`50-ayn_thor.yaml` and the `ayn_mcu` capability map), which sends the face buttons by their printed letters. I take pb-os fixes one at a time and don't run its updater. |
| [SteamOS-ARM-Port](https://github.com/hashtagbasit/SteamOS-ARM-Port) | hashtagbasit | GPL-2.0 for its own software (its LICENSE file) | Reference | pb-os's ancestor. Its gyro research for SM8550 handhelds told me which pieces the Thor's motion sensor needs. |
| [SteamOS-ARM-SM8550](https://github.com/MaSieS4Fun/SteamOS-ARM-SM8550) | MaSi | GPL-2.0 for its own software (its LICENSE file). Kernel code is GPL-2.0. | Reference | The SM8550 kernel tree behind pb-os's kernel. Its FastRPC sensors patch (carried in pb-os's kernel) is what lets the sensor hub run. |
| pb-os's kernel recipe (`external-and-mods/kernel-sm8650/`, commit `d272791`) and its patch 0545 | Project Barry | GPL-2.0 (Linux kernel code) | Used: I build it myself | The kernel I run is this recipe plus my patches and one config option. Patch 0545 adds the charge-control files my patch 2001 builds on. See [kernel.md](docs/kernel.md). |
| [ROCKNIX](https://github.com/ROCKNIX/distribution) | The ROCKNIX team | GPL-2.0 (Linux kernel code) | Used | The source tree pb-os's kernel build pulls (tag `20260901`). My lid-wake device-tree patch matches ROCKNIX's Thor device tree. |
| [Armada OS](https://github.com/armada-os/armada) | Armada OS contributors (patch authors: Armada, virtudude, gennro) | GPL-2.0-or-later for its own software (its LICENSE.md). Kernel patches are GPL-2.0. | Included: five kernel patches, unchanged, in [reference/kernel/patches/](reference/kernel/patches/) (2004 to 2008) | Nothing. Copied from commit `1ed5b2b` with their original author lines. |
| SteamOS and the Steam client | Valve | Valve's terms | Used | Unmodified. My plugins change what Steam draws at runtime with CSS and leave Steam's files alone. |

## Controller

| Project | By | License | In this repo | What I took or changed |
|---|---|---|---|---|
| [InputPlumber](https://github.com/ShadowBlip/InputPlumber) | ShadowBlip (William Edwards, Derek J. Clark and contributors) | GPL-3.0 | Included: five patches in [reference/inputplumber/patches/](reference/inputplumber/patches/) | Added a `switch-pro` target (a virtual wired Switch Pro Controller over uhid), a fix for `SendEvent` panicking a tokio worker, a configurable Quick Access chord, and a `HandleEvent` D-Bus method for tests. Made against v0.81.0. On the Thor they run on top of pb-os's two haptics patches. See [switch-pro-identity.md](docs/switch-pro-identity.md). |
| [InputPlumber PR #164](https://github.com/ShadowBlip/InputPlumber/pull/164) | InputPlumber contributors | GPL-3.0 | Reference | Its Switch source driver showed me the Pro Controller's report descriptor and HID reports. |
| [nxbt](https://github.com/Brikwerk/nxbt) | Brikwerk | MIT | Reference | How a Pro Controller answers the host: subcommand replies, SPI flash reads, calibration. |
| [joycontrol](https://github.com/Poohl/joycontrol) | mart1nro, Poohl and contributors | GPL-3.0 | Reference | The same protocol, from another angle. No code copied. |
| [SDL](https://github.com/libsdl-org/SDL) `SDL_hidapi_switch.c` | The SDL project | zlib | Reference | What Steam's side expects from a Pro Controller during setup. |
| Linux `hid-nintendo` | The Linux kernel | GPL-2.0 | Used | The kernel driver that binds my virtual Pro Controller. I also followed its rumble amplitude table. |
| [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) | SteamDeckHomebrew | GPL-2.0 | Used | Runs ThorLook and FatterPad. |
| [@decky/api](https://github.com/SteamDeckHomebrew/loader-api) | SteamDeckHomebrew | LGPL-2.1 | Included: the connection block at the top of both plugin front ends | Unchanged. |
| [Handheld Controller Glyphs](https://github.com/victor-borges/handheld-controller-glyphs) | victor-borges | MIT | Reference | Its method: swap Steam's glyph `<img>` sources and override the controller picture's CSS rule. ThorLook uses the same method with my own code and art. |
| [PCGamingWiki](https://www.pcgamingwiki.com/) | PCGamingWiki contributors | Content: CC BY-NC-SA 3.0 | Used at runtime | `prompts-db` reads each game's controller table from PCGamingWiki's API on the device and keeps the answers locally. This repo holds no wiki data. |

## Gyro

| Project | By | License | In this repo | What I took or changed |
|---|---|---|---|---|
| [hexagonrpc](https://github.com/linux-msm/hexagonrpc) | linux-msm | GPL-3.0 | Used | `hexagonrpcd` serves the sensor process on the Thor's DSP. I build it on the Thor with pb-os's eight patches. Nothing of it is here. |
| pb-os sensor pieces (`sm8550-sensors`, its hexagonrpc patches, `pbos-motiond`) | Project Barry | GPL-2.0 (pb-os) | Reference | My setup service is a port of `sm8550-sensors` and isn't in this repo. My probe ([thor-imu-probe.py](reference/gyro/thor-imu-probe.py)) sends the same sensor-hub messages as `pbos-motiond`, written from scratch. |
| Batocera's Thor notes | Batocera | n/a | Reference | The registry and start-order details for the sensor helpers. |
| AYN's stock sensor configuration and DSP library | AYN | Proprietary | Not included | They come from the Thor's own firmware. Never redistribute them. |

## Artwork

| Source | What I took |
|---|---|
| AYN's official Thor product renders and a SteamDeckHQ review photo | Reference for the drawing's shapes and the button icons' placement. The drawings are new vector work. None of the photos are in this repo. |
| A Tech Tactician photo of the Thor's top edge | Reference for the shoulder-button markers ThorLook draws on Test Device Inputs. Not in this repo. |
| Valve's Steam Deck controller art (`controller_config_controller_steam_deck.svg` in the Steam client) | Reference for style only: fill `#0D131B`, strokes `#8B929A`, line weights. No Valve art files are in this repo. |

## Screenshots

The screenshots in [docs/images/](docs/images/) show Steam's interface (Valve) and Hades' Controls screen (Supergiant Games). They're there to show what the code does. Those interfaces belong to their owners and aren't covered by this repo's CC BY license.

The drawings were made by an OpenAI Codex agent working from those references, and checked against photos and on the device. Everything else was built with Claude Code. See "How this was made" in the [README](README.md).
