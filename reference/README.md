# Reference code

This is the code that runs on my Thor. On 29 October 2026 I compared every file here with the copy on the device, and they were byte-for-byte the same. Since then I've cleaned up comments for publishing, set the two plugins' `author` field to my name, and changed ThorLook's `build.py` to find its art in this repo's `art/` and `art/glyphs/` folders (a small lookup function). Before the comment cleanup, rebuilding ThorLook from these files gave the same `index.js` that runs on the Thor, apart from its one-line header.

It's here to read and borrow from, not to install. Paths, the `steamos` user, my emulator launchers (`thor-launch`, `thor-browse`) and the systemd setup are all mine. Docs for each piece are in [docs/](../docs/).

| Folder | What | Docs |
|---|---|---|
| [inputplumber/patches/](inputplumber/) | Five patches to InputPlumber v0.81.0: the `switch-pro` target and fixes. GPL-3.0. | [switch-pro-identity.md](../docs/switch-pro-identity.md) |
| [fatterpad/](fatterpad/) | `fatterpad-abxy` (per-game layout and identity daemon), `prompts-db` (the PCGamingWiki list), their systemd units, the Proton environment file, and the Quick Access panel. | [per-game-layout.md](../docs/per-game-layout.md) |
| [thorlook/](thorlook/) | The Decky plugin that draws the Thor in Steam. Run `build.py` to make `decky/dist/index.js`. | [thorlook.md](../docs/thorlook.md) |
| [tools/](tools/) | `thor-pro-probe` (is the virtual Pro Controller bound and streaming?), `thor-steam-pads` (what Steam thinks each pad is), `steam-cdp.py` (runs JavaScript in Steam's UI through its local CEF debugger), `thor-ip-fork` (switch between the patched and stock InputPlumber). | |
| [kernel/](kernel/) | My kernel patches (three mine, five from Armada OS), the lid-wake device-tree patch, the config fragment, and the scripts I build, swap, check and roll back the kernel with. These run on a PC and on the Thor around a kernel swap. They aren't resident on the device, so they weren't part of the byte-for-byte check above. Patches are GPL-2.0, scripts MIT. | [kernel.md](../docs/kernel.md) |
| [gyro/](gyro/) | The motion daemon (sensor hub to DSU for emulators and to InputPlumber), the sensor setup service, the hexagonrpc build and pb-os's patches for it, the emulator config tool, and probes. AYN's own sensor files aren't included. | [gyro.md](../docs/gyro.md) |

Licenses: the patches are GPL-3.0. Everything else here is MIT, except the Decky API connection block at the top of the two plugin front ends, which comes from `@decky/api` (LGPL-2.1). See [LICENSE](../LICENSE).

`steam-cdp.py` talks to Steam's CEF debugger on `127.0.0.1:8080`, where it listens in Game Mode on my Thor, and runs code in Steam's `SharedJSContext` page. `prompts-db`, FatterPad's Steam Input switch and `thor-steam-pads` all go through it.
