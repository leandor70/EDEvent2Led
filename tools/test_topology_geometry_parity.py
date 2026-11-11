"""
test_topology_geometry_parity.py

Blinda la parita' tra il backend (effects.topology_geometry) e il frontend
(web/js/topology-editor.js). Verifica che:

  1. led_world_position == formula di _ledWorldPos()  ((slot+0.5), ly=-0.5, cos/sin)
  2. scene_bbox        == calculateBoundingBox()/getZoneCorners()
  3. la rotazione e' CONTINUA (un caso a 45 gradi NON collassa a 0 gradi)
  4. la nuova formula DIVERGE dalla vecchia backend (lookup cardinale, i, no offset)

Dati reali: device "LedStripScrivania::linear" (config/device_topologies.json).
Output ASCII-safe (regola Windows-unicode-handling).
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects import topology_geometry as geo  # noqa: E402

TOL = 1e-9

# Zone reali di LedStripScrivania::linear
ZONES = [
    {"name": "Desktop",      "position": {"x": 1,     "y": 20.5}, "rotation": 0,   "led_count": 16, "led_spacing": 7.5},
    {"name": "MonitorRight", "position": {"x": 118.5, "y": 25.5}, "rotation": 90,  "led_count": 5,  "led_spacing": 7},
    {"name": "MonitorTop",   "position": {"x": 118.5, "y": 61.5}, "rotation": 180, "led_count": 12, "led_spacing": 5.833333333333333},
    {"name": "MonitorLeft",  "position": {"x": 48,    "y": 60},   "rotation": 270, "led_count": 5,  "led_spacing": 7},
]


def _frontend_led(zone, i):
    """Replica esatta di _ledWorldPos() del frontend (riferimento autorevole)."""
    sp = float(zone.get("led_spacing", 1.0))
    slot = zone["led_count"] - 1 - i if zone.get("direction") == "reverse" else i
    lx, ly = (slot + 0.5) * sp, -0.5
    rad = math.radians(zone["rotation"])
    c, s = math.cos(rad), math.sin(rad)
    return (zone["position"]["x"] + lx * c - ly * s,
            zone["position"]["y"] + lx * s + ly * c)


def _old_backend_led(zone, i):
    """Vecchia formula backend (Linear1D.get_led_world_position pre-fix)."""
    off = i * float(zone.get("led_spacing", 1.0))
    r, px, py = zone["rotation"], zone["position"]["x"], zone["position"]["y"]
    if r == 0:   return (px + off, py)
    if r == 90:  return (px, py + off)
    if r == 180: return (px - off, py)
    if r == 270: return (px, py - off)
    return (px + off, py)


def _close(a, b):
    return abs(a[0] - b[0]) < TOL and abs(a[1] - b[1]) < TOL


def main():
    results = []

    # 1. Parita' per-LED con il frontend
    ok = True
    for z in ZONES:
        for i in range(z["led_count"]):
            if not _close(geo.led_world_position(z, i), _frontend_led(z, i)):
                ok = False
    results.append(("led_world_position == frontend (_ledWorldPos)", ok))

    # 1b. direction "reverse": il LED 0 sta dove stava l'ultimo LED, e viceversa
    ok_rev = True
    for z in ZONES:
        zr = dict(z, direction="reverse")
        n = z["led_count"]
        for i in range(n):
            if not _close(geo.led_world_position(zr, i), geo.led_world_position(z, n - 1 - i)):
                ok_rev = False
            if not _close(geo.led_world_position(zr, i), _frontend_led(zr, i)):
                ok_rev = False
    results.append(("direction reverse: LED i nello slot n-1-i (backend == frontend)", ok_rev))

    # 1c. il centro del LED sta DENTRO il rettangolo disegnato (0..w x -1..0)
    ok_in = True
    for z in ZONES:
        x0, x1, y0, y1 = geo.scene_bbox([z])
        for i in range(z["led_count"]):
            px, py = geo.led_world_position(z, i)
            if not (x0 - TOL <= px <= x1 + TOL and y0 - TOL <= py <= y1 + TOL):
                ok_in = False
    results.append(("centro LED dentro il rettangolo della zona", ok_in))

    # 1d. Effetti: la "tela" (Linear1D.get_global_bbox) e' l'estensione dei CENTRI dei
    #     LED, cosi' il primo e l'ultimo LED normalizzano a 0 e 1 e una striscia
    #     orizzontale ha altezza 0. Il riquadro disegnato serve solo al centro effetto.
    from types import SimpleNamespace as NS
    from effects.linear_1d import Linear1D
    lin = Linear1D(NS(name="parity"), sum(z["led_count"] for z in ZONES), 0, "__parity__::linear")
    lin._zones = [dict(z, zone_index=k) for k, z in enumerate(ZONES)]
    lin._calculate_global_bbox()
    gb = lin.get_global_bbox()
    pts = [geo.led_world_position(z, i) for z in ZONES for i in range(z["led_count"])]
    ok_canvas = (abs(gb["min_x"] - min(p[0] for p in pts)) < TOL and abs(gb["max_x"] - max(p[0] for p in pts)) < TOL
                 and abs(gb["min_y"] - min(p[1] for p in pts)) < TOL and abs(gb["max_y"] - max(p[1] for p in pts)) < TOL)
    db = lin._drawn_bbox
    ok_drawn = all(abs(a - b) < TOL for a, b in zip((db["min_x"], db["max_x"], db["min_y"], db["max_y"]),
                                                    geo.scene_bbox(ZONES)))
    results.append(("Linear1D: tela effetti = estensione dei centri LED", ok_canvas))
    results.append(("Linear1D: riquadro disegnato (centro effetto) = scene_bbox editor", ok_drawn))

    # 2. Parita' bbox con i corner del frontend
    bx = geo.scene_bbox(ZONES)
    expected_bbox = (1.0, 121.0, 19.5, 62.5)
    ok_bbox = all(abs(a - b) < TOL for a, b in zip(bx, expected_bbox))
    results.append(("scene_bbox == (1, 121, 19.5, 62.5)", ok_bbox))

    # 3. Rotazione continua: 45 gradi NON deve comportarsi come 0 gradi
    z45 = {"position": {"x": 0, "y": 0}, "rotation": 45, "led_count": 2, "led_spacing": 10}
    p1 = geo.led_world_position(z45, 1)
    # a 45 gradi sia x sia y devono crescere (vecchio backend darebbe y costante)
    ok_rot = p1[0] > 1.0 and p1[1] > 1.0 and not _close(p1, _old_backend_led(z45, 1))
    results.append(("rotazione 45 gradi continua (non collassa a 0)", ok_rot))

    # 4. La nuova formula DEVE divergere dalla vecchia su MonitorLeft (estremi)
    ml = ZONES[3]
    diverges = not _close(geo.led_world_position(ml, 0), _old_backend_led(ml, 0))
    results.append(("nuova formula diverge dalla vecchia (MonitorLeft LED0)", diverges))

    # Report
    print("=" * 64)
    print("  Topology geometry parity (backend <-> frontend)")
    print("=" * 64)
    passed = 0
    for name, ok in results:
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status}  {name}")
        if ok:
            passed += 1
    print("-" * 64)
    print(f"  {passed}/{len(results)} test passati")

    # Evidenza numerica MonitorLeft (LED0/LED4): nuovo vs vecchio
    print()
    print("  MonitorLeft (rot 270) - nuovo (frontend) vs vecchio (backend pre-fix):")
    for i in (0, 4):
        n = geo.led_world_position(ml, i)
        o = _old_backend_led(ml, i)
        print(f"    LED{i}: nuovo=({n[0]:.1f},{n[1]:.1f})  vecchio=({o[0]:.1f},{o[1]:.1f})")

    print("=" * 64)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
