"""
test_ambilight_pause.py

Verifica il coordinamento tra ambilight, flash e calibrazione:

  1. pause(): blackout dei soli device abilitati, col conteggio LED dell'hardware
  2. pause() ripetuta: un solo blackout (niente sfarfallio durante la calibrazione)
  3. resume(): riattiva senza stampare "Service stopped"
  4. _process_frame in pausa: nessuna scrittura sui LED
  5. flash: la pausa e' un contatore, l'ambilight riprende solo all'ultimo flash

Device finti e cartella temporanea: non tocca config/ ne' l'hardware.
Output ASCII-safe (regola Windows-unicode-handling).
"""
import io
import os
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects.ambilight_service import AmbilightService  # noqa: E402

_failures = []


def check(label, ok, detail=""):
    print(f"  {'[OK]' if ok else '[FAIL]'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        _failures.append(label)


class FakeManager:
    def __init__(self, leds_by_key):
        self.devices = [NS(key=k, topology=NS(led_count=n)) for k, n in leds_by_key.items()]
        self.calls = []

    @staticmethod
    def _make_device_key(ctrl):
        return ctrl.key

    def apply_direct_colors(self, key, colors):
        self.calls.append((key, list(colors)))
        return True

    def apply_direct_leds(self, key, led_colors):
        # L'ambilight scrive solo i LED in uso (vedi unified_manager.apply_direct_leds)
        self.calls.append((key, dict(led_colors)))
        return True


def make_service():
    mgr = FakeManager({"A::linear": 30, "B::linear": 10})
    svc = AmbilightService(mgr)
    svc._config["devices"] = {"A::linear": {"enabled": True}, "B::linear": {"enabled": False}}
    return svc, mgr


def test_pause_blackout():
    print("\n1-3. pause() / resume()")
    svc, mgr = make_service()
    svc.pause()
    check("blackout inviato solo al device abilitato", [c[0] for c in mgr.calls] == ["A::linear"],
          [c[0] for c in mgr.calls])
    check("blackout con 30 LED (conteggio hardware), tutti neri",
          len(mgr.calls) == 1 and len(mgr.calls[0][1]) == 30 and all(c == (0, 0, 0) for c in mgr.calls[0][1]))

    svc.pause()
    svc.pause()
    check("pause() ripetuta: nessun blackout aggiuntivo", len(mgr.calls) == 1, len(mgr.calls))

    buf = io.StringIO()
    with redirect_stdout(buf):
        svc.resume()
    check("resume(): flag azzerato", svc._paused is False)
    check("resume(): niente 'Service stopped'", "Service stopped" not in buf.getvalue(), buf.getvalue())

    svc.pause()
    check("nuova pause() dopo resume(): nuovo blackout", len(mgr.calls) == 2, len(mgr.calls))


def test_process_frame_paused():
    print("\n4. _process_frame con ambilight in pausa")
    svc, mgr = make_service()
    zone = {"name": "MonitorRight", "zone_index": 0, "led_count": 3, "led_offset": 0, "led_start": 0,
            "led_end": 3, "screen_start": 0.0, "screen_end": 1.0, "edge": "right", "reversed": False}
    svc._zone_cache["A::linear"] = ([zone], 3)
    svc._frame_size = (160, 90)   # stesso schermo del frame: la cache zone non viene ricalcolata
    frame = np.full((90, 160, 3), 200, dtype=np.uint8)

    svc._process_frame(frame, svc.get_config())
    check("senza pausa: il frame viene scritto", len(mgr.calls) == 1, len(mgr.calls))

    mgr.calls.clear()
    svc._paused = True
    svc._process_frame(frame, svc.get_config())
    check("in pausa: nessuna scrittura", mgr.calls == [], mgr.calls)


def test_flash_counter():
    print("\n5. flash: pausa come contatore")
    fake_settings = types.ModuleType("api.settings_api")
    fake_settings.try_ensure_openrgb = lambda: True
    fake_settings.with_openrgb_check = lambda f: f
    sys.modules["api.settings_api"] = fake_settings
    from api import devices_api as dapi

    events = []
    svc = NS(pause=lambda: events.append("pause"), resume=lambda: events.append("resume"))

    dapi._flash_hold(svc)
    dapi._flash_hold(svc)
    check("due flash sovrapposti: una sola pause()", events == ["pause"], events)
    dapi._flash_release(svc)
    check("primo flash finito: l'ambilight resta in pausa", events == ["pause"], events)
    dapi._flash_release(svc)
    check("ultimo flash finito: resume()", events == ["pause", "resume"], events)


def main():
    print("=" * 70)
    print("  Test pausa ambilight / flash")
    print("=" * 70)
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            test_pause_blackout()
            test_process_frame_paused()
            test_flash_counter()
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
