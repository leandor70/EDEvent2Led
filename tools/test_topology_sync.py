"""
test_topology_sync.py

Verifica il sync topologia/hardware (topology_api.sync_topologies_with_hardware),
eseguito da init_topology_api a ogni avvio e riconnessione:

  1. topologia coerente: nessuna modifica, nessun backup
  2. LED cambiati: ri-sincronizza, conserva posizione e nome scelto nell'editor, backup
  3. zona aggiunta / rimossa: rilevata
  4. device senza flag topology_editor, o senza topologia: non toccato
  5. due device omonimi (Ram::linear e Ram::linear#2): si riscrive solo quello divergente
  6. nessun ripiego sulla topologia di un altro device
  7. init_topology_api: esegue il sync e non propaga eccezioni
  8. AmbilightService._validate_topology: un solo avviso per device

Device finti e cartella temporanea: non tocca config/ ne' l'hardware.
Output ASCII-safe (regola Windows-unicode-handling).
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import types
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from api import topology_api as tapi  # noqa: E402
from effects.ambilight_service import AmbilightService  # noqa: E402

_failures = []


def check(label, ok, detail=""):
    print(f"  {'[OK]' if ok else '[FAIL]'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        _failures.append(label)


def quiet(fn, *args, **kwargs):
    """Esegue fn zittendo la stampa di debug di reload_device_from_openrgb."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*args, **kwargs)
    return out, buf.getvalue()


def hw_device(name, zone_sizes):
    zones = [NS(name=f"Z{i}", leds=[object()] * n) for i, n in enumerate(zone_sizes)]
    return NS(name=name, zones=zones, leds=[object()] * sum(zone_sizes))


def make_ctrl(name, zone_sizes, key=None):
    reloaded = []
    dev = hw_device(name, zone_sizes)
    ctrl = NS(topology=NS(device=dev, topology_type=tapi_linear(), led_count=len(dev.leds)),
              controller=NS(_load_topology=lambda: reloaded.append(1)), reloaded=reloaded,
              device_key=key or f"{name}::linear")
    return ctrl


def tapi_linear():
    from effects.device_topology import TopologyType
    return TopologyType.LINEAR


def zone(idx, name, n, x=0):
    return {"zone_index": idx, "name": name, "led_count": n, "position": {"x": x, "y": 0},
            "rotation": 0, "direction": "forward"}


def topo(zones):
    return {"zones": zones, "zone_count": len(zones), "total_leds": sum(z["led_count"] for z in zones)}


def setup(devices, topologies, flags):
    Path("config").mkdir(exist_ok=True)
    Path("config/device_topologies.json").write_text(
        json.dumps({"version": 1, "topologies": topologies}), encoding="utf-8")
    Path("config/device_config.json").write_text(json.dumps({"devices": flags}), encoding="utf-8")
    for f in Path("config").glob("*.bak.json"):
        f.unlink()
    tapi._unified_manager = NS(devices=devices)


def saved():
    return json.loads(Path("config/device_topologies.json").read_text(encoding="utf-8"))["topologies"]


def backup_exists():
    return Path("config/device_topologies.sync.bak.json").exists()


FLAG = {"topology_editor": True}


def main():
    print("=" * 70)
    print("  Test sync topologia/hardware")
    print("=" * 70)

    fake_settings = types.ModuleType("api.settings_api")
    fake_settings.try_ensure_openrgb = lambda: True
    sys.modules["api.settings_api"] = fake_settings

    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            print("\n1. topologia coerente")
            c = make_ctrl("Strip", [10, 5])
            setup([c], {"Strip::linear": topo([zone(0, "A", 10), zone(1, "B", 5)])}, {"Strip::linear": FLAG})
            changed, _ = quiet(tapi.sync_topologies_with_hardware)
            check("nessuna modifica", changed == [], changed)
            check("nessun backup", not backup_exists())

            print("\n2. LED cambiati (10 -> 15), zona rinominata dall'utente")
            c = make_ctrl("Strip", [15, 5])
            setup([c], {"Strip::linear": topo([zone(0, "MonitorRight", 10, x=42), zone(1, "B", 5)])},
                  {"Strip::linear": FLAG})
            changed, _ = quiet(tapi.sync_topologies_with_hardware)
            z = saved()["Strip::linear"]["zones"]
            check("riscritta", changed == ["Strip::linear"], changed)
            check("led_count aggiornato a 15", z[0]["led_count"] == 15, z[0])
            check("nome scelto nell'editor conservato", z[0]["name"] == "MonitorRight", z[0]["name"])
            check("posizione conservata", z[0]["position"]["x"] == 42, z[0]["position"])
            check("backup creato", backup_exists())
            check("controller ricarica la topologia", c.reloaded == [1], c.reloaded)

            print("\n3. zona aggiunta / rimossa")
            c = make_ctrl("Strip", [10, 5, 3])
            setup([c], {"Strip::linear": topo([zone(0, "A", 10), zone(1, "B", 5)])}, {"Strip::linear": FLAG})
            changed, _ = quiet(tapi.sync_topologies_with_hardware)
            check("zona aggiunta: 3 zone salvate", len(saved()["Strip::linear"]["zones"]) == 3 and changed)
            c = make_ctrl("Strip", [10])
            setup([c], {"Strip::linear": topo([zone(0, "A", 10), zone(1, "B", 5)])}, {"Strip::linear": FLAG})
            changed, _ = quiet(tapi.sync_topologies_with_hardware)
            check("zona rimossa: 1 zona salvata", len(saved()["Strip::linear"]["zones"]) == 1 and changed)

            print("\n4. device senza flag / senza topologia")
            c = make_ctrl("Strip", [15, 5])
            setup([c], {"Strip::linear": topo([zone(0, "A", 10), zone(1, "B", 5)])}, {"Strip::linear": {}})
            changed, _ = quiet(tapi.sync_topologies_with_hardware)
            check("senza topology_editor: non toccato", changed == [] and saved()["Strip::linear"]["zones"][0]["led_count"] == 10)
            setup([c], {}, {"Strip::linear": FLAG})
            changed, _ = quiet(tapi.sync_topologies_with_hardware)
            check("senza topologia: nessuna creazione", changed == [] and saved() == {}, saved())

            print("\n5. due device omonimi (Ram::linear e Ram::linear#2), diverge solo il secondo")
            c0, c1 = make_ctrl("Ram", [12]), make_ctrl("Ram", [16], key="Ram::linear#2")
            setup([c0, c1], {"Ram::linear": topo([zone(0, "R", 12)]), "Ram::linear#2": topo([zone(0, "R", 12)])},
                  {"Ram::linear": FLAG, "Ram::linear#2": FLAG})
            changed, _ = quiet(tapi.sync_topologies_with_hardware)
            s = saved()
            check("riscritto solo Ram::linear#2", changed == ["Ram::linear#2"], changed)
            check("il primo resta a 12, il secondo passa a 16", s["Ram::linear"]["zones"][0]["led_count"] == 12
                  and s["Ram::linear#2"]["zones"][0]["led_count"] == 16)

            print("\n6. nessun ripiego sulla topologia di un altro device")
            c0, c1 = make_ctrl("Ram", [12]), make_ctrl("Ram", [16], key="Ram::linear#2")
            setup([c0, c1], {"Ram::linear": topo([zone(0, "R", 12)])},
                  {"Ram::linear": FLAG, "Ram::linear#2": FLAG})
            changed, _ = quiet(tapi.sync_topologies_with_hardware)
            check("il secondo device senza topologia non eredita quella del primo",
                  changed == [] and "Ram::linear#2" not in saved(), (changed, list(saved())))

            print("\n7. init_topology_api")
            c = make_ctrl("Strip", [15])
            setup([c], {"Strip::linear": topo([zone(0, "A", 10)])}, {"Strip::linear": FLAG})
            manager = NS(devices=[c])
            quiet(tapi.init_topology_api, manager)
            check("esegue il sync", saved()["Strip::linear"]["zones"][0]["led_count"] == 15)
            broken = NS(devices=[NS(topology=None)])
            try:
                _, out = quiet(tapi.init_topology_api, broken)
                check("eccezione del sync non propagata", "sync with hardware failed" in out, out)
            except Exception as exc:  # pragma: no cover
                check("eccezione del sync non propagata", False, repr(exc))

            print("\n8. AmbilightService._validate_topology")
            mgr = NS(devices=[c], _make_device_key=lambda ctrl: "Strip::linear")
            svc = AmbilightService(mgr)
            _, out1 = quiet(svc._validate_topology, "Strip::linear", 99)
            _, out2 = quiet(svc._validate_topology, "Strip::linear", 99)
            check("avviso al primo controllo", "Topology mismatch" in out1, out1)
            check("nessun secondo avviso", out2 == "", out2)
            _, out3 = quiet(svc._validate_topology, "Altro::linear", 99)
            check("device sconosciuto: nessun avviso", out3 == "", out3)
            svc.refresh_zones("Strip::linear")
            _, out4 = quiet(svc._validate_topology, "Strip::linear", 99)
            check("dopo refresh_zones l'avviso puo' ripetersi", "Topology mismatch" in out4, out4)
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
