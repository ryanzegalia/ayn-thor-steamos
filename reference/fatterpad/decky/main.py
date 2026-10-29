#!/usr/bin/env python3
"""Decky backend -- FatterPad (per-game face buttons on the AYN Thor).

A thin front for ~/.local/bin/fatterpad-abxy (thor/steamos-fatterpad), which
owns the config and the live InputPlumber switch. Runs as the steamos user
(no root flag): the daemon and its config are the user's.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from typing import Any

import decky

HOME = getattr(decky, "DECKY_USER_HOME", "") or "/home/steamos"
CLI = os.path.join(HOME, ".local", "bin", "fatterpad-abxy")
# PyInstaller's LD_LIBRARY_PATH breaks system binaries; same fix as pbos-utils.
ENV = {"PATH": "/usr/bin:/usr/sbin", "LANG": "C.UTF-8", "HOME": HOME,
       "XDG_RUNTIME_DIR": f"/run/user/{os.getuid()}"}


def cli(*args: str) -> dict[str, Any]:
    r = subprocess.run(["/usr/bin/python3", CLI, *args], capture_output=True, text=True,
                       timeout=20, env=ENV)
    if r.returncode != 0:
        return {"ok": False, "error": (r.stderr or r.stdout).strip() or f"exit {r.returncode}"}
    try:
        return {"ok": True, **json.loads(r.stdout)}
    except ValueError:
        return {"ok": False, "error": r.stdout.strip()}


def app_args(appid: Any) -> list[str]:
    try:
        n = int(appid)
    except (TypeError, ValueError):
        return []
    return ["--app", str(n)] if n > 0 else []


class Plugin:
    async def _main(self) -> None:
        decky.logger.info(f"FatterPad: cli {CLI} exists={os.path.exists(CLI)}")

    async def _unload(self) -> None:
        pass

    async def status(self, appid: Any = None, *_: Any) -> dict[str, Any]:
        return await asyncio.to_thread(cli, "status", *app_args(appid))

    async def set_layout(self, mode: str, scope: str = "game", appid: Any = None, *_: Any) -> dict[str, Any]:
        if mode not in ("letters", "positions"):
            return {"ok": False, "error": f"unknown layout {mode!r}"}
        if scope == "default":
            r = await asyncio.to_thread(cli, "default", mode)
            decky.logger.info(f"default {mode}: {r}")
            return r
        extra = ["--class"] if scope == "class" else []
        r = await asyncio.to_thread(cli, "set", mode, *extra, *app_args(appid))
        decky.logger.info(f"set {mode} {scope} app={appid}: {r}")
        return r

    async def set_identity(self, identity: str, appid: Any = None, *_: Any) -> dict[str, Any]:
        """What the Thor reaches Steam as for that game: deck (analog
        triggers) or switch-pro; "forget" drops the game's choice."""
        if identity not in ("switch-pro", "deck", "forget"):
            return {"ok": False, "error": f"unknown identity {identity!r}"}
        r = await asyncio.to_thread(cli, "identity", identity, *app_args(appid))
        decky.logger.info(f"identity {identity} app={appid}: {r}")
        return r

    async def set_nintendo(self, state: str, appid: Any = None, *_: Any) -> dict[str, Any]:
        """Nintendo mode for that game: on, off, or forget (follow
        PCGamingWiki again). Takes effect at the game's next launch."""
        if state not in ("on", "off", "forget"):
            return {"ok": False, "error": f"unknown state {state!r}"}
        r = await asyncio.to_thread(cli, "nintendo", state, *app_args(appid))
        decky.logger.info(f"nintendo {state} app={appid}: {r}")
        return r

    async def forget(self, scope: str = "game", appid: Any = None, *_: Any) -> dict[str, Any]:
        extra = ["--class"] if scope == "class" else []
        return await asyncio.to_thread(cli, "forget", *extra, *app_args(appid))
