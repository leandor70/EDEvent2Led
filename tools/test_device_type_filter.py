"""
test_device_type_filter.py

Verifica che il tipo del device arrivi da OpenRGB e non dal nome:

  1. devices_api.get_devices: tipo da device.type (un nome con "led" o "k7" non inganna)
  2. ambilight_api.get_ambilight_devices: una tastiera senza matrix_map (topologia LINEAR)
     non viene proposta all'ambilight; un device con "K7" nel nome ma di tipo LEDSTRIP si'

Device finti: non tocca config/ ne' l'hardware. Output ASCII-safe.
"""
import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utils.openrgb_client import DeviceType  # noqa: E402
from effects.device_topology import TopologyType  # noqa: E402
from api import devices_api, ambilight_api, keyboard_api  # noqa: E402

_failures = []


def check(label, ok, detail=""):
    print(f"  {'[OK]' if ok else '[FAIL]'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        _failures.append(label)


def ctrl(name, dtype, ttype, leds=10):
    dev = NS(name=name, type=dtype)
    topo = NS(device=dev, name=name, topology_type=ttype, led_count=leds, dimensions=(leds,))
    return NS(topology=topo, device_key=f"{name}::{ttype.name.lower()}")


def main():
    print("=" * 70)
    print("  Test tipo device da OpenRGB")
    print("=" * 70)

    devs = [
        ctrl("Generic Board", DeviceType.KEYBOARD, TopologyType.LINEAR),
        ctrl("Desk K7 Strip", DeviceType.LEDSTRIP, TopologyType.LINEAR),
        ctrl("Real Keyboard", DeviceType.KEYBOARD, TopologyType.MATRIX, leds=100),
        ctrl("Led Mouse", DeviceType.MOUSE, TopologyType.LINEAR, leds=4),
    ]
    mgr = NS(devices=devs, _make_device_key=lambda c: c.device_key)

    print("\n1. devices_api.get_devices")
    devices_api._manager = mgr
    keyboard_api._manager = mgr  # il decoratore with_openrgb_check guarda questo
    res = devices_api.get_devices()
    types_ = {d["name"]: d["type"] for d in res.get("devices", [])}
    check("risposta valida", res.get("success", True) is not False, res)
    check("tastiera senza matrice: keyboard", types_.get("Generic Board") == "keyboard", types_)
    check("nome con K7 ma LEDSTRIP: strip", types_.get("Desk K7 Strip") == "strip", types_)
    check("nome con 'led' ma MOUSE: mouse", types_.get("Led Mouse") == "mouse", types_)

    print("\n2. ambilight_api.get_ambilight_devices")
    ambilight_api._effect_manager = mgr
    ambilight_api._ambilight_service = None
    ambilight_api._read_device_config = lambda: {"devices": {}}
    ambilight_api._write_ambilight_config = lambda *a, **k: None
    names = [d["name"] for d in ambilight_api.get_ambilight_devices()]
    check("tastiera LINEAR esclusa", "Generic Board" not in names, names)
    check("tastiera MATRIX esclusa", "Real Keyboard" not in names, names)
    check("striscia con K7 nel nome inclusa", "Desk K7 Strip" in names, names)
    check("mouse incluso", "Led Mouse" in names, names)

    print()
    if _failures:
        print(f"  [FAIL] {len(_failures)} controlli falliti")
        return 1
    print("  [OK] TUTTI I CONTROLLI PASSATI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
