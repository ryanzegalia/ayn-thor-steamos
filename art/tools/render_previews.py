#!/usr/bin/env python3
"""Render the PNG previews in art/png/ from the SVGs with headless Chrome.

    CHROME=google-chrome python3 art/tools/render_previews.py

Writes thor_lower.png, thor_open.png, glyphs.png and thor_intro.gif (the
animated drawing's 2.2 s intro, frame by frame: SMIL paused at each time).
Needs Pillow and a Chrome or Chromium binary.
"""
import os, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

ART = Path(__file__).resolve().parent.parent
OUT = ART / "png"
CHROME = os.environ.get("CHROME", "google-chrome")
BG = "#1b2838"  # Steam's dark page colour

def shot(html: str, w: int, h: int, dest: Path) -> None:
    with tempfile.TemporaryDirectory() as td:
        page = Path(td) / "p.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        f"--user-data-dir={td}/profile", f"--window-size={w},{h}",
                        f"--screenshot={dest}", page.as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def page(body: str) -> str:
    return (f"<!doctype html><html><body style='margin:0;background:{BG}'>{body}</body></html>")

def svg(name: str) -> str:
    return (ART / name).read_text(encoding="utf-8").split("?>", 1)[-1]

def main() -> int:
    OUT.mkdir(exist_ok=True)
    shot(page(svg("thor_lower.svg").replace("<svg", "<svg width='1000' height='640'", 1)), 1000, 640, OUT / "thor_lower.png")
    shot(page(svg("thor_open.svg").replace("<svg", "<svg width='1000' height='900'", 1)), 1000, 900, OUT / "thor_open.png")
    # Glyph sheet: the Steam-style set on the dark page, the light set on white.
    names = ("home", "triangle", "square", "back_qam")
    def row(kind, bg):
        cells = "".join(f"<div style='width:96px;height:96px;display:flex;align-items:center;justify-content:center'>"
                        f"<img src='{(ART / 'glyphs' / f'glyph_{n}_{kind}.svg').as_uri()}' width='72' height='72'></div>" for n in names)
        return f"<div style='display:flex;gap:8px;padding:8px;background:{bg}'>{cells}</div>"
    shot(f"<!doctype html><html><body style='margin:0;background:{BG}'>{row('steam', BG)}{row('dark', BG)}{row('light', '#EEF1F4')}</body></html>",
         432, 336, OUT / "glyphs.png")
    # Intro animation: pause SMIL at t and screenshot, 0.0 .. 2.4 s.
    frames, times = [], [i / 10 for i in range(25)]
    anim = svg("thor_lower_animated.svg").replace("<svg", "<svg id='a' width='1000' height='640'", 1)
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(times):
            dest = Path(td) / f"f{i:02d}.png"
            shot(page(anim + f"<script>const s=document.getElementById('a');s.pauseAnimations();s.setCurrentTime({t});</script>"),
                 1000, 640, dest)
            frames.append(Image.open(dest).convert("RGB").resize((600, 384), Image.LANCZOS))
    hold = [frames[-1]] * 8  # rest on the settled drawing before looping
    seq = frames + hold
    seq[0].save(OUT / "thor_intro.gif", save_all=True, append_images=seq[1:], duration=100, loop=0, optimize=True)
    for f in ("thor_lower.png", "thor_open.png", "glyphs.png", "thor_intro.gif"):
        print(f, (OUT / f).stat().st_size, "bytes")
    return 0

if __name__ == "__main__":
    sys.exit(main())
