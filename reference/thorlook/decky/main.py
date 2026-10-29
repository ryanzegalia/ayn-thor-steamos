#!/usr/bin/env python3
"""Decky backend -- ThorLook. The front end does most of the work (runtime CSS
and a live drawing in Steam's Game Mode window). The backend does two things
it cannot: tell the front end the serial of the Thor's virtual Pro Controller
(so only that controller is renamed), and put the same CSS into Steam's other
windows (Quick Access, main menu, toasts) over Steam's local CEF debugger, the
way CSS Loader does. It also tells the input test screen which of the Thor's
own buttons was pressed last (Home or Quick Access), because Steam only sees the
chord our InputPlumber sends for Quick Access (Home + B) and its drawing shows
the two halves up to 50 ms apart. It also reports the Thor's D-pad, which
Steam's handheld drawing does not show at all. That needs root: InputPlumber
hides the Thor's own input device from everyone else."""
import asyncio
import fcntl
import glob
import json
import os
import time

import aiohttp
import decky

CDP = "http://127.0.0.1:8080/json"
POPUP_TITLES = ("QuickAccess", "MainMenu", "notificationtoasts")
POPUP_SUFFIXES = ("Controller Layout",)
# Steam names the controller type in running text: say "AYN Thor" instead.
RENAME_JS = r"""(() => { if (window.__thorlookText) return 1; const re = /Nintendo Switch Pro [Cc]ontroller/g;
 const fix = (n) => { if (n.nodeValue && n.nodeValue.includes("Switch Pro")) n.nodeValue = n.nodeValue.replace(re, "AYN Thor"); };
 const walk = (root) => { const w = document.createTreeWalker(root, 4); for (let n = w.nextNode(); n; n = w.nextNode()) fix(n); };
 if (!document.body) return 0; walk(document.body);
 window.__thorlookText = new MutationObserver((ms) => { for (const m of ms) { if (m.type === "characterData") fix(m.target);
   else for (const x of m.addedNodes) { if (x.nodeType === 3) fix(x); else if (x.nodeType === 1) walk(x); } } });
 window.__thorlookText.observe(document.body, { childList: true, subtree: true, characterData: true }); return 1; })()"""
INJECT = ("(() => {{ let s = document.getElementById('thorlook-style');"
          " if (!s) {{ s = document.createElement('style'); s.id = 'thorlook-style';"
          " (document.head || document.documentElement).appendChild(s); }}"
          " const css = {css}; if (s.textContent !== css) s.textContent = css; return 1; }})()")


PAD_NAME = "AYN Odin2 Gamepad"   # the Thor's own pad (InputPlumber reads it, mode 000)
BTN_BACK, BTN_MODE = 0x116, 0x13C  # Quick Access (lower right) and Home (lower left)
BTN_DPAD = {0x220: "up", 0x221: "down", 0x222: "left", 0x223: "right"}  # BTN_DPAD_UP..RIGHT
EVIOCGKEY = (2 << 30) | (96 << 16) | (ord("E") << 8) | 0x18  # _IOC(READ, 'E', 0x18, 96)
WATCH_S = 90                       # keep reading this long after the screen asks


def pad_device() -> str | None:
    for name_file in glob.glob("/sys/class/input/event*/device/name"):
        try:
            with open(name_file, encoding="utf-8") as fh:
                if fh.read().strip() == PAD_NAME:
                    return "/dev/input/" + name_file.split("/")[4]
        except OSError:
            continue
    return None


def thor_mac() -> str:
    """The MAC InputPlumber's switch-pro target reports (our fork,
    src/input/target/switch_pro.rs device_mac): Nintendo's OUI 98:b6:e9 plus
    the low three bytes of a FNV-1a hash of /etc/machine-id."""
    try:
        with open("/etc/machine-id", encoding="ascii") as fh:
            machine_id = fh.read().strip()
    except OSError:
        machine_id = ""
    h = 0x811C9DC5
    for byte in machine_id.encode():
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return "98b6e9" + h.to_bytes(4, "big")[1:].hex()


class Plugin:
    css = ""
    task = None
    keys_task = None
    watch_until = 0.0
    pressed_at = {BTN_BACK: None, BTN_MODE: None}  # monotonic time of the last press
    held = set()                                   # buttons down right now

    async def watch_keys(self) -> bool:
        """Read the Thor's Home, Quick Access and D-pad for the next WATCH_S s."""
        Plugin.watch_until = time.monotonic() + WATCH_S
        if not Plugin.keys_task or Plugin.keys_task.done():
            Plugin.keys_task = asyncio.get_event_loop().create_task(self.key_loop())
        return True

    async def pad_keys(self) -> dict:
        """Milliseconds since each button was last pressed (None = not seen),
        and the D-pad directions held now."""
        now = time.monotonic()
        age = lambda t: None if t is None else round((now - t) * 1000)
        return {"qam_ms": age(Plugin.pressed_at[BTN_BACK]), "home_ms": age(Plugin.pressed_at[BTN_MODE]),
                "dpad": [name for code, name in BTN_DPAD.items() if code in Plugin.held],
                "watching": bool(Plugin.keys_task and not Plugin.keys_task.done())}

    async def key_loop(self):
        path = pad_device()
        if not path:
            decky.logger.warning("no %s device: Quick Access drawing falls back to timing", PAD_NAME)
            return
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        held = Plugin.held
        try:
            while time.monotonic() < Plugin.watch_until:
                bits = fcntl.ioctl(fd, EVIOCGKEY, bytes(96))  # current state; works while InputPlumber grabs it
                now = time.monotonic()
                for code in (BTN_BACK, BTN_MODE, *BTN_DPAD):
                    down = bool(bits[code // 8] >> (code % 8) & 1)
                    if down and code not in held and code in Plugin.pressed_at:
                        Plugin.pressed_at[code] = now
                    (held.add if down else held.discard)(code)
                await asyncio.sleep(0.004)
        except OSError as e:
            decky.logger.warning("reading %s failed: %s", path, e)
        finally:
            held.clear()  # nothing reads as held once nobody is reading
            try:
                os.close(fd)
            except OSError:  # already gone when Decky unloads the plugin (Errno 9, 10-14)
                pass

    async def thor_serial(self) -> str:
        return thor_mac()

    async def set_popup_css(self, css: str) -> bool:
        Plugin.css = css or ""
        await self.inject_popups()
        return True

    async def inject_popups(self) -> int:
        if not Plugin.css:
            return 0
        done = 0
        expr = INJECT.format(css=json.dumps(Plugin.css))
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(CDP) as resp:
                targets = await resp.json(content_type=None)
            for t in targets:
                title = t.get("title") or ""
                ws_url = t.get("webSocketDebuggerUrl")
                if not ws_url or not (title.startswith(POPUP_TITLES) or title.endswith(POPUP_SUFFIXES)):
                    continue
                try:
                    async with session.ws_connect(ws_url, max_msg_size=0) as ws:
                        await ws.send_json({"id": 1, "method": "Runtime.evaluate",
                                            "params": {"expression": expr}})
                        await ws.receive_json(timeout=5)
                        await ws.send_json({"id": 2, "method": "Runtime.evaluate",
                                            "params": {"expression": RENAME_JS}})
                        await ws.receive_json(timeout=5)
                        done += 1
                except Exception as e:  # a window closing mid-call is normal
                    decky.logger.debug("inject into %s failed: %s", title, e)
        return done

    async def loop(self):
        while True:
            try:
                await self.inject_popups()
            except Exception as e:
                decky.logger.warning("popup css pass failed: %s", e)
            await asyncio.sleep(10)

    async def _main(self):
        decky.logger.info("ThorLook loaded; Thor controller serial ends %s", thor_mac())
        Plugin.task = asyncio.get_event_loop().create_task(self.loop())

    async def _unload(self):
        if Plugin.task:
            Plugin.task.cancel()
        if Plugin.keys_task:
            Plugin.keys_task.cancel()
        decky.logger.info("ThorLook unloaded")
