# Per-game layouts and Nintendo mode (FatterPad)

FatterPad is my name for the Thor's controller helper. On SteamOS it's three pieces, all in [reference/fatterpad/](../reference/fatterpad/):

| Piece | What it does |
|---|---|
| [`fatterpad-abxy`](../reference/fatterpad/fatterpad-abxy) | A systemd user daemon (Python). It follows the game in front, picks its layout (Xbox or Nintendo) and identity (handheld or Switch Pro), and applies them live. |
| [`prompts-db`](../reference/fatterpad/prompts-db) | Keeps a local list of every Steam game I own with PCGamingWiki's answer on Nintendo button icons. Runs from a systemd timer 3 minutes after boot, then every 12 hours. |
| [`decky/`](../reference/fatterpad/decky/) | A small Quick Access panel with one toggle, "Nintendo layout (A on the right)", for the game that's running. |

## The rule

- **Steam's own menus:** the Nintendo layout, because that's what the hardware is. The A on the right confirms.
- **Games, by default:** the Xbox layout. When a game says A, you press the bottom button.
- **Nintendo mode,** for games that ship Nintendo icons: the Switch Pro identity, Steam Input off for that game, and the Nintendo layout. The game draws its own Switch icons and the printed letters match them. ZL/ZR are on/off, as on a real Switch.
- **My emulator launchers** keep the Nintendo layout, because those emulator configs were set up for it. That includes PS1 in RetroArch. PSP and PS2 get the Xbox layout (Cross is the bottom button). Eden (Switch) does its own mapping by position, so it gets the Xbox layout too, and the printed A still lands on Switch A.

Precedence, highest first: a choice saved for that game, Nintendo mode, the window class (every game of one emulator), the launcher, the default.

## How it switches layouts live

The layout is an InputPlumber device profile. FatterPad builds two from the stock default profile (`/usr/share/inputplumber/profiles/default.yaml`): `letters` is the stock profile unchanged, and `positions` swaps South with East and North with West. It loads one with `LoadProfilePath` on InputPlumber's D-Bus. The pad doesn't reconnect, so the switch is instant and safe mid-game. Like the identity switch, it waits until no face button is held.

To know which game is in front, it watches gamescope's `GAMESCOPE_FOCUSED_APP` and `GAMESCOPE_FOCUSED_WINDOW` on the root window (`xprop -spy`). Gamescope re-sets those atoms about 75 times a second even when nothing changes. Reacting to each one cost a third of a CPU core. Ignoring repeats and deciding at most once a second brought it to under 1% of a core, with Hades running.

## How Nintendo mode happens

1. `prompts-db` has already recorded PCGamingWiki's `nintendo prompts` answer for the game.
2. When the wiki says `true`, FatterPad turns Steam Input off for that game *before it launches*, because Steam reads that setting at launch. It calls `SteamClient.Apps.SetThirdPartyControllerConfiguration(appid, 0)` through Steam's local CEF debugger ([steam-cdp.py](../reference/tools/steam-cdp.py)). It only restores the setting for games it switched off itself.
3. It switches the identity to the Switch Pro as soon as Steam starts launching the game. It spots Steam's `reaper SteamLaunch AppId=N` process, so the switch has already happened while the game is still starting.
4. `PROTON_ENABLE_HIDRAW=0x057E/0x2009` is already set for the session ([70-fatterpad-nintendo.conf](../reference/fatterpad/70-fatterpad-nintendo.conf)), so Proton hands the game the Pro Controller's hidraw node.
5. When the game closes, the Thor goes back to the handheld identity.

You can override it per game: `fatterpad-abxy nintendo on|off|forget`. "Forget" means "follow PCGamingWiki again". There's also the Quick Access toggle, and a manual choice always wins.

## Checked on my Thor

- **Hades** (wiki: Nintendo icons). A plain launch logged `identity switch-pro (Nintendo mode (PCGamingWiki))`. The Controls screen drew Y, B, A, X and ZL/ZR. The printed A selected and the printed B went back.
- **Balatro** (no Nintendo icons). The log said `positions (auto: default)` on the handheld identity, and the game drew Xbox icons. The bottom button (printed B) selected and the right one (printed A) went back.
- **A RetroArch game** started from my launcher. `fatterpad-abxy status` reported `layout: letters`, and the printed A advanced while the printed B did nothing on that screen.
- **Mario Kart 8 in Eden Duo**. A and B landed on Switch A and B.
- After each game, the Thor went back to `type=100 ... name=AYN Thor`.
- `prompts-db status` reports no owned game left to look up, and new games get added on the next run.

## Use it

```
fatterpad-abxy status          # the game in front, its layout, and why
fatterpad-abxy flip            # switch this game's layout and remember it
fatterpad-abxy default positions
fatterpad-abxy nintendo on --app 1145360
prompts-db update              # add new games, re-read pages that changed
prompts-db status
```

Config lives in `~/.config/fatterpad/abxy.json`, and the PCGamingWiki answers in `~/.local/share/fatterpad/prompts.json`. `prompts-db` tries to be polite to a volunteer-run wiki: it sends a User-Agent naming itself, makes at most one request a second, backs off on errors, and only re-reads pages whose revision changed.

`fatterpad-abxy` also has an older `classify` command that sorted games from Steam's own data. The PCGamingWiki list replaced it, because Steam's data didn't predict Nintendo icons, so it isn't part of what I'm claiming works.
