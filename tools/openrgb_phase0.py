"""
Phase 0 of the OpenRGB client migration: record how openrgb-python behaves today.

    python tools/openrgb_phase0.py capture [--host 127.0.0.1] [--port 6742]
        Connects openrgb-python to the real OpenRGB server THROUGH a recording
        proxy, reads the device list and disconnects. Read-only: no LED is
        changed. Saves:
          tools/fixtures/openrgb/session_reads.json  every packet of the session
          tools/fixtures/openrgb/model_lib.json      the device model as the app sees it

    python tools/openrgb_phase0.py golden
        Starts a fake server that replays session_reads.json, drives
        openrgb-python through every write the app uses, and saves the exact
        packets it sends:
          tools/fixtures/openrgb/golden_writes.json
        No hardware is touched.

The new built-in client must produce the same model and the same packets.
NOTE: the fixtures describe the local hardware (names, serials): keep them out
of a public repository.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orgb_testkit import RecordingProxy, ReplayServer, load_json, save_json, settle  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "openrgb"


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return v


def _rgb(c):
    return [int(c.red), int(c.green), int(c.blue)]


def dump_model(client) -> dict:
    """Device model through the attribute names the app uses (openrgb-python API)."""
    devices = []
    for d in client.devices:
        md = d.metadata
        devices.append({
            "id": d.id,
            "name": d.name,
            "type": _int(d.type),
            "metadata": {k: getattr(md, k, None) for k in ("vendor", "description", "version", "serial", "location")},
            "active_mode": d.active_mode,
            "modes": [{
                "id": m.id, "name": m.name, "value": m.value, "flags": _int(m.flags),
                "speed_min": m.speed_min, "speed_max": m.speed_max,
                "brightness_min": m.brightness_min, "brightness_max": m.brightness_max,
                "colors_min": m.colors_min, "colors_max": m.colors_max,
                "speed": m.speed, "brightness": m.brightness,
                "direction": _int(m.direction), "color_mode": _int(m.color_mode),
                "colors": [_rgb(c) for c in (m.colors or [])],
            } for m in d.modes],
            "zones": [{
                "id": z.id, "name": z.name, "type": _int(z.type),
                "leds": [led.id for led in z.leds],
                "mat_height": getattr(z, "mat_height", None), "mat_width": getattr(z, "mat_width", None),
                "matrix_map": getattr(z, "matrix_map", None),
                "segments": [{"name": s.name, "type": _int(s.type), "start_idx": s.start_idx,
                              "leds_count": s.leds_count} for s in (z.segments or [])],
            } for z in d.zones],
            "leds": [{"id": led.id, "name": led.name} for led in d.leds],
            "colors": [_rgb(c) for c in d.colors],
        })
    return {"protocol_version": client.protocol_version, "devices": devices}


def capture(host: str, port: int) -> int:
    from openrgb import OpenRGBClient

    proxy = RecordingProxy((host, port))
    client = OpenRGBClient("127.0.0.1", proxy.port, name="ED:Event2Led phase0")
    model = dump_model(client)
    client.disconnect()
    settle(0.5)
    proxy.close()

    save_json(FIXTURES / "session_reads.json", proxy.log)
    save_json(FIXTURES / "model_lib.json", model)
    names = sorted({e["name"] for e in proxy.log})
    print(f"[OK] {len(proxy.log)} packets recorded ({', '.join(names)})")
    print(f"[OK] model: protocol {model['protocol_version']}, {len(model['devices'])} devices")
    for d in model["devices"]:
        print(f"     [{d['id']}] {d['name']}  type={d['type']} leds={len(d['leds'])} zones={len(d['zones'])} modes={len(d['modes'])}")
    return 0


def _pick(devices, pred, label):
    for d in devices:
        if pred(d):
            return d
    raise SystemExit(f"[FAIL] no device for {label}")


def write_ops(client):
    """(label, callable) for every write call the app makes, on representative devices."""
    from openrgb.utils import RGBColor, DeviceType

    devs = client.devices
    kbd = _pick(devs, lambda d: d.type == DeviceType.KEYBOARD and len(d.leds) > 1, "keyboard")
    strip = _pick(devs, lambda d: d.type == DeviceType.LEDSTRIP and len(d.leds) > 1, "led strip")
    multi = _pick(devs, lambda d: len(d.zones) > 2, "multi-zone device")
    zi = next(i for i, z in enumerate(multi.zones) if len(z.leds) > 0)
    li = min(3, len(multi.leds) - 1)

    def ramp(n, k=1):
        return [RGBColor((i * 7 * k) % 256, (i * 13 + 5) % 256, (255 - i * 3) % 256) for i in range(n)]

    def direct_name(d):
        return next(m.name for m in d.modes if m.name.lower() == "direct")

    ops = [
        ("strip.set_colors(fast)", lambda: strip.set_colors(ramp(len(strip.leds)), fast=True)),
        ("kbd.set_colors(fast)", lambda: kbd.set_colors(ramp(len(kbd.leds), 2), fast=True)),
        ("multi.zone.set_colors(fast)", lambda: multi.zones[zi].set_colors(ramp(len(multi.zones[zi].leds), 3), fast=True)),
        ("multi.led.set_color(fast)", lambda: multi.leds[li].set_color(RGBColor(10, 20, 30), fast=True)),
        ("strip.set_color(device)", lambda: strip.set_color(RGBColor(255, 128, 0))),
        ("kbd.set_color(device)", lambda: kbd.set_color(RGBColor(1, 2, 3))),
        ("kbd.set_mode(name Direct)", lambda: kbd.set_mode(direct_name(kbd))),
        ("kbd.set_mode(int 0)", lambda: kbd.set_mode(0)),
        ("kbd.set_mode(Mode obj modes[0])", lambda: kbd.set_mode(kbd.modes[0])),
        ("strip.set_custom_mode()", lambda: strip.set_custom_mode()),
        ("strip.show()", lambda: strip.show()),
        ("strip.update()", lambda: strip.update()),
        ("kbd.update()", lambda: kbd.update()),
    ]
    return ops, {"keyboard": kbd.id, "strip": strip.id, "multi": multi.id, "multi_zone": zi, "multi_led": li}


def golden() -> int:
    from openrgb import OpenRGBClient

    recorded = load_json(FIXTURES / "session_reads.json")
    server = ReplayServer(recorded)
    client = OpenRGBClient("127.0.0.1", server.port, name="ED:Event2Led phase0")
    settle()
    connect_packets = server.take()
    ops, picked = write_ops(client)

    results = []
    for label, fn in ops:
        fn()
        settle()
        sent = server.take()
        results.append({"op": label, "packets": sent})
        print(f"[OK] {label:34} -> {', '.join(p['name'] for p in sent) or '(nothing sent)'}")
    client.disconnect()
    server.close()

    if server.unknown:
        print(f"[WARN] {len(server.unknown)} request(s) not in the recording:",
              sorted({u['name'] for u in server.unknown}))
    save_json(FIXTURES / "golden_writes.json",
              {"devices": picked, "connect": connect_packets, "ops": results})
    print(f"[OK] saved {FIXTURES / 'golden_writes.json'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["capture", "golden"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=6742)
    a = ap.parse_args()
    return capture(a.host, a.port) if a.step == "capture" else golden()


if __name__ == "__main__":
    sys.exit(main())
