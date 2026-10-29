#!/usr/bin/env python3
"""Ask the local DSU server (thor-motiond, 127.0.0.1:26760) what an emulator
would: protocol version, slot 0 info, then motion data for a few seconds.

  dsu-probe.py [seconds]
"""
import socket
import struct
import sys
import time
import zlib

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 3
CID = 0x7468_6f72


def pkt(msg_type, payload=b""):
    body = struct.pack("<I", msg_type) + payload
    p = bytearray(b"DSUC" + struct.pack("<HHII", 1001, len(body), 0, CID) + body)
    struct.pack_into("<I", p, 8, zlib.crc32(p) & 0xFFFFFFFF)
    return bytes(p)


def ok_crc(d):
    c = struct.unpack_from("<I", d, 8)[0]
    z = bytearray(d); struct.pack_into("<I", z, 8, 0)
    return zlib.crc32(z) & 0xFFFFFFFF == c


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(1.0)
srv = ("127.0.0.1", 26760)
s.sendto(pkt(0x100000), srv)
d, _ = s.recvfrom(256)
print(f"version reply {d[:4]} v{struct.unpack_from('<H', d, 20)[0]} crc_ok={ok_crc(d)}")
s.sendto(pkt(0x100001, struct.pack("<i", 1) + b"\x00"), srv)
d, _ = s.recvfrom(256)
slot, state, model, conn = d[20:24]
print(f"slot {slot}: state {state} (2=connected) model {model} (2=full gyro) conn {conn} battery {d[30]} crc_ok={ok_crc(d)}")
end, n, last = time.monotonic() + SECS, 0, None
s.sendto(pkt(0x100002, b"\x01\x00" + bytes(6)), srv)
reg = time.monotonic()
while time.monotonic() < end:
    if time.monotonic() - reg > 0.5:
        s.sendto(pkt(0x100002, b"\x01\x00" + bytes(6)), srv); reg = time.monotonic()
    try:
        d, _ = s.recvfrom(256)
    except socket.timeout:
        continue
    if len(d) >= 100 and struct.unpack_from("<I", d, 16)[0] == 0x100002:
        n += 1
        last = (struct.unpack_from("<Q", d, 68)[0], struct.unpack_from("<3f", d, 76), struct.unpack_from("<3f", d, 88), ok_crc(d))
print(f"data packets: {n} in {SECS:.0f} s ({n / SECS:.0f}/s)")
if last:
    ts, a, w, c = last
    print(f"last: accel {['%+.3f' % x for x in a]} g  gyro {['%+.2f' % x for x in w]} dps  crc_ok={c}")
print("DSU OK" if n > 0 else "DSU FAIL: no data")
