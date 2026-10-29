#!/usr/bin/env python3
"""Read the Thor's accelerometer and gyroscope straight from the ADSP sensor
hub (Qualcomm SSC, QMI service 400 over QRTR) for a few seconds and print
what arrives. A test tool: no uinput, no daemon.

  thor-imu-probe.py [seconds] [rate_hz]

Protocol (sns_client / sns_suid / sns_std_sensor protobufs, hand-encoded):
the same messages pb-os's pbos-motiond sends, written here from scratch.
  1. name-service lookup -> node/port of service 400
  2. SUID lookup ("accel", "gyro"), default sensor only
  3. std sensor config (sample rate) -> indications with x, y, z
Needs the sensors process served by hexagonrpcd (thor-sensors run).
"""
import os
import select
import socket
import struct
import sys
import time

SNS_SERVICE = 400
QMI_REQ, QMI_RESP, QMI_IND = 0, 2, 4
SNS_CLIENT_REQ, SNS_CLIENT_REPORT, SNS_CLIENT_JUMBO = 0x20, 0x21, 0x22
MSG_SUID_REQ, MSG_SUID_EVENT = 512, 768
MSG_STD_CONFIG, MSG_STD_EVENT = 513, 1025
MSG_DISABLE = 10
SUID_LOOKUP = 0xABABABABABABABAB
QRTR_PORT_CTRL = 0xFFFFFFFE
QRTR_NEW_SERVER, QRTR_NEW_LOOKUP = 4, 10


# ---- protobuf, just enough ----------------------------------------------
def varint(v):
    out = bytearray()
    while v >= 0x80:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v)
    return bytes(out)


def pb_u(field, v): return varint(field << 3) + varint(v)
def pb_f32(field, v): return varint(field << 3 | 5) + struct.pack("<f", v)
def pb_x32(field, v): return varint(field << 3 | 5) + struct.pack("<I", v)
def pb_x64(field, v): return varint(field << 3 | 1) + struct.pack("<Q", v)
def pb_bytes(field, b): return varint(field << 3 | 2) + varint(len(b)) + b


def pb_fields(buf):
    i = 0
    while i < len(buf):
        k, i = _rv(buf, i)
        f, w = k >> 3, k & 7
        if w == 0:
            v, i = _rv(buf, i)
        elif w == 1:
            v = struct.unpack_from("<Q", buf, i)[0]; i += 8
        elif w == 5:
            v = struct.unpack_from("<I", buf, i)[0]; i += 4
        elif w == 2:
            n, i = _rv(buf, i); v = buf[i:i + n]; i += n
        else:
            return
        yield f, w, v


def _rv(buf, i):
    v = s = 0
    while True:
        c = buf[i]; i += 1
        v |= (c & 0x7F) << s
        if not c & 0x80:
            return v, i
        s += 7


def suid_pb(low, high): return pb_x64(1, low) + pb_x64(2, high)


def client_request(suid, msg_id, payload=b""):
    susp = pb_u(1, 1) + pb_u(2, 1)          # processor APSS, delivery no-wakeup
    req = pb_bytes(2, payload) if payload else b""
    return pb_bytes(1, suid_pb(*suid)) + pb_x32(2, msg_id) + pb_bytes(3, susp) + pb_bytes(4, req)


def events(report):
    """(msg_id, payload) for each event in an sns_client_event_msg."""
    for f, w, v in pb_fields(report):
        if f == 2 and w == 2:
            mid, pay = 0, b""
            for ef, ew, ev in pb_fields(v):
                if ef == 1 and ew == 5: mid = ev
                if ef == 3 and ew == 2: pay = ev
            yield mid, pay


# ---- QRTR / QMI -----------------------------------------------------------
def find_service(timeout=5.0):
    s = socket.socket(socket.AF_QIPCRTR, socket.SOCK_DGRAM)
    node, _ = s.getsockname()
    s.sendto(struct.pack("<5I", QRTR_NEW_LOOKUP, SNS_SERVICE, 0, 0, 0), (node, QRTR_PORT_CTRL))
    s.settimeout(timeout)
    try:
        while True:
            d, _ = s.recvfrom(64)
            cmd, svc, inst, n, p = struct.unpack_from("<5I", d)
            if cmd == QRTR_NEW_SERVER and svc == SNS_SERVICE and (n or p):
                return n, p
            if cmd == QRTR_NEW_SERVER and not (svc or inst or n or p):
                pass  # end of the current list; keep waiting for it to appear
    except socket.timeout:
        return None
    finally:
        s.close()


class Client:
    def __init__(self, svc):
        self.svc, self.txn = svc, 0
        self.s = socket.socket(socket.AF_QIPCRTR, socket.SOCK_DGRAM)
        self.sensor = None

    def send(self, pb):
        self.txn = (self.txn + 1) & 0xFFFF
        tlv = b"\x01" + struct.pack("<HH", len(pb) + 2, len(pb)) + pb
        self.s.sendto(struct.pack("<BHHH", QMI_REQ, self.txn, SNS_CLIENT_REQ, len(tlv)) + tlv, self.svc)

    def recv(self):
        d, _ = self.s.recvfrom(65536)
        if len(d) < 7:
            return None
        typ, _txn, mid, ln = struct.unpack_from("<BHHH", d)
        tl, i = {}, 7
        while i + 3 <= 7 + ln:
            t, n = d[i], struct.unpack_from("<H", d, i + 1)[0]
            tl[t] = d[i + 3:i + 3 + n]; i += 3 + n
        if typ == QMI_RESP and mid == SNS_CLIENT_REQ:
            r = tl.get(2, b"\0\0\0\0")
            res, err = struct.unpack_from("<HH", r)
            return ("resp", res, err)
        if typ == QMI_IND and mid in (SNS_CLIENT_REPORT, SNS_CLIENT_JUMBO) and 2 in tl:
            n = struct.unpack_from("<H", tl[2])[0]
            return ("report", tl[2][2:2 + n])
        return ("other", typ, mid)

    def start(self, data_type, rate, timeout=5.0):
        q = pb_bytes(1, data_type.encode()) + pb_u(2, 1) + pb_u(3, 1)
        self.send(client_request((SUID_LOOKUP, SUID_LOOKUP), MSG_SUID_REQ, q))
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if not select.select([self.s], [], [], 0.5)[0]:
                continue
            m = self.recv()
            if not m:
                continue
            if m[0] == "resp" and m[1] != 0:
                raise RuntimeError(f"{data_type}: hub refused the lookup (error {m[2]})")
            if m[0] != "report":
                continue
            for mid, pay in events(m[1]):
                if mid != MSG_SUID_EVENT:
                    continue
                typ, first = b"", None
                for f, w, v in pb_fields(pay):
                    if f == 1 and w == 2: typ = v
                    if f == 2 and w == 2 and first is None:
                        lo = hi = 0
                        for sf, sw, sv in pb_fields(v):
                            if sf == 1: lo = sv
                            if sf == 2: hi = sv
                        first = (lo, hi)
                if typ == data_type.encode() and first:
                    self.sensor = first
                    self.send(client_request(first, MSG_STD_CONFIG, pb_f32(1, float(rate))))
                    return first
        raise RuntimeError(f"no {data_type} sensor answered in {timeout:.0f} s")

    def stop(self):
        if self.sensor:
            self.send(client_request(self.sensor, MSG_DISABLE))
        self.s.close()


def samples(report):
    for mid, pay in events(report):
        if mid != MSG_STD_EVENT:
            continue
        v = []
        for f, w, val in pb_fields(pay):
            if f == 1 and w == 5:
                v.append(struct.unpack("<f", struct.pack("<I", val))[0])
            elif f == 1 and w == 2:
                v += list(struct.unpack(f"<{len(val) // 4}f", val[:len(val) // 4 * 4]))
        if len(v) >= 3:
            yield v[:3]


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 5
    rate = float(sys.argv[2]) if len(sys.argv) > 2 else 100
    svc = find_service()
    if not svc:
        print("PROBE FAIL: sensor hub service 400 not found")
        return 1
    print(f"service 400 at node {svc[0]} port {svc[1]}")
    clients = {}
    for t in ("accel", "gyro"):
        c = Client(svc)
        suid = c.start(t, rate)
        print(f"{t}: sensor {suid[1]:016x}{suid[0]:016x} at {rate:.0f} Hz")
        clients[t] = c
    stats = {t: [0, None] for t in clients}
    end = time.monotonic() + secs
    try:
        while time.monotonic() < end:
            r, _, _ = select.select([c.s for c in clients.values()], [], [], 0.5)
            for t, c in clients.items():
                if c.s in r:
                    m = c.recv()
                    if m and m[0] == "report":
                        for v in samples(m[1]):
                            stats[t][0] += 1; stats[t][1] = v
    finally:
        for c in clients.values():
            c.stop()
    ok = True
    for t, (n, last) in stats.items():
        hz = n / secs
        print(f"{t}: {n} samples, {hz:.0f} Hz, last {['%.3f' % x for x in last] if last else None}")
        ok &= n > 0
    print("PROBE OK" if ok else "PROBE FAIL: a sensor sent nothing")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
