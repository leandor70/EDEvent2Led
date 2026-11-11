"""
Connection status after an OpenRGB restart (settings_api.get_openrgb_connection_status).

Scenario: OpenRGB is restarted. Its port answers again, but the app's
connection belongs to the old instance and is dead. A fresh TCP probe says
"reachable"; the status must still report "disconnected", so the frontend
starts the automatic reconnection.

No OpenRGB or hardware needed: fake server from tools/orgb_testkit.py.
Run:  python tools/test_openrgb_status.py
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]

from orgb_testkit import settle  # noqa: E402
from test_openrgb_client import CMD_COUNT, sample_controllers, synthetic_server  # noqa: E402
from utils.openrgb_client import OpenRGBClient  # noqa: E402

import api.keyboard_api as kbd  # noqa: E402
import api.settings_api as sa  # noqa: E402


def check(cond, msg):
    print(f"  [{'OK' if cond else 'FAIL'}] {msg}")
    return bool(cond)


def main() -> int:
    srv = synthetic_server(4, sample_controllers(4))
    ok = True
    saved = (sa._settings, kbd._manager)
    try:
        sa._settings = types.SimpleNamespace(get_openrgb_host=lambda: "127.0.0.1",
                                             get_openrgb_port=lambda: srv.port)
        client = OpenRGBClient("127.0.0.1", srv.port)
        kbd._manager = types.SimpleNamespace(client=client, devices=[1, 2, 3])
        settle(0.1)
        srv.take()

        sa.invalidate_ping_cache()
        st = sa.get_openrgb_connection_status()
        sent = [p["cmd"] for p in srv.take()]
        ok &= check(st["connected"] and st["device_count"] == 3, f"healthy connection reported connected: {st}")
        ok &= check(sent == [CMD_COUNT], "probe is a request on the app's connection (no new TCP connection)")

        st = sa.get_openrgb_connection_status()
        settle(0.05)
        ok &= check(st["connected"] and srv.take() == [], "within the cache TTL: no I/O")

        # OpenRGB restarted: the port still answers, our connection is dead
        srv.drop_clients()
        settle(0.1)
        ok &= check(sa._ping_openrgb("127.0.0.1", srv.port),
                    "a fresh TCP probe still says reachable (the old check was fooled here)")
        sa.invalidate_ping_cache()
        st = sa.get_openrgb_connection_status()
        ok &= check(not st["connected"], f"dead connection reported disconnected: {st}")
        ok &= check(not client.connected, "client knows it is disconnected")

        # Once the client knows, the status says so at once, even inside the TTL
        sa._ping_cache_result, sa._ping_cache_time = True, 10 ** 12
        st = sa.get_openrgb_connection_status()
        ok &= check(not st["connected"], "known-dead client reported without waiting for the cache")

        # No manager: unchanged path
        kbd._manager = None
        st = sa.get_openrgb_connection_status()
        ok &= check(not st["connected"], "no manager -> disconnected")
    finally:
        sa._settings, kbd._manager = saved
        sa.invalidate_ping_cache()
        srv.close()

    print()
    print("  [OK] TUTTI I CONTROLLI PASSATI" if ok else "  [FAIL] ALCUNI CONTROLLI FALLITI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
