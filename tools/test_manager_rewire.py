"""
Effect manager swap on (re)connection: settings_api._initialize_hardware().

Bug fixed: "Test connection", the automatic reconnection and the late first
connection create a new UnifiedEffectManager, but the ambilight service and the
event processor kept the manager built at startup. The ambilight asked the OLD
manager whether an effect was playing (always no) and wrote over the effects;
game events went to the old, disconnected client.

Fakes only: no OpenRGB, no hardware.
Run:  python tools/test_manager_rewire.py
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import api.ambilight_api as ambi_api        # noqa: E402
import api.keyboard_api as kbd              # noqa: E402
import api.monitoring_api as mon            # noqa: E402
import api.settings_api as sa               # noqa: E402
import effects.unified_manager as um        # noqa: E402
from effects.ambilight_service import AmbilightService  # noqa: E402

INIT_FUNCS = [("api.effects_api", "init_effects_api"), ("api.devices_api", "init_devices_api"),
              ("api.keyboard_api", "init_keyboard_api"), ("api.monitoring_api", "set_effect_manager"),
              ("api.bindings_api", "init_bindings_api"), ("api.device_config_api", "init_device_config_api"),
              ("api.topology_api", "init_topology_api")]


class FakeClient:
    def __init__(self, name):
        self.name = name
        self.disconnects = 0

    def disconnect(self):
        self.disconnects += 1


class FakeManager:
    fail = False
    seen_ambilight_manager = "unset"

    def __init__(self, client):
        # What the ambilight points to while the new manager initializes the LEDs
        FakeManager.seen_ambilight_manager = svc._effect_manager
        if FakeManager.fail:
            raise RuntimeError("init failed")
        self.client = client
        self.stops = 0

    def stop_all_effects(self):
        self.stops += 1


def check(cond, msg):
    print(f"  [{'OK' if cond else 'FAIL'}] {msg}")
    return bool(cond)


svc = AmbilightService(None)      # never started: no capture thread


def main() -> int:
    import importlib
    saved_init = {(m, f): getattr(importlib.import_module(m), f) for m, f in INIT_FUNCS}
    saved = (um.UnifiedEffectManager, sa._visual_library, kbd._manager, mon._event_processor,
             ambi_api._ambilight_service, ambi_api._effect_manager)
    ok = True
    try:
        um.UnifiedEffectManager = FakeManager
        sa._visual_library = object()
        for m, f in INIT_FUNCS:
            mod = importlib.import_module(m)
            if f == "init_keyboard_api":
                setattr(mod, f, lambda manager, client=None, _mod=mod: setattr(_mod, "_manager", manager))
            else:
                setattr(mod, f, lambda *a, **k: None)
        ambi_api.init_ambilight_api(svc, None)
        processor = types.SimpleNamespace(effect_manager=None)
        mon._event_processor = processor

        print("First connection (app started with OpenRGB off):")
        c1 = FakeClient("c1")
        sa._initialize_hardware(c1)
        m1 = kbd._manager
        ok &= check(isinstance(m1, FakeManager), "keyboard API got the new manager")
        ok &= check(svc._effect_manager is m1 and ambi_api._effect_manager is m1, "ambilight service and API follow it")
        ok &= check(processor.effect_manager is m1, "event processor follows it")

        print("Reconnection / Test connection:")
        svc._led_in_use["dev"] = {1, 2}
        c2 = FakeClient("c2")
        sa._initialize_hardware(c2)
        m2 = kbd._manager
        ok &= check(m2 is not m1, "a new manager was created")
        ok &= check(FakeManager.seen_ambilight_manager is None,
                    "ambilight detached while the new manager initializes the LEDs")
        ok &= check(m1.stops == 1, "old manager's effects stopped")
        ok &= check(svc._effect_manager is m2 and ambi_api._effect_manager is m2, "ambilight follows the new manager")
        ok &= check(svc._led_in_use == {}, "ambilight LED bookkeeping reset")
        ok &= check(processor.effect_manager is m2, "game events go to the new manager")
        ok &= check(c1.disconnects == 1 and c2.disconnects == 0, "old client closed, new one kept")

        print("New manager fails to initialize:")
        FakeManager.fail = True
        try:
            sa._initialize_hardware(FakeClient("c3"))
            ok &= check(False, "error propagated")
        except RuntimeError:
            ok &= check(True, "error propagated")
        FakeManager.fail = False
        ok &= check(svc._effect_manager is m2 and kbd._manager is m2, "previous manager put back")
        ok &= check(c2.disconnects == 0, "previous client left open")
    finally:
        for (m, f), fn in saved_init.items():
            setattr(importlib.import_module(m), f, fn)
        (um.UnifiedEffectManager, sa._visual_library, kbd._manager, mon._event_processor,
         ambi_api._ambilight_service, ambi_api._effect_manager) = saved

    print()
    print("  [OK] TUTTI I CONTROLLI PASSATI" if ok else "  [FAIL] ALCUNI CONTROLLI FALLITI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
