"""
test_ambilight_geometry.py

Verifica che l'ambilight decida cosa leggere dalla TOPOLOGIA (posizione dei LED
rispetto al rettangolo schermo) e non dai nomi delle zone:

  1. lati: striscia destra/sinistra/alto/basso leggono il lato giusto, con
     l'asse verticale corretto (LED in alto = meta' superiore dello schermo)
  2. i nomi delle zone non contano (stessa topologia, nomi diversi = stessi colori)
  3. direction "reverse" inverte davvero l'ordine dei LED
  4. un LED dentro il rettangolo legge il punto di schermo sotto di lui
  5. un LED fuori dal rettangolo non viene mai scritto
  6. LED liberi: una zona spenta riceve il nero UNA volta e poi non viene piu' toccata
  7. il centro del LED sta sul bordo disegnato (rotazione continua, nessun lookup cardinale)

Layout sintetico (coordinate editor, y SU, rettangolo schermo x 0..20, y 0..10):
  destra  rot 90  : sale, LED 0 in basso
  sinistra rot 270 : scende, LED 0 in alto
  alto    rot 180 : va verso sinistra
  basso   rot 0   : va verso destra
Frame: meta' superiore ROSSA, meta' inferiore BLU.

Output ASCII-safe (regola Windows-unicode-handling).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects import ambilight_service as A  # noqa: E402

RED, BLUE, BLACK = (255, 0, 0), (0, 0, 255), (0, 0, 0)
RECT = {"x_min": 0, "x_max": 20, "y_min": 0, "y_max": 10}


def zone(idx, name, n, x, y, rot, direction="forward", spacing=1.0):
    return {"name": name, "zone_index": idx, "led_count": n, "led_spacing": spacing,
            "position": {"x": x, "y": y}, "rotation": rot, "direction": direction}


def layout(names=("R", "L", "T", "B"), right_dir="forward", extra=()):
    r, l, t, b = names
    return [
        zone(0, r, 8, 19.5, 1.0, 90, right_dir),
        zone(1, l, 8, 0.5, 9.0, 270),
        zone(2, t, 20, 20.0, 9.5, 180),
        zone(3, b, 20, 0.0, 0.5, 0),
        *extra,
    ]


class FakeManager:
    """Registra cio' che l'ambilight scrive: {device: ultimo dict {led: colore}}."""
    def __init__(self):
        self.writes = []
        self.devices = []

    def apply_direct_leds(self, device_key, led_colors):
        self.writes.append((device_key, dict(led_colors)))
        return True

    def is_effect_playing(self):
        return False


def frame():
    f = np.zeros((100, 200, 3), np.uint8)
    f[:50] = (0, 0, 255)     # BGR: rosso in alto
    f[50:] = (255, 0, 0)     # BGR: blu in basso
    return f


def run(zones, rect=RECT, zones_enabled=None, svc=None, fr=None):
    """Una passata di _process_frame; ritorna (svc, mgr, {led: colore} dell'ultima scrittura)."""
    topo = {"version": 1, "topologies": {"dev": {"zones": zones}}}
    if rect:
        topo["screen_rect"] = rect
    Path("config").mkdir(exist_ok=True)
    Path("config/device_topologies.json").write_text(json.dumps(topo), encoding="utf-8")
    mgr = FakeManager() if svc is None else svc._effect_manager
    if svc is None:
        svc = A.AmbilightService(mgr)
    svc._zone_cache.clear()
    dev = {"enabled": True}
    if zones_enabled is not None:
        dev["zones_enabled"] = zones_enabled
    svc._config = {"enabled": True, "strategy": "mean", "depth": 10, "saturation_boost": 1.0,
                   "devices": {"dev": dev}}
    svc._process_frame(fr if fr is not None else frame(), dict(svc._config))
    return svc, mgr, (mgr.writes[-1][1] if mgr.writes else {})


def check_partial_writes():
    """apply_direct_leds: un pacchetto se tutti i LED, per zona se coperta, altrimenti per LED."""
    from types import SimpleNamespace as NS
    from effects.unified_manager import UnifiedEffectManager as UM

    log = []

    class Led:
        def __init__(self, i):
            self.id = i

        def set_color(self, color, fast=False):
            log.append(("led", self.id))

    class Zone:
        def __init__(self, ids):
            self.leds = [Led(i) for i in ids]

        def set_colors(self, colors, fast=False):
            log.append(("zone", [l.id for l in self.leds]))

    device = NS(name="fake", leds=[Led(i) for i in range(10)],
                zones=[Zone(range(0, 4)), Zone(range(4, 10))],
                colors=[None] * 10, set_colors=lambda c, fast=False: log.append(("all", len(c))))
    ctrl = NS(topology=NS(device=device, led_count=10), key="d::linear")
    me = NS(disabled_device_keys=set(), devices=[ctrl], _make_device_key=lambda c: c.key)
    c = (1, 2, 3)

    out = []
    log.clear()
    UM.apply_direct_leds(me, "d::linear", {i: c for i in range(10)})
    out.append(("tutti i LED: un solo pacchetto per device", [e[0] for e in log] == ["all"]))

    log.clear()
    UM.apply_direct_leds(me, "d::linear", {i: c for i in range(0, 4)})
    out.append(("zona OpenRGB interamente coperta: un pacchetto di zona",
                log == [("zone", [0, 1, 2, 3])]))

    log.clear()
    UM.apply_direct_leds(me, "d::linear", {0: c, 1: c, 5: c})
    out.append(("copertura parziale: solo i LED indicati, nessun altro",
                sorted(e[1] for e in log if e[0] == "led") == [0, 1, 5] and all(e[0] == "led" for e in log)))

    log.clear()
    me.disabled_device_keys = {"d::linear"}
    out.append(("device disabilitato: nessuna scrittura",
                UM.apply_direct_leds(me, "d::linear", {0: c}) is False and not log))
    return out


def check_device_toggle_and_aurora():
    """Regressioni: device fuori dal riquadro deve restare accendibile; Aurora orizzontale."""
    from types import SimpleNamespace as NS
    import api.ambilight_api as api
    from effects.device_topology import TopologyType
    from effects.linear_1d import Linear1D
    from effects.spatial_effects_1d import AuroraEffect1D

    out = []
    # Riquadro automatico = solo i device accesi (B). A e' lontano: fuori schermo,
    # ma deve poter essere acceso (has_topology True, on_screen False).
    topo = {"version": 1, "topologies": {
        "A::linear": {"zones": [zone(0, "a", 5, 500.0, 500.0, 0)]},
        "B::linear": {"zones": layout()},
    }}
    Path("config").mkdir(exist_ok=True)
    Path("config/device_topologies.json").write_text(json.dumps(topo), encoding="utf-8")

    def ctrl(key, n):
        return NS(key=key, topology=NS(led_count=n, topology_type=TopologyType.LINEAR,
                                       device=NS(name=key, type=NS(name="LEDSTRIP"))))
    mgr = FakeManager()
    mgr.devices = [ctrl("A::linear", 5), ctrl("B::linear", 56)]
    mgr._make_device_key = lambda c: c.key
    svc = A.AmbilightService(mgr)
    svc._config = {"enabled": True, "devices": {"B::linear": {"enabled": True}}}
    svc.set_config = lambda u: svc._config.update(u)
    old = (api._effect_manager, api._ambilight_service, api.display_name)
    api._effect_manager, api._ambilight_service = mgr, svc
    api.display_name = lambda c, devs: c.key
    try:
        devs = {d["device_key"]: d for d in api.get_ambilight_devices()}
    finally:
        api._effect_manager, api._ambilight_service, api.display_name = old
    a, b = devs.get("A::linear", {}), devs.get("B::linear", {})
    out.append(("device fuori schermo: resta accendibile (has_topology)", a.get("has_topology") is True))
    out.append(("device fuori schermo: on_screen False", a.get("on_screen") is False))
    out.append(("device sullo schermo: has_topology e on_screen", b.get("has_topology") and b.get("on_screen")))

    # Aurora: striscia orizzontale (bbox alta 1 = spessore) deve restare orizzontale
    topo = {"version": 1, "topologies": {
        "H::linear": {"zones": [zone(0, "h", 16, 0.0, 0.0, 0, spacing=2.0)]},
        "V::linear": {"zones": [zone(0, "v", 16, 0.0, 0.0, 90, spacing=2.0)]},
    }}
    Path("config/device_topologies.json").write_text(json.dumps(topo), encoding="utf-8")
    # Ramo in coordinate mondo (use_normalized=False): li' conta is_horizontal
    h = AuroraEffect1D(Linear1D(NS(name="H"), 16, 0, "H::linear"), use_normalized=False)
    v = AuroraEffect1D(Linear1D(NS(name="V"), 16, 0, "V::linear"), use_normalized=False)
    out.append(("Aurora: striscia orizzontale riconosciuta come orizzontale", h.is_horizontal is True))
    out.append(("Aurora: striscia verticale resta verticale", v.is_horizontal is False))
    return out


def main():
    results = []
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            # 1. Lati e asse verticale ------------------------------------------
            _, _, w = run(layout())
            right = [w[0 + i] for i in range(8)]            # zona 0: LED 0..7
            left = [w[8 + i] for i in range(8)]             # zona 1: LED 8..15
            top = [w[16 + i] for i in range(20)]            # zona 2
            bottom = [w[36 + i] for i in range(20)]         # zona 3
            ok_right = right[0] == BLUE and right[7] == RED       # LED 0 in basso
            ok_left = left[0] == RED and left[7] == BLUE          # LED 0 in alto
            results.append(("destra (rot 90): LED 0 in basso legge il blu, in alto il rosso", ok_right))
            results.append(("sinistra (rot 270): LED 0 in alto legge il rosso, in basso il blu", ok_left))
            results.append(("alto legge la meta' superiore (rosso)", all(c == RED for c in top)))
            results.append(("basso legge la meta' inferiore (blu)", all(c == BLUE for c in bottom)))

            # 2. I nomi non contano ----------------------------------------------
            _, _, w2 = run(layout(names=("x1", "zzz", "???", "Strip")))
            results.append(("nomi diversi (anche '???'), stessi colori", w2 == w))

            # 3. direction reverse inverte l'ordine ------------------------------
            _, _, w3 = run(layout(right_dir="reverse"))
            right_rev = [w3[0 + i] for i in range(8)]
            results.append(("direction reverse: LED 0 della destra ora in alto (rosso)",
                            right_rev[0] == RED and right_rev[7] == BLUE))

            # 4. LED dentro il rettangolo = punto di schermo sotto di lui --------
            f = frame()
            f[25:75, 60:140] = (0, 255, 0)                   # rettangolo verde al centro
            centre = zone(4, "punto", 1, 9.5, 5.5, 0)        # centro LED = (10, 5)
            _, _, w4 = run(layout(extra=[centre]), fr=f)
            c = w4.get(56)                                   # dopo 8+8+20+20 LED
            results.append(("LED dentro il rettangolo legge il punto sotto di lui (verde dominante)",
                            c is not None and c[1] > c[0] and c[1] > c[2]))

            # 5. LED fuori dal rettangolo mai scritti ----------------------------
            outside = zone(5, "fuori", 3, 40.0, 5.0, 0)
            _, _, w5 = run(layout(extra=[outside]))
            results.append(("LED fuori dal rettangolo non scritti",
                            all(i not in w5 for i in (56, 57, 58))))

            # 6. LED liberi: nero una sola volta, poi niente ---------------------
            svc, mgr, _ = run(layout())
            n_before = len(mgr.writes)
            run(layout(), zones_enabled={"0": False}, svc=svc)      # spengo la destra (indice 0)
            released = mgr.writes[-1][1]
            ok_black = all(released.get(i) == BLACK for i in range(8))
            run(layout(), zones_enabled={"0": False}, svc=svc)      # frame successivo
            again = mgr.writes[-1][1]
            ok_free = all(i not in again for i in range(8))
            results.append(("zona spenta: nero una volta sola", ok_black))
            results.append(("zona spenta: poi i suoi LED non vengono piu' toccati", ok_free))
            results.append(("nessun LED non pilotato nel pacchetto (fuori zona spenta)",
                            n_before >= 1 and len(again) == 48))

            # 6b. Scrittura parziale verso OpenRGB (apply_direct_leds)
            results.extend(check_partial_writes())

            # 6c. Regressioni corrette (toggle device, Aurora)
            results.extend(check_device_toggle_and_aurora())

            # 7. Rotazione continua: una striscia a 45 gradi non collassa --------
            from effects import topology_geometry as geo
            z45 = zone(0, "diag", 4, 0.0, 0.0, 45)
            pts = A._led_world_positions(z45)
            results.append(("rotazione 45: x cresce e y (schermo) decresce lungo la striscia",
                            pts[3][0] > pts[0][0] and pts[3][1] < pts[0][1]))
        finally:
            os.chdir(cwd)

    print("=" * 70)
    print("  Ambilight: la topologia decide, non i nomi")
    print("=" * 70)
    passed = 0
    for name, ok in results:
        print(f"  {'[OK]' if ok else '[FAIL]'}  {name}")
        passed += bool(ok)
    print("-" * 70)
    print(f"  {passed}/{len(results)} test passati")
    print("=" * 70)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
