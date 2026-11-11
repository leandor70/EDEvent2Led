"""
test_calibration_stop.py

Verifica che stop_topology_calibration sia sicuro da chiamare a ogni uscita
dalla pagina (pagehide / disconnessione del browser):

  1. senza calibrazione attiva: no-op (niente stop effetti, niente resume ambilight)
  2. calibrazione avviata (anche se fallisce dopo la pausa): lo stop riprende
     l'ambilight una volta sola e ferma gli effetti
  3. seconda chiamata di stop: di nuovo no-op

Device finti: non tocca l'hardware. Output ASCII-safe.
"""
import sys
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


def main():
    print("=" * 70)
    print("  Test stop calibrazione (no-op / resume ambilight)")
    print("=" * 70)

    events = []
    fake_ambilight = types.ModuleType("api.ambilight_api")
    fake_ambilight._ambilight_service = NS(pause=lambda: events.append("pause"),
                                           resume=lambda: events.append("resume"))
    fake_settings = types.ModuleType("api.settings_api")
    fake_settings.try_ensure_openrgb = lambda: True
    sys.modules["api.ambilight_api"] = fake_ambilight
    sys.modules["api.settings_api"] = fake_settings

    effects_stopped = []
    tapi._unified_manager = NS(devices=[], stop_all_effects=lambda: effects_stopped.append(1))

    print("\n1. stop senza calibrazione attiva")
    res = tapi.stop_topology_calibration()
    check("risponde success + already_stopped", res.get("success") and res.get("already_stopped"), res)
    check("nessun resume() dell'ambilight", events == [], events)
    check("effetti non fermati", effects_stopped == [], effects_stopped)

    print("\n2. calibrazione avviata (nessun device lineare -> fallisce dopo la pausa)")
    res = tapi.test_topology_calibration({"x": 50, "y": 50}, 5.0)
    check("la calibrazione riporta l'errore", res.get("success") is False, res)
    check("ambilight messo in pausa", events == ["pause"], events)
    res = tapi.stop_topology_calibration()
    check("stop esegue davvero", res.get("success") and not res.get("already_stopped"), res)
    check("ambilight ripreso una volta", events == ["pause", "resume"], events)
    check("effetti fermati", effects_stopped == [1], effects_stopped)

    print("\n3. seconda chiamata di stop")
    res = tapi.stop_topology_calibration()
    check("di nuovo no-op", res.get("already_stopped") is True, res)
    check("nessun resume aggiuntivo", events == ["pause", "resume"], events)

    print()
    if _failures:
        print(f"  [FAIL] {len(_failures)} controlli falliti")
        return 1
    print("  [OK] TUTTI I CONTROLLI PASSATI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
