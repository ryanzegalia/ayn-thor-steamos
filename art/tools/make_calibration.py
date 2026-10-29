#!/usr/bin/env python3
"""Derive the Calibration-screen art from thor_lower.svg (run after editing the drawing).

Steam's Settings > Controller > Calibration & Advanced Settings draws the 2015 Steam Controller
(/images/steamcontroller_left.png and _right.png, both 643x464) with its deadzone circles centred on
that controller's stick. Measured on the Thor 2026-10-17 (CDP, Big Picture): the circle centre sits at
(288.5, 168.3) of the left image and (350.0, 168.3) of the right one. ThorLook swaps each image for a
crop of the Thor drawing, at the same 643x464 size, that puts the Thor's own stick on that point, so
Steam's circles land on the Thor's sticks.
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent   # the art/ folder
W, H = 643, 464                 # Steam's image size (natural pixels)
SCALE = 0.62                    # image pixels per drawing unit: keeps the face buttons in the right crop
CROPS = {                       # name: (stick centre in thor_lower.svg, circle centre in Steam's image)
    "thor_cal_left.svg": ((153, 216), (288.5, 168.3)),    # lstick: translate(153 216)
    "thor_cal_right.svg": ((847, 406), (350.0, 168.3)),   # rstick: translate(847 406)
}


def main() -> None:
    src = (HERE / "thor_lower.svg").read_text(encoding="utf-8")
    m = re.match(r"\s*<svg\b[^>]*>", src)
    body = src[m.end():]
    body = re.sub(r"<title[^>]*>.*?</title>", "", body, flags=re.S)
    for name, ((sx, sy), (ix, iy)) in CROPS.items():
        vw, vh = W / SCALE, H / SCALE
        x0, y0 = sx - ix / SCALE, sy - iy / SCALE
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="{x0:.1f} {y0:.1f} {vw:.1f} {vh:.1f}" fill="none">')
        (HERE / name).write_text(head + body, encoding="utf-8")
        print(f"{name}: viewBox {x0:.1f} {y0:.1f} {vw:.1f} {vh:.1f}")


if __name__ == "__main__":
    main()
