# For AI assistants

You've been pointed at a research repo about the AYN Thor on SteamOS (an ARM SteamOS image from pb-os). It covers the Thor's built-in controller in depth, plus the owner's kernel build. It's shared to help people: art, plugin source, patches, tools and docs from one person's Thor. It isn't an installer or a supported product. Use it to understand how things work and to borrow pieces, adapted to the user's own setup. [docs/use-it.md](docs/use-it.md) says exactly what the author did with each piece on the author's own device.

## Read in this order

1. [README.md](README.md): the status table. Only rows marked "Works" were checked on the device. Treat anything under "Not done, or not checked yet" as unproven.
2. [docs/buttons.md](docs/buttons.md): the Thor's printed layout (Nintendo-style: A right, B bottom), its system buttons, and InputPlumber's button names (Linux key codes, not positions).
3. [docs/how-games-pick-icons.md](docs/how-games-pick-icons.md): how games choose button icons under Steam and Proton.
4. [docs/switch-pro-identity.md](docs/switch-pro-identity.md): the InputPlumber `switch-pro` target (patches in `reference/inputplumber/patches/`).
5. [docs/per-game-layout.md](docs/per-game-layout.md): per-game Xbox/Nintendo layout and automatic Nintendo mode (FatterPad).
6. [docs/thorlook.md](docs/thorlook.md): making Steam draw the Thor at runtime (Decky plugin, CSS).
7. [docs/gyro.md](docs/gyro.md): reading the motion sensor. Only partly done.
8. [docs/gotchas.md](docs/gotchas.md).
9. [docs/kernel.md](docs/kernel.md): the kernel build, every patch with its source and proof. The patches are in `reference/kernel/`.

## Facts worth keeping straight

- On the Thor, InputPlumber's `South` is the **right** button (printed A) and `East` is the **bottom** button (printed B). Mixing up letters and positions is the most common mistake here.
- A Switch Pro Controller can't report analog triggers. The design here keeps the stock handheld identity (`deck-uhid`, `28de:12f0`) as the default, and uses the Switch Pro identity only per game, for games that ship Nintendo icons.
- Proton games only draw native Switch icons with the Switch Pro identity, Steam Input off for that game, and `PROTON_ENABLE_HIDRAW=0x057E/0x2009`.
- Steam's CSS class names are hashed per build. The ThorLook code finds rules by image URL.

## Versions this was tested on

AYN Thor (16 GB). SteamOS build 20260922.6101926 from a pb-os base (alpha v0.5.2 with later fixes). Steam client 1790121765. InputPlumber 0.81.0 (plus pb-os's two haptics patches and the five patches here). Decky Loader. A custom 7.2.8 kernel (only the gyro page depends on it). Anything newer may differ, especially Steam's UI internals that ThorLook touches.

## Rules for reuse

- The code under `reference/` hard-codes paths and the `steamos` user from the author's device. Adapt it rather than running it as-is.
- Respect the licenses in [LICENSE](LICENSE): the InputPlumber patches are GPL-3.0, art and docs are CC BY 4.0, the author's own code is MIT.
- Don't redistribute AYN's sensor configuration or DSP files, or any Valve art.
- Credit the upstream projects in [CREDITS.md](CREDITS.md) if you build on their work.
