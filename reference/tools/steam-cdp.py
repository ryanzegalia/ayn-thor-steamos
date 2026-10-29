#!/usr/bin/env python3
"""Evaluate JavaScript in Steam's SharedJSContext on the Thor (Game Mode).

Runs ON the Thor (system python3 has aiohttp). Steam's CEF debugger listens on
127.0.0.1:8080 there. The result is printed as JSON.

    python3 steam-cdp.py 'Object.keys(SteamClient)'      # one expression
    python3 steam-cdp.py - < script.js                    # async body with return
"""
import asyncio
import json
import sys
import urllib.request

import aiohttp

CDP = "http://127.0.0.1:8080/json"


def target() -> str:
    with urllib.request.urlopen(CDP, timeout=5) as r:
        for t in json.load(r):
            if t.get("title") == "SharedJSContext":
                return t["webSocketDebuggerUrl"]
    sys.exit("SharedJSContext not found (is Steam in Game Mode?)")


async def evaluate(expr: str, body: bool) -> object:
    # body: a full async function body with its own return (the "-" form).
    code = f"(async () => {{ {expr} }})()" if body else f"(async () => {{ return ({expr}); }})()"
    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(target(), max_msg_size=0) as ws:
            await ws.send_json({"id": 1, "method": "Runtime.evaluate", "params": {
                "expression": code,
                "awaitPromise": True, "returnByValue": True}})
            async for msg in ws:
                data = json.loads(msg.data)
                if data.get("id") == 1:
                    res = data.get("result", {})
                    if "exceptionDetails" in res:
                        sys.exit("JS error: " + json.dumps(res["exceptionDetails"])[:2000])
                    return res.get("result", {}).get("value")


def main() -> None:
    body = sys.argv[1:] == ["-"]
    expr = sys.stdin.read() if body else " ".join(sys.argv[1:])
    print(json.dumps(asyncio.run(evaluate(expr, body)), indent=1, default=str))


if __name__ == "__main__":
    main()
