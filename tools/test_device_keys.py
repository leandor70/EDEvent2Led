"""
test_device_keys.py

Verifica lo schema unico di chiavi dei device (utils.device_keys) e la migrazione
dei file di configurazione (utils.device_key_migration):

  1. assign_keys / display_name: '#N' sui duplicati, indipendente dagli altri device
  2. migrazione sulla struttura reale: due RAM (::0, ::1) e una striscia con chiave
     legacy + ::6; l'indicizzata vince, device_id riscritti, copie per i duplicati
  3. migrazione: backup, marcatore, idempotenza, voce che non corrisponde, file illeggibile
  4. Linear1D: ogni device legge la propria topologia, nessun ripiego sul gemello
  5. UnifiedEffectManager._migrate_device_keys migra prima che i controller leggano

Device finti e cartella temporanea: non tocca config/ ne' l'hardware.
Output ASCII-safe (regola Windows-unicode-handling).
"""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from effects.device_topology import TopologyType  # noqa: E402
from effects.linear_1d import Linear1D  # noqa: E402
from utils import device_keys as dk  # noqa: E402
from utils.device_key_migration import migrate_device_keys, MARKER, SCHEME  # noqa: E402

_failures = []


def check(label, ok, detail=""):
    print(f"  {'[OK]' if ok else '[FAIL]'}  {label}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        _failures.append(label)


def quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = fn(*args, **kwargs)
    return out, buf.getvalue()


def zone(idx, name, n, device_id=None):
    z = {"zone_index": idx, "name": name, "led_count": n, "position": {"x": idx * 10, "y": 0}}
    if device_id:
        z["device_id"] = device_id
    return z


def topo(key, zones, tag):
    return {"device_id": key, "zones": zones, "zone_count": len(zones), "tag": tag}


def write(name, data):
    Path("config").mkdir(exist_ok=True)
    Path("config", name).write_text(json.dumps(data), encoding="utf-8")


def read(name):
    return json.loads(Path("config", name).read_text(encoding="utf-8"))


# Enumerazione come nella configurazione reale: 2 RAM, 4 altri device, striscia all'indice 6
DEVICES = [
    {"idx": 0, "name": "Corsair Dominator Platinum", "type": "linear"},
    {"idx": 1, "name": "Corsair Dominator Platinum", "type": "linear"},
    {"idx": 2, "name": "B450 AORUS PRO-CF", "type": "linear"},
    {"idx": 3, "name": "Logitech G933 Lightsync Headset", "type": "linear"},
    {"idx": 4, "name": "Tunable RGB Gaming Mouse G502", "type": "linear"},
    {"idx": 5, "name": "ASUS TUF K7", "type": "matrix"},
    {"idx": 6, "name": "LedStripScrivania", "type": "linear"},
]
for _d, _k in zip(DEVICES, dk.assign_keys((d["name"], d["type"]) for d in DEVICES)):
    _d["key"] = _k


def test_keys():
    print("\n1. assign_keys / display_name")
    keys = {d["idx"]: d["key"] for d in DEVICES}
    check("prima RAM: chiave nuda", keys[0] == "Corsair Dominator Platinum::linear", keys[0])
    check("seconda RAM: '#2'", keys[1] == "Corsair Dominator Platinum::linear#2", keys[1])
    check("device unici: chiave nuda", keys[6] == "LedStripScrivania::linear" and keys[5] == "ASUS TUF K7::matrix")

    shifted = dk.assign_keys([("X", "linear")] + [(d["name"], d["type"]) for d in DEVICES])
    check("un device in piu' in testa non cambia le chiavi dei duplicati",
          shifted[2] == "Corsair Dominator Platinum::linear#2" and shifted[7] == "LedStripScrivania::linear", shifted)
    check("stesso nome e tipo diverso: chiavi distinte e senza '#'",
          dk.assign_keys([("A", "linear"), ("A", "matrix")]) == ["A::linear", "A::matrix"])
    check("split_key", dk.split_key("A::linear#3") == ("A::linear", 3) and dk.split_key("A::linear") == ("A::linear", 1))

    ctrls = [NS(topology=NS(device=NS(name=d["name"]), topology_type=TopologyType.LINEAR if d["type"] == "linear"
                            else TopologyType.MATRIX), device_key=d["key"]) for d in DEVICES]
    check("display_name duplicati: 'Nome 1' / 'Nome 2'",
          dk.display_name(ctrls[0], ctrls) == "Corsair Dominator Platinum 1"
          and dk.display_name(ctrls[1], ctrls) == "Corsair Dominator Platinum 2")
    check("display_name unico: solo il nome", dk.display_name(ctrls[6], ctrls) == "LedStripScrivania")


def real_like_files():
    strip_zones_legacy = [zone(0, "Desktop", 16), zone(1, "MonitorRight", 5)]
    strip_zones_live = [zone(0, "Desktop", 16, "LedStripScrivania::linear::6"),
                        zone(1, "MonitorRight", 5, "LedStripScrivania::linear::6")]
    write("device_topologies.json", {
        "version": 1,
        "global_effect_center": {"x": 50, "y": 50},
        "topologies": {
            "LedStripScrivania::linear": topo("LedStripScrivania::linear", strip_zones_legacy, "legacy"),
            "Corsair Dominator Platinum::linear::0": topo("Corsair Dominator Platinum::linear::0",
                                                          [zone(0, "R", 12, "Corsair Dominator Platinum::linear::0")], "ram0"),
            "Corsair Dominator Platinum::linear::1": topo("Corsair Dominator Platinum::linear::1",
                                                          [zone(0, "R", 12, "Corsair Dominator Platinum::linear::1")], "ram1"),
            "LedStripScrivania::linear::6": topo("LedStripScrivania::linear::6", strip_zones_live, "live"),
        },
    })
    write("device_config.json", {"version": 1, "devices": {
        "Corsair Dominator Platinum::linear": {"enabled": True, "on_disable": "keep", "topology_editor": True},
        "LedStripScrivania::linear": {"enabled": True, "on_disable": "color", "topology_editor": True},
    }})
    write("ambilight_config.json", {"version": 1, "enabled": True, "devices": {
        "LedStripScrivania::linear": {"enabled": True}}})


def test_migration():
    print("\n2. migrazione sulla struttura reale")
    real_like_files()
    originals = {n: read(n) for n in ("device_topologies.json", "device_config.json", "ambilight_config.json")}
    res, out = quiet(migrate_device_keys, DEVICES)
    t = read("device_topologies.json")["topologies"]

    check("RAM 1: ::0 -> chiave nuda", t.get("Corsair Dominator Platinum::linear", {}).get("tag") == "ram0", list(t))
    check("RAM 2: ::1 -> '#2'", t.get("Corsair Dominator Platinum::linear#2", {}).get("tag") == "ram1", list(t))
    check("striscia: vince la topologia indicizzata (::6), non la copia legacy",
          t.get("LedStripScrivania::linear", {}).get("tag") == "live", t.get("LedStripScrivania::linear", {}).get("tag"))
    check("nessuna chiave '::N' rimasta", not any(k.rsplit("::", 1)[-1].isdigit() for k in t), list(t))
    check("device_id dell'entry e delle zone riscritti",
          t["Corsair Dominator Platinum::linear#2"]["device_id"] == "Corsair Dominator Platinum::linear#2"
          and t["Corsair Dominator Platinum::linear#2"]["zones"][0]["device_id"] == "Corsair Dominator Platinum::linear#2"
          and t["LedStripScrivania::linear"]["zones"][0]["device_id"] == "LedStripScrivania::linear")
    check("altri campi del file conservati", read("device_topologies.json")["global_effect_center"] == {"x": 50, "y": 50})

    dc = read("device_config.json")["devices"]
    check("device_config: la seconda RAM eredita le impostazioni",
          dc.get("Corsair Dominator Platinum::linear#2") == dc["Corsair Dominator Platinum::linear"], dc)
    check("device_config: la striscia non cambia", dc["LedStripScrivania::linear"]["on_disable"] == "color")
    am = read("ambilight_config.json")["devices"]
    check("ambilight_config: nessuna voce inventata", list(am) == ["LedStripScrivania::linear"], list(am))

    print("\n3. backup, marcatore, idempotenza")
    check("marcatore in tutti e tre i file",
          all(read(n).get(MARKER) == SCHEME for n in originals), [read(n).get(MARKER) for n in originals])
    check("backup delle topologie = contenuto originale",
          json.loads(Path("config/device_topologies.v1.bak.json").read_text(encoding="utf-8")) == originals["device_topologies.json"])
    check("backup di device_config creato", Path("config/device_config.v1.bak.json").exists())
    check("ambilight_config invariato nel contenuto: nessun backup", not Path("config/ambilight_config.v1.bak.json").exists())

    snapshot = {n: Path("config", n).read_text(encoding="utf-8") for n in originals}
    res2, out2 = quiet(migrate_device_keys, DEVICES)
    check("seconda esecuzione: nessuna nota, nulla da fare", all(v is None for v in res2.values()), res2)
    check("seconda esecuzione: file byte per byte identici",
          all(Path("config", n).read_text(encoding="utf-8") == snapshot[n] for n in originals))

    # Senza marcatore ma gia' migrato (file riscritto da un modulo che lo perde): idempotente
    for n in originals:
        d = read(n)
        d.pop(MARKER, None)
        write(n, d)
    before = {n: read(n) for n in originals}
    quiet(migrate_device_keys, DEVICES)
    after = {n: read(n) for n in originals}
    check("senza marcatore: stesso contenuto (a parte il marcatore)",
          all({k: v for k, v in after[n].items() if k != MARKER} == before[n] for n in originals))

    print("\n   voci che non si possono risolvere")
    write("device_topologies.json", {"topologies": {
        "ASUS TUF K7::linear::5": topo("x", [zone(0, "K", 10)], "wrongtype"),
        "Ghost::linear::40": topo("y", [zone(0, "G", 3)], "ghost"),
    }})
    Path("config/device_topologies.v1.bak.json").unlink()
    res3, out3 = quiet(migrate_device_keys, DEVICES)
    t = read("device_topologies.json")["topologies"]
    check("indice che punta a un altro device: voce lasciata com'e'", "ASUS TUF K7::linear::5" in t and "Ghost::linear::40" in t, list(t))
    check("... e segnalata", "left unchanged" in out3, out3)

    print("\n   file mancanti e illeggibili")
    for f in Path("config").glob("*.json"):
        f.unlink()
    res4, _ = quiet(migrate_device_keys, DEVICES)
    check("nessun file: nessun errore", all(v is None for v in res4.values()), res4)
    Path("config/device_topologies.json").write_text("{ not json", encoding="utf-8")
    res5, out5 = quiet(migrate_device_keys, DEVICES)
    check("JSON illeggibile: non solleva e non lo tocca",
          res5["device_topologies.json"] is None and Path("config/device_topologies.json").read_text() == "{ not json", out5)


def test_linear1d():
    print("\n4. Linear1D: ogni device legge la propria topologia")
    write("device_topologies.json", {"topologies": {
        "Ram::linear": topo("Ram::linear", [zone(0, "R", 12), zone(1, "S", 4)], "first"),
    }})
    dev = NS(name="Ram", leds=[object()] * 12)
    first, _ = quiet(Linear1D, dev, 12, 0, "Ram::linear")
    second, _ = quiet(Linear1D, dev, 12, 1, "Ram::linear#2")
    check("il primo device usa la propria topologia (2 zone)", len(first._zones) == 2, len(first._zones))
    check("il gemello senza topologia non eredita quella del primo (zona unica di ripiego)",
          len(second._zones) == 1 and second._topology is None, (len(second._zones), second._topology))
    check("senza device_key usa la chiave nuda '<nome>::linear'",
          len(quiet(Linear1D, dev, 12, 0)[0]._zones) == 2)


def test_manager_hook():
    print("\n5. UnifiedEffectManager._migrate_device_keys")
    from effects.unified_manager import UnifiedEffectManager
    real_like_files()
    detected = [(None, NS(device=NS(name=d["name"]),
                          topology_type=TopologyType.LINEAR if d["type"] == "linear" else TopologyType.MATRIX))
                for d in DEVICES]
    keys = dk.assign_keys((t.device.name, dk.type_name(t.topology_type)) for _, t in detected)
    quiet(UnifiedEffectManager._migrate_device_keys, detected, keys)
    t = read("device_topologies.json")["topologies"]
    check("il hook migra i file con le chiavi assegnate",
          "Corsair Dominator Platinum::linear#2" in t and read("device_topologies.json").get(MARKER) == SCHEME, list(t))
    _, out = quiet(UnifiedEffectManager._migrate_device_keys, [("broken",)], ["k"])
    check("un errore nel hook non si propaga", "migration failed" in out, out)


def main():
    print("=" * 70)
    print("  Test chiavi device e migrazione")
    print("=" * 70)
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            test_keys()
            test_migration()
            test_linear1d()
            test_manager_hook()
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
