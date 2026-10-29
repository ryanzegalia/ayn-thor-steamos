# The Switch Pro identity (InputPlumber patches)

For Steam to treat the Thor as a Nintendo controller, the virtual pad InputPlumber presents has to be one Steam already knows as Nintendo. Steam picks its driver by USB id, so a made-up id just becomes a generic pad. When I looked (October 2026, InputPlumber v0.82.0), InputPlumber could read a Switch Pro but had no Switch Pro *target*, and I found no other Linux virtual Switch Pro device that Steam accepts. So I wrote one: [five patches](../reference/inputplumber/patches/) against InputPlumber v0.81.0.

## What the patches do

| Patch | What |
|---|---|
| 0001 | Adds a `switch-pro` target: a wired Nintendo Switch Pro Controller (USB `057e:2009`) over uhid. It answers the setup handshake that Steam (SDL's `SDL_hidapi_switch.c`) and the kernel's `hid-nintendo` driver run before a Pro Controller streams input, then streams full `0x30` input reports and passes rumble back. It's registered beside the existing targets, following the shape of the HORIPAD STEAM target. |
| 0002 | Fixes InputPlumber's `SendEvent` D-Bus method panicking a tokio worker and hanging the caller, and names the home-light and vibration subcommands the target acknowledges. |
| 0003 | Quick Access: a Switch Pro has no Quick Access button, so the Thor's Quick Access button sends a chord Steam understands. It's read from a file, default `Guide` + `East` (Home + B). |
| 0004 | Adds `CompositeDevice.HandleEvent` on D-Bus: inject an event *through* the device profile, as if the button were pressed, for end-to-end tests of profile swaps. |
| 0005 | Sends the Quick Access chord's two halves 10 ms apart, and fixes the face-button mapping so `North` goes to the Pro's X and `West` to its Y. |

All five apply cleanly to a stock v0.81.0 tree (checked with `git apply` on 29 October 2026). On my Thor they're built on top of pb-os's two haptics patches. I haven't built them on a plain v0.81.0.

## Turning it on

The target is switched live over InputPlumber's system D-Bus, with no reboot. The `steamos` user can make the call. It's `SetTargetDevices` on the composite device (bus `org.shadowblip.InputPlumber`, object `/org/shadowblip/InputPlumber/CompositeDevice0`, interface `org.shadowblip.Input.CompositeDevice`), with `["switch-pro", "keyboard"]` for the Switch Pro and `["deck-uhid", "keyboard"]` to go back to the stock handheld pad. FatterPad makes this call per game (`apply_identity` in [fatterpad-abxy](../reference/fatterpad/fatterpad-abxy)). Before switching, it waits until no face button is held, so a button can't get stuck down across the switch. [thor-ip-fork](../reference/tools/thor-ip-fork) is the small script I use to run the patched binary in place of the stock one through a systemd drop-in, with the stock binary one command away.

## How I checked it

| Check | Result on my Thor |
|---|---|
| [thor-pro-probe](../reference/tools/thor-pro-probe): is the kernel's Nintendo driver bound, and is input streaming? | `bound=nintendo reports_0x30_per_s=221 hid=0003:057E:2009.0007 hidraw=/dev/hidraw1` |
| [thor-steam-pads](../reference/tools/thor-steam-pads): what does Steam think it is? | `type=38 style=1 vidpid=057e:2009 nintendo=True reversed=True name=Nintendo Switch Pro Controller` |
| Steam's menus, by hand | A on the right confirms, B goes back, Home opens the Steam menu, Quick Access opens Quick Access. Rumble works on Test Device Inputs. |
| Games | See [how-games-pick-icons.md](how-games-pick-icons.md): Hades draws its Switch icons. |

## Why it isn't my default

**A Switch Pro report has no analog triggers.** ZL and ZR are on/off, and Steam's test screen reads them as 0 or 32767. The Thor's triggers are analog, and I want analog everywhere a game can use it. Steam also picks its driver by USB id, so I can't make a "Switch Pro with analog triggers": a new id is just a generic pad.

So my default is InputPlumber's stock handheld target (`deck-uhid`), which has analog triggers and a real Quick Access button, and [ThorLook](thorlook.md) makes Steam draw it as a Thor. The Switch Pro identity is only used per game, for games that ship Nintendo icons ("Nintendo mode"). There ZL/ZR being on/off matches a real Switch anyway.

## The Quick Access chord

On the Switch Pro identity, the Thor's Quick Access button has to become something Steam already understands. My target sends Home, then B (`Guide` + `East` in InputPlumber's names), and Steam opens Quick Access on that (tested by hand). It depends on a timing detail I measured:

- If Home and the second button arrive in the **same report**, Steam doesn't open Quick Access, and B acts as Back. So the two halves have to arrive in separate reports. 10 ms apart works.
- Steam's Test Device Inputs screen samples the pad about 20 times a second, so it sometimes draws the chord as "Home and B pressed" in one frame. No gap under about 70 ms reliably avoids that. Instead, [ThorLook](thorlook.md)'s backend reads the Thor's own pad to show which physical button was really pressed.
