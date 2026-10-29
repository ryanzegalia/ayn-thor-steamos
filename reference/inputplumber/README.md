# InputPlumber patches

Five patches to [InputPlumber](https://github.com/ShadowBlip/InputPlumber) v0.81.0, made with `git format-patch`. They're licensed GPL-3.0, like InputPlumber itself.

| Patch | What |
|---|---|
| `0001` | Adds the `switch-pro` target: a wired Nintendo Switch Pro Controller (`057e:2009`) over uhid. It handles the setup handshake, full `0x30` input reports and rumble. |
| `0002` | Fixes `SendEvent` panicking a tokio worker, and names the home-light and vibration subcommands the target acknowledges. |
| `0003` | The Quick Access chord is read from a file, default `Guide` + `East`. |
| `0004` | Adds `CompositeDevice.HandleEvent` on D-Bus: inject an event through the device profile, for tests. |
| `0005` | A 10 ms gap between the chord's two halves, and `North` to the Pro's X, `West` to its Y. |

Apply them to a v0.81.0 checkout:

```
git checkout v0.81.0
git am /path/to/patches/*.patch
```

All five apply cleanly to a stock v0.81.0 tree (checked with `git apply` on 29 October 2026). On my Thor they're built on top of pb-os's two haptics patches, and that's the build I tested. I haven't built them on a plain v0.81.0. The Quick Access chord file is `/var/lib/thor-inputplumber/switch-pro-qam`.

How it behaves and how I checked it: [docs/switch-pro-identity.md](../../docs/switch-pro-identity.md).
