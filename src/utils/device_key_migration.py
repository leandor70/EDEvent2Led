"""
One-time migration of the per-device configuration to the key scheme of
utils.device_keys ("<name>::<type>", "#N" on duplicates).

What changes, per file (config/):

  device_topologies.json   "<name>::linear::<global index>"  ->  new device key.
                           The index is resolved against the devices detected
                           now; if the device at that index has another name or
                           type (the enumeration order changed) the entry is
                           left as it is and reported, never guessed. When a
                           legacy bare entry "<name>::linear" exists next to an
                           indexed one, the indexed one wins: it is the one the
                           topology editor kept writing to.
  device_config.json       devices with the same name used to share one entry;
  ambilight_config.json    every duplicate ("#2", "#3") gets a copy of it, so it
                           keeps the settings it had.

Safe to run on every start: a migrated file carries "device_keys": 2 and is
skipped, and every rule is idempotent anyway. The first time a file changes,
the old content is saved as "<file>.v1.bak.json" (never overwritten).
"""
import copy
import json
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from utils.device_keys import split_key

MARKER = "device_keys"
SCHEME = 2

_LEGACY_INDEXED = re.compile(r"^(?P<name>.+)::(?P<type>[a-z0-9]+)::(?P<idx>\d+)$")


def _retarget(entry: dict, key: str) -> dict:
    """Copy of a topology entry with device_id (entry and zones) set to the new key."""
    out = copy.deepcopy(entry)
    out["device_id"] = key
    for zone in out.get("zones", []):
        if isinstance(zone, dict) and "device_id" in zone:
            zone["device_id"] = key
    return out


def _migrate_topologies(data: dict, devices: List[dict]) -> Tuple[dict, List[str]]:
    notes: List[str] = []
    topos = data.get("topologies", {})
    by_idx = {d["idx"]: d for d in devices}

    # Pass 1: which indexed entries resolve to which new key
    resolved: Dict[str, str] = {}      # old key -> new key
    for key in topos:
        m = _LEGACY_INDEXED.match(key)
        if not m:
            continue
        dev = by_idx.get(int(m.group("idx")))
        if dev and dev["name"] == m.group("name") and dev["type"] == m.group("type"):
            resolved[key] = dev["key"]
        else:
            notes.append(f"'{key}' does not match the device now at that index: left unchanged")
    new_keys = set(resolved.values())

    # Pass 2: rebuild, keeping the original order
    new_topos: dict = {}
    for key, entry in topos.items():
        if key in resolved:
            new_key = resolved[key]
            new_topos[new_key] = _retarget(entry, new_key)
            if new_key != key:
                notes.append(f"'{key}' -> '{new_key}'")
        elif _LEGACY_INDEXED.match(key):
            new_topos[key] = entry                      # unresolved, left as is
        elif key in new_keys:
            notes.append(f"legacy entry '{key}' dropped: the indexed topology replaces it")
        else:
            new_topos[key] = entry
    data["topologies"] = new_topos
    return data, notes


def _copy_for_duplicates(data: dict, devices: List[dict]) -> Tuple[dict, List[str]]:
    notes: List[str] = []
    section = data.setdefault("devices", {})
    for dev in devices:
        base, ordinal = split_key(dev["key"])
        if ordinal > 1 and dev["key"] not in section and base in section:
            section[dev["key"]] = copy.deepcopy(section[base])
            notes.append(f"'{dev['key']}' inherits the settings of '{base}'")
    return data, notes


def _process(path: Path, transform: Callable[[dict], Tuple[dict, List[str]]]) -> Optional[List[str]]:
    """Migrate one file. Returns the notes, or None if skipped/failed."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[KeyMigration] Cannot read {path.name}: {e}")
        return None
    if not isinstance(data, dict) or data.get(MARKER) == SCHEME:
        return None

    before = json.dumps(data, sort_keys=True)
    new, notes = transform(copy.deepcopy(data))
    changed = json.dumps(new, sort_keys=True) != before

    try:
        if changed:
            backup = path.with_name(f"{path.stem}.v1.bak.json")
            if not backup.exists():
                backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        new[MARKER] = SCHEME
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(new, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
    except Exception as e:
        print(f"[KeyMigration] Cannot write {path.name}: {e}")
        return None

    for n in notes:
        print(f"[KeyMigration] {path.name}: {n}")
    return notes


def migrate_device_keys(devices: List[dict], config_dir: Path = Path("config")) -> Dict[str, Optional[List[str]]]:
    """
    devices: one dict per detected device, in OpenRGB order:
             {"idx": global index, "name": str, "type": "linear"/..., "key": new device key}
    Returns {file name: notes or None if skipped}. Never raises.
    """
    result: Dict[str, Optional[List[str]]] = {}
    steps = (
        ("device_topologies.json", lambda d: _migrate_topologies(d, devices)),
        ("device_config.json",     lambda d: _copy_for_duplicates(d, devices)),
        ("ambilight_config.json",  lambda d: _copy_for_duplicates(d, devices)),
    )
    for name, transform in steps:
        try:
            result[name] = _process(Path(config_dir) / name, transform)
        except Exception as e:
            print(f"[KeyMigration] {name} failed: {e}")
            result[name] = None
    return result
