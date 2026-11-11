"""
test_topology_segment_indexes.py

Verifica che zone_index sia univoco anche per i device con segmenti (E1.31/ARGB):

  1. _read_openrgb_zones: indici progressivi su zone e segmenti, invariati senza segmenti
  2. _renumber_legacy_zones: rinumera per posizione i JSON vecchi, non tocca gli altri
  3. reload_device_from_openrgb: con 2 zone x 2 segmenti il layout salvato non si mischia
  4. build_device_zones: offset LED corretti anche con indici duplicati nel JSON

Usa device finti e una cartella temporanea: non tocca config/ ne' l'hardware.
Output ASCII-safe (regola Windows-unicode-handling).
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import topology_api as tapi  # noqa: E402
from effects import ambilight_service as asvc  # noqa: E402

_failures = []


def check(label, ok, detail=""):
    print(f"  {'[OK]' if ok else '[FAIL]'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        _failures.append(label)


def seg(name, n, start=0):
    return NS(name=name, leds_count=n, start_idx=start)


def zone_plain(name, n):
    return NS(name=name, leds=[object()] * n)


def zone_segmented(name, segs):
    return NS(name=name, leds=[object()] * sum(s.leds_count for s in segs), segments=segs)


def device(name, zones):
    return NS(name=name, zones=zones, leds=[object()] * sum(len(z.leds) for z in zones))


def test_read_zones():
    print("\n1. _read_openrgb_zones")
    plain = device("Plain", [zone_plain("A", 10), zone_plain("B", 5), zone_plain("C", 3)])
    idx = [z["zone_index"] for z in tapi._read_openrgb_zones(plain)]
    check("senza segmenti: indici 0,1,2 (come prima)", idx == [0, 1, 2], idx)

    two_seg = device("Seg", [
        zone_segmented("Z0", [seg("S0", 4), seg("S1", 6)]),
        zone_segmented("Z1", [seg("S2", 8), seg("S3", 2)]),
    ])
    zones = tapi._read_openrgb_zones(two_seg)
    idx = [z["zone_index"] for z in zones]
    check("2 zone x 2 segmenti: indici 0,1,2,3 univoci", idx == [0, 1, 2, 3], idx)
    check("led_count dei segmenti preservati", [z["led_count"] for z in zones] == [4, 6, 8, 2])

    mixed = device("Mixed", [zone_plain("P", 5), zone_segmented("Z", [seg("S0", 3), seg("S1", 3)])])
    idx = [z["zone_index"] for z in tapi._read_openrgb_zones(mixed)]
    check("zona normale + segmenti: indici 0,1,2", idx == [0, 1, 2], idx)


def test_renumber():
    print("\n2. _renumber_legacy_zones")
    legacy = [{"zone_index": 0, "name": "a", "x": 1}, {"zone_index": 1, "name": "b", "x": 2},
              {"zone_index": 0, "name": "c", "x": 3}, {"zone_index": 1, "name": "d", "x": 4}]
    out = tapi._renumber_legacy_zones(legacy)
    check("duplicati rinumerati per posizione", [z["zone_index"] for z in out] == [0, 1, 2, 3])
    check("altri campi conservati", [z["x"] for z in out] == [1, 2, 3, 4])
    check("lista originale non modificata", [z["zone_index"] for z in legacy] == [0, 1, 0, 1])
    clean = [{"zone_index": 0}, {"zone_index": 1}]
    check("lista senza duplicati restituita invariata", tapi._renumber_legacy_zones(clean) is clean)


def _write_topology(zones, key="Strip::linear"):
    Path("config").mkdir(exist_ok=True)
    Path("config/device_topologies.json").write_text(json.dumps({
        "version": 1,
        "topologies": {key: {"device_id": key, "effect_center": {"x": 50, "y": 50}, "zones": zones}},
    }), encoding="utf-8")


def test_reload():
    print("\n3. reload_device_from_openrgb (layout non mischiato)")
    dev = device("Strip", [
        zone_segmented("Z0", [seg("S0", 4), seg("S1", 6)]),
        zone_segmented("Z1", [seg("S2", 8), seg("S3", 2)]),
    ])
    from effects.device_topology import TopologyType
    ctrl = NS(topology=NS(device=dev, topology_type=TopologyType.LINEAR, led_count=len(dev.leds)))

    fake_settings = types.ModuleType("api.settings_api")
    fake_settings.try_ensure_openrgb = lambda: True
    sys.modules["api.settings_api"] = fake_settings
    tapi._unified_manager = NS(devices=[ctrl])

    legacy = [
        {"zone_index": 0, "name": "S0", "led_count": 4, "position": {"x": 0, "y": 0}},
        {"zone_index": 1, "name": "S1", "led_count": 6, "position": {"x": 100, "y": 0}},
        {"zone_index": 0, "name": "S2", "led_count": 8, "position": {"x": 200, "y": 0}},
        {"zone_index": 1, "name": "S3", "led_count": 2, "position": {"x": 300, "y": 0}},
    ]
    _write_topology(legacy)
    res = tapi.reload_device_from_openrgb("Strip::linear")
    check("reload riuscito", res.get("success") is True, res.get("error"))
    zones = res.get("zones", [])
    check("posizioni conservate in ordine [0,100,200,300]",
          [z["position"]["x"] for z in zones] == [0, 100, 200, 300],
          [z["position"]["x"] for z in zones])
    check("zone_index univoci 0..3", [z["zone_index"] for z in zones] == [0, 1, 2, 3])
    saved = json.loads(Path("config/device_topologies.json").read_text(encoding="utf-8"))
    saved_idx = [z["zone_index"] for z in saved["topologies"]["Strip::linear"]["zones"]]
    check("JSON salvato con indici univoci", saved_idx == [0, 1, 2, 3], saved_idx)


def test_build_zones():
    print("\n4. build_device_zones (offset con indici duplicati)")
    base = {"rotation": 0, "led_spacing": 1.0}
    legacy = [
        dict(base, zone_index=0, name="MonitorRight", led_count=5, position={"x": 10, "y": 0}),
        dict(base, zone_index=1, name="MonitorTop",   led_count=12, position={"x": 0, "y": 10}),
        dict(base, zone_index=0, name="MonitorLeft",  led_count=5, position={"x": 0, "y": 0}),
        dict(base, zone_index=1, name="Desktop",      led_count=16, position={"x": 0, "y": 20}),
    ]
    _write_topology(legacy)
    zones, total = asvc.build_device_zones("Strip::linear")
    offsets = {z["name"]: z["led_offset"] for z in zones}
    check("totale LED 38", total == 38, total)
    check("offset in ordine hardware (file): Right=0, Top=5, Left=17, Desktop=22",
          offsets == {"MonitorRight": 0, "MonitorTop": 5, "MonitorLeft": 17, "Desktop": 22}, offsets)


def main():
    print("=" * 70)
    print("  Test zone_index univoci (segmenti)")
    print("=" * 70)
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            test_read_zones()
            test_renumber()
            test_reload()
            test_build_zones()
        finally:
            os.chdir(old_cwd)
    print()
    if _failures:
        print(f"  [FAIL] {len(_failures)} controlli falliti")
        return 1
    print("  [OK] TUTTI I CONTROLLI PASSATI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
