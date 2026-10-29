#!/usr/bin/env python3
"""List QRTR services (like linux-msm's qrtr-lookup). The Thor's sensor hub
is service 400 once the ADSP sensors process is served by hexagonrpcd.

  qrtr-lookup.py [service]
"""
import socket
import struct
import sys

QRTR_PORT_CTRL = 0xFFFFFFFE
QRTR_TYPE_NEW_SERVER = 4
QRTR_TYPE_NEW_LOOKUP = 10
NAMES = {15: "test", 41: "ipa?", 42: "servreg-notifier", 64: "servreg-locator", 66: "ssctl",
         400: "SNS client (sensors)", 769: "?", 0x110: "?"}


def lookup(service=0, timeout=2.0):
    s = socket.socket(socket.AF_QIPCRTR, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    node, _port = s.getsockname()
    s.sendto(struct.pack("<5I", QRTR_TYPE_NEW_LOOKUP, service, 0, 0, 0), (node, QRTR_PORT_CTRL))
    out = []
    try:
        while True:
            data, _ = s.recvfrom(64)
            cmd, svc, inst, n, p = struct.unpack_from("<5I", data)
            if cmd != QRTR_TYPE_NEW_SERVER:
                continue
            if svc == 0 and inst == 0 and n == 0 and p == 0:
                break  # end of the list
            out.append((svc, inst & 0xFF, inst >> 8, n, p))
    except socket.timeout:
        pass
    s.close()
    return out


if __name__ == "__main__":
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    for svc, ver, inst, node, port in lookup(want):
        print(f"service {svc:5d} v{ver} inst {inst:3d}  node {node} port {port}  {NAMES.get(svc, '')}")
