# Gotchas

Things that cost me time, so they don't cost you any. Each one was seen on my Thor.

## InputPlumber

- **Button names are Linux key codes, not positions.** `South` is `BTN_A`, `East` is `BTN_B`, `North` is `BTN_X`, `West` is `BTN_Y`. On the Thor, `South` is the right-hand button. My Switch Pro target first sent `North` to the Pro's Y, so X and Y were swapped. Patch 0005 fixes that.
- **`SendEvent` on InputPlumber 0.81.0 can panic a tokio worker and hang the caller.** Patch 0002 fixes it. Before the fix, don't use it for live button injection.
- **`LoadProfilePath` and `SetTargetDevices` work live** over the system D-Bus as the normal `steamos` user, with no reconnect. Wait until no face button is held before switching, or a button can stay stuck down across the switch.
- **Check that only one Thor config loads.** Leftover Thor configs in `/etc/inputplumber/devices.d/` raced the real one at boot, and one of them turned the pad into an Xbox Elite with a different face-button swap. See [buttons.md](buttons.md).
- **An InputPlumber restart drops the pad for a moment.** Don't restart it while a game runs.

## Steam

- **A Switch Pro Controller has no analog triggers.** ZL and ZR are on/off (0 or 32767 on Steam's test screen). You can't fix that with a new USB id, because Steam picks its driver by USB id and an unknown one becomes a generic pad.
- **Proton hides the Switch Pro from games while Steam Input is on.** Through Steam Input's virtual pad, a Proton game sees a PlayStation or Xbox type, never a Switch. For native Switch icons: Steam Input off for that game, and `PROTON_ENABLE_HIDRAW=0x057E/0x2009`. See [how-games-pick-icons.md](how-games-pick-icons.md).
- **Steam's Quick Access shortcut on the Switch Pro is a chord,** and its two halves must arrive in separate reports. In one report, Steam treats B as Back. 10 ms apart works.
- **Steam's Test Device Inputs samples about 20 times a second.** It can draw a fast chord as two buttons held at once. Don't trust it for timing.
- **Steam's CSS class names are hashed** and change between builds. Find rules by their image URL, not their class.
- **Steam's Quick Access, main menu and toasts are separate browser windows.** Anything you inject has to go into each one, including ones opened later.
- **Steam reads a game's Steam Input setting at launch.** Change it before the game starts.
- **Gamescope re-sets its focus atoms about 75 times a second** even when nothing changes. A focus watcher has to ignore repeats, or it eats a third of a CPU core.

## Gyro

- **Start the sensor helpers early in boot,** after the sound card appears. Attaching late never brought the sensor hub's service up until a reboot.
- **The default handheld identity doesn't show gyro on Steam's test screen,** even with motion in its reports.
- **The gyro's zero only learns while the Thor lies still.** In the hands, a warm sensor and tremor creep into an emulator's aim unless you filter them (my DSU feed does, [gyro.md](gyro.md)).
- **An always-on 200 Hz stream in Python isn't free:** about 3.5% of a core on average on my Thor.
