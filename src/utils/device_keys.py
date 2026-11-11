"""
Device keys for ED:Event2Led.

One key scheme for everything that is stored per device (device_config.json,
ambilight_config.json, device_topologies.json, disabled devices, the topology
editor):

    "<DeviceName>::<type>"        first device with that name and type
    "<DeviceName>::<type>#2"      second one, "#3" the third, ...

<type> is the lowercase TopologyType name (matrix / linear / single). The
suffix depends only on the order among devices that share name AND type, not
on the position of the device in the whole list, so adding an unrelated device
does not move a saved configuration to another device.

Before this scheme the topology editor used "<name>::linear::<global index>"
(see device_key_migration.py).
"""
import re
from typing import Iterable, List, Tuple

_KEY_RE = re.compile(r"^(?P<base>.+::[a-z0-9]+)(?:#(?P<ordinal>\d+))?$")


def type_name(topology_type) -> str:
    """'matrix' / 'linear' / 'single' from a TopologyType (or an already lowercase str)."""
    name = getattr(topology_type, "name", topology_type)
    return str(name).lower()


def base_key(device_name: str, ttype: str) -> str:
    return f"{device_name}::{ttype}"


def assign_keys(entries: Iterable[Tuple[str, str]]) -> List[str]:
    """Keys for a list of (device_name, type) in device order: '#N' on duplicates."""
    seen: dict = {}
    keys = []
    for name, ttype in entries:
        base = base_key(name, ttype)
        n = seen.get(base, 0) + 1
        seen[base] = n
        keys.append(base if n == 1 else f"{base}#{n}")
    return keys


def device_key_of(device_ctrl) -> str:
    """Key of a DeviceEffectController (falls back to the bare key if none was assigned)."""
    key = getattr(device_ctrl, "device_key", None)
    if key:
        return key
    return base_key(device_ctrl.topology.device.name, type_name(device_ctrl.topology.topology_type))


def split_key(key: str) -> Tuple[str, int]:
    """('<name>::<type>', ordinal) with ordinal 1 for the bare key."""
    m = _KEY_RE.match(key)
    if not m:
        return key, 1
    return m.group("base"), int(m.group("ordinal") or 1)


def display_name(device_ctrl, devices) -> str:
    """Name for the UI: 'Name' if unique, 'Name 1', 'Name 2', ... when several devices share it."""
    key = device_key_of(device_ctrl)
    base, ordinal = split_key(key)
    siblings = sum(1 for d in devices if split_key(device_key_of(d))[0] == base)
    name = device_ctrl.topology.device.name
    return f"{name} {ordinal}" if siblings > 1 else name
