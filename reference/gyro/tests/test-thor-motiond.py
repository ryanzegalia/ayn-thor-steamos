#!/usr/bin/env python3
"""Tests for thor-motiond's on-when-wanted streams (the pure parts: when the motion
is wanted, the debounce, starting and stopping the streams, the optional slow idle,
and the rate-aware zero and drift).
No sensor hub needed: the QMI clients are faked.

    python3 tests/test-thor-motiond.py -v
"""
import asyncio
import importlib.machinery
import importlib.util
import os
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "thor-motiond")


def load(env_idle=None):
    if env_idle is None:
        os.environ.pop("THOR_MOTION_IDLE_HZ", None)
    else:
        os.environ["THOR_MOTION_IDLE_HZ"] = env_idle
    loader = importlib.machinery.SourceFileLoader("thor_motiond", SRC)
    spec = importlib.util.spec_from_loader("thor_motiond", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


md = load()


class FakeClient:
    def __init__(self):
        self.s = None


def motion(mod=md, tmp=None):
    asyncio.set_event_loop(asyncio.new_event_loop())
    mod.ZERO_FILE = os.path.join(tmp or tempfile.mkdtemp(), "gyro-zero")
    mod.MODE_FILE = os.path.join(tmp or tempfile.mkdtemp(), "mode")
    mod.SWITCH_PRO_HID = os.path.join(tempfile.mkdtemp(), "*:057E:2009.*")
    m = mod.Motion()
    m.dsu = mod.DsuServer(m.poke)
    return m


class Rates(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual((md.RATE, md.IDLE_RATE), (200, 0))         # off when not wanted

    def test_env_picks_the_idle_behaviour(self):
        for v in ("200", "500", "-1"):
            self.assertEqual(load(v).IDLE_RATE, 200)                # always on, the old behaviour
        self.assertEqual(load("25").IDLE_RATE, 25)                  # slow stream
        self.assertEqual(load("0").IDLE_RATE, 0)
        load()

    def test_full_rate_right_after_start_then_idle(self):
        m = motion()
        now = time.monotonic()
        self.assertEqual(m.target_rate(now), 200)                   # inside IDLE_AFTER_S of start
        self.assertEqual(m.target_rate(now + md.IDLE_AFTER_S + 1), 0)

    def test_dsu_client_means_full_rate(self):
        m = motion()
        m.wanted_at = time.monotonic() - 60
        self.assertEqual(m.target_rate(), 0)
        m.dsu.clients[("127.0.0.1", 5000)] = time.monotonic()
        self.assertEqual(m.target_rate(), 200)
        self.assertEqual(m.why, "dsu")

    def test_expired_dsu_client_then_debounce(self):
        m = motion()
        now = time.monotonic()
        m.dsu.clients[("127.0.0.1", 5000)] = now - 6                # gone quiet 6 s ago
        m.wanted_at = now - 1                                       # it was wanted 1 s ago
        self.assertEqual(m.target_rate(now), 200)                   # still inside the debounce
        self.assertEqual(m.target_rate(now + md.IDLE_AFTER_S), 0)

    def test_switch_pro_identity_means_full_rate(self):
        m = motion()
        m.wanted_at = time.monotonic() - 60
        d = tempfile.mkdtemp()
        md.SWITCH_PRO_HID = os.path.join(d, "*:057E:2009.*")
        self.assertEqual(m.target_rate(), 0)
        open(os.path.join(d, "0003:057E:2009.0007"), "w").close()
        self.assertEqual(m.target_rate(), 200)
        self.assertEqual(m.why, "switch-pro")

    def test_dump_is_always_full_rate(self):
        m = motion()
        m.dump, m.wanted_at = True, time.monotonic() - 60
        self.assertEqual(m.target_rate(), 200)


class Switching(unittest.TestCase):
    def setUp(self):
        self.m = motion()
        self.calls = []
        self.m.stop = lambda: (self.calls.append("stop"), self.m.clients.clear())
        def start():
            self.m.rate = self.m.target_rate()
            self.m.clients = {"accel": FakeClient(), "gyro": FakeClient()} if self.m.rate else {}
            self.calls.append(("start", self.m.rate))
            return True
        self.m.start = start
        self.m.clients = {"accel": FakeClient(), "gyro": FakeClient()}

    def test_no_restart_when_rate_unchanged(self):
        self.m.rate = 200
        self.m.check_rate()                                         # just started: still wanted
        self.assertEqual(self.calls, [])

    def test_stops_then_starts_on_a_client(self):
        self.m.rate, self.m.wanted_at = 200, time.monotonic() - 60
        self.m.check_rate()
        self.assertEqual(self.calls, ["stop", ("start", 0)])
        self.assertEqual(self.m.clients, {})                        # streams really off
        self.m.dsu.datagram_received(b"DSUC" + bytes(12) + (0x100002).to_bytes(4, "little"), ("127.0.0.1", 5000))
        self.m.loop.run_until_complete(asyncio.sleep(0))            # the poke runs on the loop
        self.assertEqual(self.calls[-2:], ["stop", ("start", 200)])

    def test_asleep_never_restarts(self):
        self.m.rate, self.m.wanted_at = 200, time.monotonic() - 60
        self.m.asleep = True
        self.m.check_rate()
        self.assertEqual(self.calls, [])

    def test_a_dead_stream_is_left_to_health(self):
        self.m.rate, self.m.clients = 200, {}                       # still wanted, stream died
        self.m.check_rate()
        self.assertEqual(self.calls, [])

    def test_off_and_staying_off_does_nothing(self):
        self.m.rate, self.m.clients, self.m.wanted_at = 0, {}, time.monotonic() - 60
        self.m.check_rate()
        self.assertEqual(self.calls, [])

    def test_real_start_while_unwanted_opens_no_stream(self):
        m = motion()
        m.wanted_at = time.monotonic() - 60
        self.addCleanup(setattr, md.probe, "find_service", md.probe.find_service)
        md.probe.find_service = lambda timeout=0: self.fail("asked the sensor hub while off")
        self.assertTrue(md.Motion.start(m))
        self.assertEqual((m.rate, m.clients), (0, {}))
        with open(md.MODE_FILE) as f:
            self.assertEqual(f.read().split()[:2], ["0", "off"])


class Dsu(unittest.TestCase):
    def test_new_client_pokes_once(self):
        pokes = []
        s = md.DsuServer(lambda: pokes.append(1))
        req = b"DSUC" + bytes(12) + (0x100002).to_bytes(4, "little")
        s.datagram_received(req, ("127.0.0.1", 5000))
        s.datagram_received(req, ("127.0.0.1", 5000))
        s.datagram_received(req, ("127.0.0.1", 5001))
        self.assertEqual(len(pokes), 2)
        self.assertTrue(s.live())
        self.assertFalse(s.live(time.monotonic() + 6))


class Measured(unittest.TestCase):
    def test_measures_what_the_hub_delivers(self):
        m = motion()
        t0 = m.hz_t
        for i in range(111):                                        # the hub's ~110 Hz floor
            m.measure(t0 + (i + 1) / 110.0)
        self.assertAlmostEqual(m.hz, 110.0, delta=1.5)

    def test_slow_idle_passes_only_idle_rate_to_uinput(self):
        m = motion()
        self.addCleanup(setattr, md, "IDLE_RATE", md.IDLE_RATE)
        md.IDLE_RATE = 25                                          # THOR_MOTION_IDLE_HZ=25
        m.rate, t0 = 25, 1000.0
        sent = sum(m.emit_due(t0 + i / 110.0) for i in range(110))  # one second at 110 Hz
        self.assertEqual(sent, 25)
        m.rate = 200
        self.assertEqual(sum(m.emit_due(t0 + 2 + i / 220.0) for i in range(220)), 220)


class RateAware(unittest.TestCase):
    def still(self, z, n, rate):
        for _ in range(n):
            z.add([0.3, -0.2, 0.1], [0.0, 0.0, 1.0], rate)

    def test_zero_learns_in_half_a_second_at_either_rate(self):
        for rate, n in ((25, 12), (200, 100)):
            z = md.GyroZero(os.path.join(tempfile.mkdtemp(), "zero"))
            self.still(z, n - 1, rate)
            self.assertFalse(z.learned, rate)
            self.still(z, 1, rate)
            self.assertTrue(z.learned, rate)
            self.assertAlmostEqual(z.bias[0], 0.3)

    def test_drift_tracking_time_constant_follows_the_rate(self):
        for rate in (25, 200):
            s = md.Steady()
            s([0.5, 0.0, 0.0], rate)
            self.assertAlmostEqual(s.d[0], 0.5 / (rate * md.DRIFT_TAU_S))


if __name__ == "__main__":
    unittest.main()
