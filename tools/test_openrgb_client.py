"""
Tests for the built-in OpenRGB client (src/utils/openrgb_client.py).

No OpenRGB server and no hardware needed: every test talks to a fake server.

  * Parity with openrgb-python (needs tools/fixtures/openrgb/, made by
    tools/openrgb_phase0.py; skipped when missing): same device model, same
    write packets byte for byte.
  * Synthetic controllers built by an independent encoder: protocol v0/v3/v4,
    unknown device type, matrix holes, segments, mode flag rules.
  * Robustness: truncated data, lost connection, unsolicited packets,
    stale replies, concurrent writers.
  * Semantics: show(), mode-specific colors, ee_devices, errors.
  * Performance guard on color packing.

Run:  python tools/test_openrgb_client.py
"""
from __future__ import annotations

import struct
import sys
import threading
import time
import timeit
import traceback
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "src")]

from orgb_testkit import PacketReader, ReplayServer, ScriptServer, load_json, settle  # noqa: E402
from utils import openrgb_client as oc  # noqa: E402

FIXTURES = ROOT / "tools" / "fixtures" / "openrgb"

CMD_COUNT, CMD_DATA, CMD_VERSION, CMD_NAME, CMD_LIST_UPDATED = 0, 1, 40, 50, 51
CMD_LEDS, CMD_ZONE, CMD_SINGLE, CMD_CUSTOM, CMD_MODE = 1050, 1051, 1052, 1100, 1101

PER_LED, MODE_SPECIFIC, NO_COLORS = 1, 2, 0
F_SPEED, F_DIR_LR, F_BRIGHT, F_PER_LED, F_MODE_COLOR = 1, 2, 16, 32, 64


# ── Independent encoder for controller data ────────────────────────────────────


def s(text: str) -> bytes:
    raw = text.encode() + b"\x00"
    return struct.pack("<H", len(raw)) + raw


def col(*rgb) -> bytes:
    return bytes((rgb[0], rgb[1], rgb[2], 0))


def enc_mode(v, name, value=0, flags=F_PER_LED, speed=(0, 0, 0), bright=(0, 0, 0),
             cmin=0, cmax=0, direction=0, color_mode=PER_LED, colors=()) -> bytes:
    out = s(name) + struct.pack("<iIII", value, flags, speed[0], speed[1])
    if v >= 3:
        out += struct.pack("<II", bright[0], bright[1])
    out += struct.pack("<III", cmin, cmax, speed[2])
    if v >= 3:
        out += struct.pack("<I", bright[2])
    out += struct.pack("<II", direction, color_mode)
    out += struct.pack("<H", len(colors)) + b"".join(col(*c) for c in colors)
    return out


def enc_zone(v, name, ztype, count, matrix=None, segments=()) -> bytes:
    out = s(name) + struct.pack("<iIII", ztype, 0, count, count)
    if matrix:
        h, w = len(matrix), len(matrix[0])
        cells = [0xFFFFFFFF if c is None else c for row in matrix for c in row]
        out += struct.pack("<H", 8 + 4 * h * w) + struct.pack(f"<II{h * w}I", h, w, *cells)
    else:
        out += struct.pack("<H", 0)
    if v >= 4:
        out += struct.pack("<H", len(segments))
        for name_, t, start, n in segments:
            out += s(name_) + struct.pack("<iII", t, start, n)
    return out


def enc_controller(v, dtype, name, modes, active, zones, led_names, colors, vendor="Vendor") -> bytes:
    body = struct.pack("<i", dtype) + s(name)
    if v >= 1:
        body += s(vendor)
    body += s("desc") + s("1.0") + s("SN1") + s("loc")
    body += struct.pack("<Hi", len(modes), active) + b"".join(modes)
    body += struct.pack("<H", len(zones)) + b"".join(zones)
    body += struct.pack("<H", len(led_names))
    for i, ln in enumerate(led_names):
        body += s(ln) + struct.pack("<I", i)
    body += struct.pack("<H", len(colors)) + b"".join(col(*c) for c in colors)
    return struct.pack("<I", len(body) + 4) + body


def sample_controllers(v: int):
    """[keyboard-like (matrix, unknown type), strip (segments, mode-specific active), plain (NONE mode active)]"""
    kbd = enc_controller(
        v, 99, "Kbd",
        [enc_mode(v, "Direct"),
         enc_mode(v, "Wave", 3, F_SPEED | F_DIR_LR | F_BRIGHT | F_MODE_COLOR, (1, 9, 5), (0, 100, 80),
                  1, 2, 1, MODE_SPECIFIC, [(10, 20, 30)])],
        0,
        [enc_zone(v, "Line", 1, 3, segments=[("A", 1, 0, 2), ("B", 1, 2, 1)]),
         enc_zone(v, "Keys", 2, 4, matrix=[[0, None, 1], [2, 3, None]])],
        [f"L{i}" for i in range(7)], [(i, 2 * i, 3 * i) for i in range(7)])
    strip = enc_controller(
        v, 4, "Strip",
        [enc_mode(v, "Direct"),
         enc_mode(v, "Static", 1, F_MODE_COLOR, cmin=1, cmax=2, color_mode=MODE_SPECIFIC,
                  colors=[(1, 1, 1), (2, 2, 2)])],
        1, [enc_zone(v, "Z", 1, 4)], [f"S{i}" for i in range(4)], [(0, 0, 0)] * 4)
    plain = enc_controller(v, 0, "Plain", [enc_mode(v, "Rainbow", 0, 0, color_mode=NO_COLORS)], 0,
                           [enc_zone(v, "Z", 0, 2)], ["a", "b"], [(5, 5, 5)] * 2)
    return [kbd, strip, plain]


def synthetic_server(v, controllers, answer_version=True, extra=None):
    def handler(dev, cmd, payload):
        if extra:
            r = extra(dev, cmd, payload)
            if r is not None:
                return r
        if cmd == CMD_VERSION:
            return [(0, CMD_VERSION, struct.pack("<I", v))] if answer_version else []
        if cmd == CMD_COUNT:
            return [(0, CMD_COUNT, struct.pack("<I", len(controllers)))]
        if cmd == CMD_DATA:
            return [(dev, CMD_DATA, controllers[dev])]
        return []
    return ScriptServer(handler)


def connect(srv, **kw) -> oc.OpenRGBClient:
    c = oc.OpenRGBClient("127.0.0.1", srv.port, **kw)
    settle(0.1)
    srv.take()
    return c


def leds_payload(colors) -> bytes:
    body = struct.pack("<H", len(colors)) + b"".join(col(*c) for c in colors)
    return struct.pack("<I", len(body) + 4) + body


# ── Tests ──────────────────────────────────────────────────────────────────────

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


class Skip(Exception):
    pass


def need_fixtures():
    if not (FIXTURES / "model_lib.json").exists():
        raise Skip("fixtures missing (run tools/openrgb_phase0.py capture + golden)")


@test
def parity_model_with_openrgb_python():
    need_fixtures()
    from openrgb_phase0 import dump_model
    srv = ReplayServer(load_json(FIXTURES / "session_reads.json"))
    try:
        c = connect(srv)
        assert dump_model(c) == load_json(FIXTURES / "model_lib.json"), "device model differs"
        c.disconnect()
    finally:
        srv.close()


@test
def parity_write_packets_with_openrgb_python():
    need_fixtures()
    import openrgb_phase0 as p0
    golden = load_json(FIXTURES / "golden_writes.json")
    srv = ReplayServer(load_json(FIXTURES / "session_reads.json"))
    saved = sys.modules.get("openrgb.utils")
    sys.modules["openrgb.utils"] = types.SimpleNamespace(RGBColor=oc.RGBColor, DeviceType=oc.DeviceType)
    try:
        c = connect(srv)
        ops, picked = p0.write_ops(c)
        assert picked == golden["devices"], f"devices picked {picked} != {golden['devices']}"
        for (label, fn), g in zip(ops, golden["ops"]):
            fn()
            settle(0.15)
            got = srv.take()
            writes = [(p["dev"], p["cmd"], p["payload"]) for p in got if p["cmd"] != CMD_DATA]
            ref = [(p["dev"], p["cmd"], p["payload"]) for p in g["packets"] if p["cmd"] != CMD_DATA]
            assert writes == ref, f"{label}: write packets differ"
            reads = sum(p["cmd"] == CMD_DATA for p in got)
            ref_reads = sum(p["cmd"] == CMD_DATA for p in g["packets"])
            expected = 0 if "set_color(device)" in label else ref_reads   # re-read removed on purpose
            assert reads == expected, f"{label}: {reads} re-reads, expected {expected}"
        assert not srv.unknown, f"requests not in the recording: {srv.unknown}"
        c.disconnect()
    finally:
        if saved is not None:
            sys.modules["openrgb.utils"] = saved
        else:
            sys.modules.pop("openrgb.utils", None)
        srv.close()


@test
def connect_sequence_without_plugins_or_profiles():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = oc.OpenRGBClient("127.0.0.1", srv.port)
        settle(0.1)
        got = srv.take()
        cmds = [p["cmd"] for p in got]
        assert cmds == [CMD_VERSION, CMD_NAME, CMD_COUNT, CMD_DATA, CMD_DATA, CMD_DATA], cmds
        assert bytes.fromhex(got[1]["payload"]) == b"ED:Event2Led\x00"
        assert bytes.fromhex(got[0]["payload"]) == struct.pack("<I", 4)
        assert all(bytes.fromhex(p["payload"]) == struct.pack("<I", 4) for p in got[3:]), "data request must carry the version"
        assert c.protocol_version == 4 and len(c.devices) == 3
        c.disconnect()
    finally:
        srv.close()


@test
def parse_v4_matrix_segments_unknown_type_and_mode_flags():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        kbd, strip, plain = c.devices
        assert kbd.type == oc.DeviceType.UNKNOWN, kbd.type
        assert (kbd.name, kbd.metadata.vendor, kbd.metadata.serial) == ("Kbd", "Vendor", "SN1")
        line, keys = kbd.zones
        assert line.type == oc.ZoneType.LINEAR and keys.type == oc.ZoneType.MATRIX
        assert [l.id for l in line.leds] == [0, 1, 2] and [l.id for l in keys.leds] == [3, 4, 5, 6]
        assert (line.start_idx, keys.start_idx) == (0, 3)
        assert keys.matrix_map == [[0, None, 1], [2, 3, None]] and (keys.mat_height, keys.mat_width) == (2, 3)
        assert line.matrix_map is None and line.mat_height is None
        assert [(g.name, g.start_idx, g.leds_count) for g in line.segments] == [("A", 0, 2), ("B", 2, 1)]
        assert kbd.colors[6] == (6, 12, 18) and kbd.colors[6].red == 6
        assert keys.colors == kbd.colors[3:7]
        direct, wave = kbd.modes
        assert (direct.speed, direct.speed_min, direct.brightness, direct.direction) == (None, None, None, None)
        assert direct.colors is None and direct.colors_min is None
        assert (wave.speed_min, wave.speed_max, wave.speed) == (1, 9, 5)
        assert (wave.brightness_min, wave.brightness_max, wave.brightness) == (0, 100, 80)
        assert wave.direction == 1 and wave.color_mode == oc.ModeColors.MODE_SPECIFIC
        assert wave.colors == [(10, 20, 30)] and (wave.colors_min, wave.colors_max) == (1, 2)
        assert [m.id for m in kbd.modes] == [0, 1]
        c.disconnect()
    finally:
        srv.close()


@test
def parse_v3_has_brightness_but_no_segments():
    srv = synthetic_server(3, sample_controllers(3))
    try:
        c = connect(srv)
        kbd = c.devices[0]
        assert c.protocol_version == 3
        assert kbd.zones[0].segments is None
        assert kbd.modes[1].brightness == 80 and kbd.metadata.vendor == "Vendor"
        c.disconnect()
    finally:
        srv.close()


@test
def parse_v0_when_server_does_not_answer_version():
    srv = synthetic_server(0, sample_controllers(0), answer_version=False)
    try:
        t0 = time.perf_counter()
        c = oc.OpenRGBClient("127.0.0.1", srv.port)
        elapsed = time.perf_counter() - t0
        settle(0.1)
        got = srv.take()
        assert c.protocol_version == 0
        assert all(p["payload"] == "" for p in got if p["cmd"] == CMD_DATA), "v0 data request has no payload"
        kbd = c.devices[0]
        assert kbd.metadata.vendor == "" and kbd.modes[1].brightness is None
        assert kbd.zones[1].matrix_map == [[0, None, 1], [2, 3, None]]
        assert elapsed < 3.0, f"version fallback took {elapsed:.1f}s"
        c.disconnect()
    finally:
        srv.close()


@test
def truncated_controller_data_raises_openrgb_error():
    ctrls = sample_controllers(4)
    ctrls[1] = ctrls[1][:40]
    srv = synthetic_server(4, ctrls)
    try:
        try:
            oc.OpenRGBClient("127.0.0.1", srv.port)
        except oc.OpenRGBDisconnected:
            raise AssertionError("truncated data is a protocol error, not a disconnection")
        except oc.OpenRGBError as exc:
            assert "Truncated" in str(exc)
        else:
            raise AssertionError("no error on truncated data")
    finally:
        srv.close()


@test
def refused_connection_raises_disconnected():
    srv = synthetic_server(4, sample_controllers(4))
    port = srv.port
    srv.close()
    try:
        oc.OpenRGBClient("127.0.0.1", port, timeout=1.0)
    except oc.OpenRGBDisconnected:
        pass
    else:
        raise AssertionError("connecting to a closed port must raise OpenRGBDisconnected")


@test
def lost_connection_raises_disconnected_and_ping_detects_it():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        assert c.ping() == 3
        srv.drop_clients()
        settle(0.1)
        try:
            c.ping()
        except oc.OpenRGBDisconnected:
            pass
        else:
            raise AssertionError("ping after the server dropped us must raise")
        assert not c.connected
        try:
            c.devices[0].set_colors([(1, 1, 1)] * 7, fast=True)
        except oc.OpenRGBDisconnected:
            pass
        else:
            raise AssertionError("write on a closed connection must raise")
    finally:
        srv.close()


@test
def writes_detect_a_dead_server():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        srv.drop_clients()
        deadline = time.time() + 3
        while time.time() < deadline:
            try:
                c.devices[0].set_colors([(1, 1, 1)] * 7, fast=True)
            except oc.OpenRGBDisconnected:
                return
            time.sleep(0.01)
        raise AssertionError("writes kept succeeding after the server closed the connection")
    finally:
        srv.close()


@test
def unsolicited_device_list_updated_is_skipped_and_flagged():
    flag = {"push": False}

    def extra(dev, cmd, payload):
        if cmd == CMD_COUNT and flag["push"]:
            return [(0, CMD_LIST_UPDATED, b""), (0, CMD_COUNT, struct.pack("<I", 3))]
        return None

    srv = synthetic_server(4, sample_controllers(4), extra=extra)
    try:
        c = connect(srv)
        assert not c.device_list_changed
        flag["push"] = True
        assert c.ping() == 3
        assert c.device_list_changed
        c.disconnect()
    finally:
        srv.close()


@test
def stale_reply_for_another_device_is_ignored():
    ctrls = sample_controllers(4)
    state = {"stale": False}

    def extra(dev, cmd, payload):
        if cmd == CMD_DATA and dev == 1 and state["stale"]:
            return [(0, CMD_DATA, ctrls[0]), (1, CMD_DATA, ctrls[1])]
        return None

    srv = synthetic_server(4, ctrls, extra=extra)
    try:
        c = connect(srv)
        state["stale"] = True
        strip = c.devices[1]
        strip.update()
        assert strip.name == "Strip", f"took the reply of another device: {strip.name}"
        c.disconnect()
    finally:
        srv.close()


@test
def update_keeps_object_identity():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        dev = c.devices[0]
        zone, led = dev.zones[1], dev.leds[4]
        dev.update()
        c.update()
        assert c.devices[0] is dev and dev.zones[1] is zone and dev.leds[4] is led
        assert zone.leds[1] is led
        c.disconnect()
    finally:
        srv.close()


@test
def concurrent_writers_never_interleave_packets():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        n_threads, n_frames = 4, 250
        errors = []

        kbd = c.devices[0]                # per-LED mode; half the threads write a zone (other size)

        def writer(t):
            try:
                target = kbd if t % 2 == 0 else kbd.zones[1]
                for k in range(n_frames):
                    target.set_colors([(t, k % 256, 7)] * len(target.leds), fast=True)
            except Exception as exc:     # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        settle(0.3)
        got = srv.take()
        assert not errors, errors
        assert len(got) == n_threads * n_frames, f"{len(got)} packets, expected {n_threads * n_frames}"
        sizes = {CMD_LEDS: 6 + 4 * 7, CMD_ZONE: 10 + 4 * 4}
        for p in got:
            assert len(bytes.fromhex(p["payload"])) == sizes[p["cmd"]], "corrupted packet"
        c.disconnect()
    finally:
        srv.close()


@test
def payload_formats():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        kbd = c.devices[0]
        cols = [(i, 255 - i, 9) for i in range(7)]
        kbd.set_colors(cols, fast=True)
        kbd.zones[1].set_colors([(1, 2, 3)] * 4, fast=True)
        kbd.leds[5].set_color(oc.RGBColor(4, 5, 6), fast=True)
        kbd.set_color((7, 8, 9))
        settle(0.15)
        got = [(p["dev"], p["cmd"], bytes.fromhex(p["payload"])) for p in srv.take()]
        zone_body = struct.pack("<iH", 1, 4) + col(1, 2, 3) * 4
        assert got == [
            (0, CMD_LEDS, leds_payload(cols)),
            (0, CMD_ZONE, struct.pack("<I", len(zone_body) + 4) + zone_body),
            (0, CMD_SINGLE, struct.pack("<i", 5) + col(4, 5, 6)),
            (0, CMD_LEDS, leds_payload([(7, 8, 9)] * 7)),
        ], got
        c.disconnect()
    finally:
        srv.close()


@test
def show_sends_only_changes():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        kbd = c.devices[0]
        kbd.show(fast=True)
        settle(0.1)
        assert srv.take() == [], "unchanged colors must send nothing"
        kbd.colors[2] = oc.RGBColor(9, 9, 9)
        kbd.show(fast=True)
        kbd.colors[0] = oc.RGBColor(1, 1, 1)
        kbd.colors[1] = oc.RGBColor(2, 2, 2)
        kbd.show(fast=True)
        settle(0.1)
        assert [p["cmd"] for p in srv.take()] == [CMD_SINGLE, CMD_LEDS]
        c.disconnect()
    finally:
        srv.close()


@test
def mode_specific_and_colorless_modes():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        _, strip, plain = c.devices
        strip.set_colors([(3, 4, 5)], fast=True)              # active mode "Static": mode colors
        settle(0.1)
        got = srv.take()
        assert [p["cmd"] for p in got][:1] == [CMD_MODE], got
        sent = bytes.fromhex(got[0]["payload"])
        assert sent.endswith(struct.pack("<H", 1) + col(3, 4, 5)), "mode colors not sent"
        assert struct.unpack_from("<i", sent, 4)[0] == 1, "mode index"
        strip.set_color((6, 7, 8))                            # colors_max copies
        settle(0.1)
        sent = bytes.fromhex(srv.take()[0]["payload"])
        assert sent.endswith(struct.pack("<H", 2) + col(6, 7, 8) * 2)
        plain.set_colors([(1, 1, 1)] * 2, fast=True)          # NONE mode: nothing, like openrgb-python
        plain.set_color((1, 1, 1))
        settle(0.1)
        assert srv.take() == []
        plain._set_device_colors([(2, 3, 4)] * 2, fast=True)  # IOBatcher path: writes whatever the mode
        settle(0.1)
        got = srv.take()
        assert [(p["cmd"], bytes.fromhex(p["payload"])) for p in got] == [(CMD_LEDS, leds_payload([(2, 3, 4)] * 2))], got
        try:
            strip.set_colors([(1, 1, 1)] * 3)
        except ValueError:
            pass
        else:
            raise AssertionError("too many mode colors accepted")
        c.disconnect()
    finally:
        srv.close()


@test
def ee_devices_and_errors():
    srv = synthetic_server(4, sample_controllers(4))
    try:
        c = connect(srv)
        assert [d.name for d in c.ee_devices] == ["Kbd", "Strip"]
        kbd = c.devices[0]
        for call, exc in ((lambda: kbd.set_mode("nope"), ValueError),
                          (lambda: kbd.set_mode(1.5), TypeError),
                          (lambda: kbd.set_colors([(1, 1, 1)] * 3, fast=True), IndexError),
                          (lambda: kbd.zones[0].set_colors([(1, 1, 1)], fast=True), IndexError),
                          (lambda: kbd.set_colors([(256, 0, 0)] * 7, fast=True), struct.error),
                          (lambda: kbd.set_colors([(1.5, 0, 0)] * 7, fast=True), struct.error)):
            try:
                call()
            except exc:
                pass
            else:
                raise AssertionError(f"expected {exc.__name__}")
        c.disconnect()
    finally:
        srv.close()


@test
def rgbcolor_compatibility():
    c = oc.RGBColor(1, 2, 3)
    assert c == (1, 2, 3) and (c.red, c.green, c.blue) == (1, 2, 3) and tuple(c) == (1, 2, 3)
    assert oc.RGBColor.fromHEX("#FF8000") == (255, 128, 0)
    assert oc.RGBColor.fromHSV(0, 100, 100) == (255, 0, 0)
    assert c.pack() == b"\x01\x02\x03\x00"
    assert oc._pack_colors([c, (4, 5, 6)]) == b"\x01\x02\x03\x00\x04\x05\x06\x00"


@test
def packing_is_faster_than_color_by_color():
    cols = [oc.RGBColor(i % 256, (i * 7) % 256, (i * 13) % 256) for i in range(105)]
    naive = lambda: b"".join(struct.pack("BBBx", x.red, x.green, x.blue) for x in cols)  # noqa: E731
    fast = lambda: oc._pack_colors(cols)  # noqa: E731
    assert naive() == fast()
    t_naive = min(timeit.repeat(naive, number=2000, repeat=5))
    t_fast = min(timeit.repeat(fast, number=2000, repeat=5))
    print(f"         105 LEDs: {t_fast / 2000 * 1e6:.1f} us vs {t_naive / 2000 * 1e6:.1f} us color by color "
          f"({t_naive / t_fast:.1f}x)")
    assert t_naive / t_fast >= 1.5, f"packing only {t_naive / t_fast:.2f}x faster"


def main() -> int:
    passed = failed = skipped = 0
    for fn in TESTS:
        name = fn.__name__
        try:
            fn()
            print(f"[OK]   {name}")
            passed += 1
        except Skip as exc:
            print(f"[SKIP] {name}: {exc}")
            skipped += 1
        except Exception as exc:
            print(f"[FAIL] {name}: {exc}")
            traceback.print_exc(limit=3)
            failed += 1
    print(f"\n  {passed} passed, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
