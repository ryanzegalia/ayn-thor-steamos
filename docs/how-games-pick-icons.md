# How games pick their button icons

I wanted games that ship Nintendo button icons to show them on the Thor. That meant working out how a game running under Steam decides which icons to draw. Everything below was tested on my Thor in Game Mode (October 2026).

## Three kinds of game

1. **Games that use Steam Input's API** ask Steam which icon to draw for each action. Their icons follow whatever Steam thinks the controller is.
2. **Type-aware games** ask what kind of controller is connected (usually through SDL) and pick an icon set from that. Steam passes the controller type through to them.
3. **Xbox-only games** always draw Xbox icons, whatever is connected. Balatro is one of these on my Thor.

## Proof that Steam passes the type through

With Hades on its Controls screen, I switched the Thor's InputPlumber target to a DualSense. Hades' icons changed from Xbox to PlayStation, while Balatro kept drawing Xbox icons. So a type-aware game on this device does follow the controller type, and a Nintendo identity should get Nintendo icons. That was the reason for building the [Switch Pro identity](switch-pro-identity.md).

## Proton games need one more step

Getting Hades to draw its Switch icons took more than the Switch Pro identity:

| Tried | Result |
|---|---|
| Switch Pro identity, Steam Input on | Xbox icons. Steam even writes `virtualgamepadinfo.txt` with `type=switchpro 057e:2009`, but through Steam Input's virtual pad Proton hands the game a PlayStation or Xbox type, never a Switch type. |
| `SDL_JOYSTICK_HIDAPI_SWITCH=0`, `SDL_XINPUT_ENABLED=0`, or hidraw with Steam Input still on | Xbox icons |
| **Switch Pro identity + Steam Input off for that game + `PROTON_ENABLE_HIDRAW=0x057E/0x2009`** | **Switch icons (Y, B, A, X, ZL, ZR), checked on Hades' Controls screen** |

So a Proton game only draws native Nintendo icons when it reads the Switch Pro itself:

- Turn Steam Input off for the game: `SteamClient.Apps.SetThirdPartyControllerConfiguration(appid, 0)`. The value 1 puts it back to default.
- Let Proton open the Pro Controller's hidraw node with `PROTON_ENABLE_HIDRAW=0x057E/0x2009`. I set this once for the whole session in a systemd user `environment.d` file ([70-fatterpad-nintendo.conf](../reference/fatterpad/70-fatterpad-nintendo.conf)), so Steam and every game inherit it. It does nothing while no Switch Pro device exists.
- Use the Nintendo layout (printed A = A) for that game. Otherwise the game's A ends up on the wrong button.

## Which games ship Nintendo icons?

Steam's own data doesn't predict it. Neither Steam Input API support nor Steam's PlayStation-support metadata tells you whether a game has Nintendo icons (Hades, for one, ships Switch icons on PC). What did predict it was **PCGamingWiki**: each game's page has an `{{Input}}` table with fields like `nintendo prompts`, `nintendo button layout` and `playstation prompts`. My [prompts-db](../reference/fatterpad/prompts-db) asks Steam which games I own, reads those fields for each one over PCGamingWiki's API, and keeps them in one local JSON file. FatterPad then gives every game with `nintendo prompts = true` the Nintendo mode. A game the wiki says nothing about stays on the Xbox layout. A manual flip always wins. Details: [per-game-layout.md](per-game-layout.md).

## What Steam reports for each identity

`thor-steam-pads` ([reference/tools/](../reference/tools/)) asks Steam's UI for its controller list. These are real readings from my Thor:

```
type=100 style=100 vidpid=28de:12f0 nintendo=False reversed=False name=AYN Thor                         (default: the handheld identity)
type=38 style=1 vidpid=057e:2009 nintendo=True reversed=True name=Nintendo Switch Pro Controller      (the Switch Pro identity)
```

Steam keeps per-controller flags (`bNintendoLayout`, `bUseReversedLayout`, `bUseUniversalFaceButtonGlyphs`). On the handheld identity they're all false. On the Switch Pro identity Steam turns on the Nintendo layout by itself, and its own menus then draw circled Nintendo-style letters that match what's printed on the Thor.
