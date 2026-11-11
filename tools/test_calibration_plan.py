"""
test_calibration_plan.py

La calibrazione hardware deve mostrare ESATTAMENTE cio' che l'editor disegna.
L'editor manda il suo piano (anello e LED centrale per ogni LED, calcolati dalle
zone dal vivo); il backend fa solo la mappatura al LED fisico. Verifica:

  1. offset delle zone per zone_index (non per ordine nel piano)
  2. anello e LED centrale passano invariati al loop
  3. device non presenti nella scena NON vengono toccati (niente RAM fantasma)
  4. device del piano non collegati e LED oltre il led_count vengono saltati
  5. piano senza LED collegati -> errore, nessun thread
  6. senza piano resta il vecchio percorso (compatibilita')

Device finti: non tocca l'hardware. Output ASCII-safe.
"""
import sys
import time
import types
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import topology_api as tapi  # noqa: E402

_failures = []


def check(label, ok, detail=""):
    print(f"  {'[OK]' if ok else '[FAIL]'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        _failures.append(label)


class FakeController:
    def __init__(self):
        self.maps = []

    def apply_color_map(self, color_map):
        self.maps.append(dict(color_map))


class FakeDevice:
    """Hashable like the real DeviceEffectController (the loop groups by device)."""
    def __init__(self, key, led_count):
        self.device_key = key
        self.controller = FakeController()
        self.topology = NS(led_count=led_count, topology_type=None, device=NS(name=key))


def fake_device(key, led_count):
    return FakeDevice(key, led_count)


def main():
    print("=" * 70)
    print("  Test piano di calibrazione (editor -> LED fisici)")
    print("=" * 70)

    fake_ambilight = types.ModuleType("api.ambilight_api")
    fake_ambilight._ambilight_service = NS(pause=lambda: None, resume=lambda: None)
    fake_settings = types.ModuleType("api.settings_api")
    fake_settings.try_ensure_openrgb = lambda: True
    sys.modules["api.ambilight_api"] = fake_ambilight
    sys.modules["api.settings_api"] = fake_settings

    strip = fake_device("Strip::linear", 10)        # zone 0: 4 LED, zone 1: 6 LED
    ram = fake_device("RAM::linear", 6)             # collegata ma NON nella scena
    tapi._unified_manager = NS(devices=[strip, ram], stop_all_effects=lambda: None)

    # Piano con le zone in ordine inverso: l'offset deve seguire zone_index
    plan = {
        "zones": [
            {"device_id": "Strip::linear", "zone_index": 1, "led_count": 6},
            {"device_id": "Strip::linear", "zone_index": 0, "led_count": 4},
            {"device_id": "Ghost::linear", "zone_index": 0, "led_count": 3},
        ],
        "leds": (
            [{"device_id": "Strip::linear", "zone_index": 1, "led_index": i, "ring": 10 + i,
              "center": i == 2} for i in range(6)]
            + [{"device_id": "Strip::linear", "zone_index": 0, "led_index": i, "ring": i,
                "center": False} for i in range(4)]
            + [{"device_id": "Ghost::linear", "zone_index": 0, "led_index": 0, "ring": 0,
                "center": False}]
        ),
    }

    print("\n0. esposizione a Eel (il browser chiama per nome)")
    import eel
    exposed = getattr(eel, "_exposed_functions", {})
    check("test_topology_calibration esposta", "test_topology_calibration" in exposed)
    check("stop_topology_calibration esposta", "stop_topology_calibration" in exposed)
    check("_plan_led_data NON esposta (helper interno)", "_plan_led_data" not in exposed)

    print("\n1-4. mappatura")
    data = tapi._plan_led_data(plan)
    by_hw = {hw: (ring, c) for ctrl, hw, ring, c in data if ctrl is strip}
    check("zona 0 -> LED fisici 0..3", all(by_hw.get(i, (None,))[0] == i for i in range(4)), by_hw)
    check("zona 1 -> LED fisici 4..9", all(by_hw.get(4 + i, (None,))[0] == 10 + i for i in range(6)), by_hw)
    check("LED centrale = zona 1 #2 = fisico 6", [hw for hw, (_, c) in by_hw.items() if c] == [6], by_hw)
    check("RAM fuori scena mai toccata", not any(ctrl is ram for ctrl, *_ in data))
    check("device non collegato saltato", len(data) == 10, len(data))

    over = {"zones": [{"device_id": "Strip::linear", "zone_index": 0, "led_count": 12}],
            "leds": [{"device_id": "Strip::linear", "zone_index": 0, "led_index": i, "ring": 0,
                      "center": False} for i in range(12)]}
    check("LED oltre il led_count saltati", len(tapi._plan_led_data(over)) == 10)

    print("\n2. il loop colora i LED come il piano")
    res = tapi.test_topology_calibration({"x": 50, "y": 50}, 10, {"center": {"blink": False}}, plan)
    check("calibrazione avviata", res.get("success") and res.get("leds_colored") == 10, res)
    time.sleep(0.15)
    tapi.stop_topology_calibration()
    last = strip.controller.maps[-1] if strip.controller.maps else {}
    check("anello 0 -> bianco", last.get(0) == (255, 255, 255), last.get(0))
    check("anello 1 -> rosso", last.get(1) == (255, 60, 60), last.get(1))
    check("centro (fisso, senza blink) -> bianco", last.get(6) == (255, 255, 255), last.get(6))
    check("anello 13 -> rosso (13 % 4 = 1)", last.get(7) == (255, 60, 60), last.get(7))
    check("RAM mai scritta", ram.controller.maps == [], len(ram.controller.maps))

    print("\n5. piano senza LED collegati")
    ghost = {"zones": [{"device_id": "Ghost::linear", "zone_index": 0, "led_count": 3}],
             "leds": [{"device_id": "Ghost::linear", "zone_index": 0, "led_index": 0, "ring": 0}]}
    res = tapi.test_topology_calibration({"x": 50, "y": 50}, 10, None, ghost)
    check("errore esplicito", res.get("success") is False, res)
    tapi.stop_topology_calibration()

    print("\n6. senza piano: vecchio percorso")
    tapi._unified_manager = NS(devices=[], stop_all_effects=lambda: None)
    res = tapi.test_topology_calibration({"x": 50, "y": 50}, 10)
    check("vecchio percorso risponde (nessun device lineare)", res.get("success") is False, res)
    tapi.stop_topology_calibration()

    print()
    if _failures:
        print(f"  [FAIL] {len(_failures)} controlli falliti")
        return 1
    print("  [OK] TUTTI I CONTROLLI PASSATI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
