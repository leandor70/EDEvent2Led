"""
Tests for src/utils/openrgb_diagnostics.py and the quiet connect watcher in
src/api/settings_api.py. No OpenRGB and no hardware needed: fake TCP servers
on local ports, and a fake process table for the Windows part.

Run:  python tools/test_openrgb_diagnostics.py
"""
import socket
import struct
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import utils.openrgb_diagnostics as diag  # noqa: E402

_results = []


def check(name, cond, detail=""):
    _results.append(bool(cond))
    print(f"  {'[OK]  ' if cond else '[FAIL]'} {name}" + (f"  ({detail})" if detail and not cond else ""))


# ── Fake servers ──────────────────────────────────────────────────────────────

class FakeServer:
    """Listens on 127.0.0.1:<free port>; `mode` decides how it answers."""

    def __init__(self, mode):
        self.mode = mode
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.received = []
        self._stop = False
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                conn.settimeout(3)
                try:
                    data = conn.recv(16)
                    self.received.append(data)
                    if self.mode == "openrgb":
                        conn.sendall(struct.pack("<4sIII", b"ORGB", 0, 0, 4) + struct.pack("<I", 3))
                    elif self.mode == "http":
                        conn.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                    elif self.mode == "hangup":
                        pass                       # close at once
                    elif self.mode == "silent":
                        time.sleep(2.5)            # longer than the reply timeout
                except OSError:
                    pass

    def close(self):
        self._stop = True
        self.sock.close()


def free_closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ── Fake Windows process table ────────────────────────────────────────────────

def fake_windows(processes, listeners, services):
    """Replace the ctypes scans with fixed data."""
    diag._processes = lambda: dict(processes)
    diag._listeners = lambda: list(listeners)
    diag._services_by_pid = lambda: dict(services)
    diag._process_path = lambda pid: f"C:\\Fake\\{processes.get(pid, 'x')}"


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_protocol_probe():
    print("\n[1] Protocol probe against fake servers")
    srv = FakeServer("openrgb")
    r = diag.probe_protocol("127.0.0.1", srv.port)
    check("OpenRGB reply -> openrgb, 3 devices", r["state"] == "openrgb" and r["device_count"] == 3, r)
    time.sleep(0.1)
    sent = srv.received[0] if srv.received else b""
    check("request is REQUEST_CONTROLLER_COUNT (read-only)",
          sent == struct.pack("<4sIII", b"ORGB", 0, 0, 0), sent)
    srv.close()

    for mode, expected in (("http", "other"), ("hangup", "other"), ("silent", "no_reply")):
        srv = FakeServer(mode)
        r = diag.probe_protocol("127.0.0.1", srv.port)
        check(f"{mode} server -> {expected}", r["state"] == expected, r)
        srv.close()

    t = time.perf_counter()
    r = diag.probe_protocol("localhost", free_closed_port())
    ms = (time.perf_counter() - t) * 1000
    check("closed port -> closed", r["state"] == "closed", r)
    check("closed local port answers fast (< 1500 ms)", ms < 1500, f"{ms:.0f} ms")


def test_classification():
    print("\n[2] Classification with a fake process table")
    real = (diag._processes, diag._listeners, diag._services_by_pid, diag._process_path)
    try:
        # connected, OpenRGB owned by a service, plus a second OpenRGB (Thing Fish's case)
        srv = FakeServer("openrgb")
        fake_windows({100: "OpenRGB.exe", 200: "OpenRGB.exe", 300: "node.exe"},
                     [{"port": srv.port, "pid": 100}],
                     {100: "OpenRGB Service"})
        d = diag.diagnose("127.0.0.1", srv.port)
        check("connected", d["code"] == "connected" and d["device_count"] == 3, d["code"])
        check("owner is the service instance",
              d["owner"] and d["owner"]["pid"] == 100 and d["owner"]["service"] == "OpenRGB Service", d["owner"])
        check("multiple_instances warning", d["warnings"] == ["multiple_instances"], d["warnings"])
        line = diag.summary_line(d)
        check("summary mentions service + warning",
              "service 'OpenRGB Service'" in line and "2 OpenRGB processes" in line, line)
        srv.close()

        closed = free_closed_port()
        fake_windows({100: "OpenRGB.exe"}, [], {})
        d = diag.diagnose("127.0.0.1", closed)
        check("OpenRGB running, nothing listening -> openrgb_no_sdk", d["code"] == "openrgb_no_sdk", d["code"])

        fake_windows({100: "OpenRGB.exe"}, [{"port": 6743, "pid": 100}], {})
        d = diag.diagnose("127.0.0.1", closed)
        check("OpenRGB on another port -> openrgb_other_port [6743]",
              d["code"] == "openrgb_other_port" and d["other_ports"] == [6743], (d["code"], d["other_ports"]))

        fake_windows({300: "node.exe"}, [], {})
        d = diag.diagnose("127.0.0.1", closed)
        check("no OpenRGB -> not_running", d["code"] == "not_running", d["code"])
        check("single/no instance -> no warning", d["warnings"] == [], d["warnings"])

        srv = FakeServer("http")
        fake_windows({300: "node.exe"}, [{"port": srv.port, "pid": 300}], {})
        d = diag.diagnose("127.0.0.1", srv.port)
        check("other program on port -> port_busy_other, owner node.exe",
              d["code"] == "port_busy_other" and d["owner"]["name"] == "node.exe", (d["code"], d["owner"]))
        srv.close()

        # remote host: no process scan at all
        calls = []
        diag._processes = lambda: calls.append(1) or {}
        real_local = diag.is_local_host
        diag.is_local_host = lambda h: False
        try:
            d = diag.diagnose("127.0.0.1", closed)
        finally:
            diag.is_local_host = real_local
        check("remote host -> remote_unreachable, no process scan",
              d["code"] == "remote_unreachable" and not calls and d["local"] is False, (d["code"], calls))
    finally:
        diag._processes, diag._listeners, diag._services_by_pid, diag._process_path = real


def test_summary_ascii():
    print("\n[3] Console/log lines are ASCII (Windows cp1252 console)")
    codes = ["connected", "openrgb_no_sdk", "openrgb_other_port", "not_running",
             "port_busy_other", "no_reply", "remote_unreachable"]
    ok = True
    for c in codes:
        d = {"code": c, "host": "localhost", "port": 6742, "device_count": 2,
             "owner": {"pid": 1, "name": "x.exe", "service": ""}, "other_ports": [6743],
             "warnings": ["multiple_instances"],
             "openrgb_processes": [{"pid": 1}, {"pid": 2}]}
        try:
            diag.summary_line(d).encode("ascii")
        except UnicodeEncodeError:
            ok = False
    check("summary_line is ASCII for every code", ok)


def test_real_scan_does_not_crash():
    print("\n[4] Real Windows scan (whatever runs on this PC)")
    if sys.platform != "win32":
        check("skipped (not Windows)", True)
        return
    d = diag.diagnose("localhost", free_closed_port())
    check("diagnose() returns a code", d["code"] in (
        "openrgb_no_sdk", "openrgb_other_port", "not_running"), d["code"])
    print(f"        this PC: {diag.summary_line(d)}")


def test_watcher():
    print("\n[5] Quiet connect watcher (settings_api)")
    import api.settings_api as sa
    import api.keyboard_api as kbd

    class FakeSettings:
        def get_openrgb_host(self): return "127.0.0.1"
        def get_openrgb_port(self): return 6742

    connected = []
    sa._settings = FakeSettings()
    kbd._manager = None
    sa._reconnect_in_progress = False

    import utils.openrgb_client as oc
    real = (sa._ping_openrgb, sa._initialize_hardware, oc.OpenRGBClient, sa._current_diagnosis)
    try:
        oc.OpenRGBClient = lambda h, p: "client"
        sa._initialize_hardware = lambda c: (connected.append(c), setattr(kbd, "_manager", "manager"))
        sa._current_diagnosis = lambda force=False: {"code": "connected", "host": "127.0.0.1",
                                                     "port": 6742, "device_count": 1, "warnings": []}

        sa._ping_openrgb = lambda h, p: False
        check("OpenRGB down -> no connect, no error", sa._quiet_connect_once() is False and not connected)

        sa._reconnect_in_progress = True
        sa._ping_openrgb = lambda h, p: True
        check("Tier 2 running -> watcher stays out", sa._quiet_connect_once() is False and not connected)
        sa._reconnect_in_progress = False

        check("OpenRGB up -> connects", sa._quiet_connect_once() is True and connected == ["client"], connected)
        check("in-progress flag released", sa._reconnect_in_progress is False)
        check("already connected -> nothing to do", sa._quiet_connect_once() is True and len(connected) == 1)
    finally:
        sa._ping_openrgb, sa._initialize_hardware, oc.OpenRGBClient, sa._current_diagnosis = real
        kbd._manager = None


def main():
    print("=" * 70)
    print("  OpenRGB diagnostics tests")
    print("=" * 70)
    test_protocol_probe()
    test_classification()
    test_summary_ascii()
    test_real_scan_does_not_crash()
    test_watcher()
    passed = sum(_results)
    print(f"\n  Results: {passed}/{len(_results)} checks passed")
    print("  [OK] ALL TESTS PASSED" if passed == len(_results) else "  [FAIL] SOME TESTS FAILED")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
