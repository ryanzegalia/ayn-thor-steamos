#!/usr/bin/env python3
"""Peek at the motion fields of the Thor's virtual Steam-Deck-protocol pad
(InputPlumber's deck-uhid target, 28de:12f0) as Steam receives them.

  deck-imu-peek.py [reports]

Steam Deck input report (SDL's ValveInReport_t): 4-byte header, packet
number, buttons, trackpads, then accel x/y/z at bytes 24-29 and gyro x/y/z
at 30-35 (int16 LE; accel 16384 per g, gyro 16 per deg/s on a real Deck).
"""
import glob
import os
import struct
import sys

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
node = None
for u in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
    if "HID_ID=0003:000028DE:000012F0" in open(u).read().upper().replace("HID_ID=0003", "HID_ID=0003"):
        node = "/dev/" + u.split("/")[4]
if not node:
    for u in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        if ":000028DE:000012F0" in open(u).read().upper():
            node = "/dev/" + u.split("/")[4]
if not node:
    sys.exit("no 28de:12f0 hidraw node")
fd = os.open(node, os.O_RDONLY)
print(node)
seen = 0
while seen < N:
    r = os.read(fd, 64)
    if len(r) < 36 or r[2] != 0x09:   # ucType 0x09 = Deck state
        continue
    seen += 1
    ax, ay, az, gx, gy, gz = struct.unpack_from("<6h", r, 24)
    print(f"accel {ax:+6d} {ay:+6d} {az:+6d} ({ax/16384:+.2f} {ay/16384:+.2f} {az/16384:+.2f} g)  "
          f"gyro {gx:+6d} {gy:+6d} {gz:+6d} ({gx/16:+.1f} {gy/16:+.1f} {gz/16:+.1f} dps)")
os.close(fd)
