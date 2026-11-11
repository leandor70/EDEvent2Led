"""
topology_api.py
API for managing device topology configurations (multi-zone spatial layout)
"""

import eel
import json
import math
import threading
import time as _time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from utils.device_keys import device_key_of, display_name

# Configuration file path
TOPOLOGY_CONFIG_FILE = Path('config/device_topologies.json')

# Calibration animation thread state
_calib_thread: Optional[threading.Thread] = None
_calib_stop = threading.Event()
# True da quando la calibrazione ha messo in pausa l'ambilight fino allo stop.
# Distinto da _calib_thread: se la calibrazione fallisce dopo la pausa non c'e'
# nessun thread, ma l'ambilight va comunque ripreso.
_calib_active = False


def _calibration_loop(device_led_data: list, stop_event: threading.Event, blink_config: dict) -> None:
    """
    Background thread: animated concentric ring calibration.
    device_led_data: list of (device_ctrl, hw_idx, ring_idx, is_center)
    blink_config: {key: {blink: bool, period_ms: int}} for center/white/red/blue/green
    """
    RING_COLORS = [(255, 255, 255), (255, 60, 60), (80, 140, 255), (60, 210, 70)]
    COLOR_KEYS  = ['white', 'red', 'blue', 'green']

    by_device: Dict[Any, list] = {}
    for entry in device_led_data:
        by_device.setdefault(entry[0], []).append(entry)

    while not stop_event.is_set():
        t_ms = _time.monotonic() * 1000.0

        for ctrl, entries in by_device.items():
            color_map: Dict[int, tuple] = {}
            for _, hw_idx, ring_idx, is_center in entries:
                if is_center:
                    cfg = blink_config.get('center', {})
                    if cfg.get('blink', True):
                        period = max(100, cfg.get('period_ms', 333))
                        on = int(t_ms / (period / 2)) % 2 == 0
                        color = (255, 255, 255) if on else (0, 0, 0)
                    else:
                        color = (255, 255, 255)
                else:
                    key = COLOR_KEYS[ring_idx % 4]
                    cfg = blink_config.get(key, {})
                    base = RING_COLORS[ring_idx % 4]
                    if cfg.get('blink', False):
                        period = max(100, cfg.get('period_ms', 1000))
                        on = int(t_ms / (period / 2)) % 2 == 0
                        color = base if on else (0, 0, 0)
                    else:
                        color = base
                color_map[hw_idx] = color
            ctrl.controller.apply_color_map(color_map)

        stop_event.wait(0.05)  # ~20 fps


# Reference to UnifiedEffectManager (set by main.py)
_unified_manager = None


def _ensure_config_exists():
    """Create default topology config if doesn't exist"""
    if not TOPOLOGY_CONFIG_FILE.exists():
        TOPOLOGY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        default_config = {
            "version": 1,
            "topologies": {}
        }
        TOPOLOGY_CONFIG_FILE.write_text(
            json.dumps(default_config, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"[TopologyAPI] Created default config: {TOPOLOGY_CONFIG_FILE}")


def _load_topologies() -> dict:
    """Load all topology configurations"""
    _ensure_config_exists()
    try:
        with open(TOPOLOGY_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[TopologyAPI] Error loading topologies: {e}")
        return {"version": 1, "topologies": {}}


def _save_topologies(config: dict) -> bool:
    """Save topology configurations to disk"""
    try:
        with open(TOPOLOGY_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[TopologyAPI] Saved topologies to {TOPOLOGY_CONFIG_FILE}")
    except Exception as e:
        print(f"[TopologyAPI] Error saving topologies: {e}")
        return False
    _apply_saved_topologies()
    return True


def _apply_saved_topologies() -> None:
    """Make the running app use what was just written: the ambilight zone cache and
    the Linear1D controllers read device_topologies.json only once otherwise."""
    try:
        from api.ambilight_api import _ambilight_service
        if _ambilight_service is not None:
            _ambilight_service.refresh_all_zones()
    except Exception as e:
        print(f"[TopologyAPI] Could not refresh ambilight zones: {e}")
    try:
        from effects.device_topology import TopologyType
        for ctrl in (_unified_manager.devices if _unified_manager else []):
            if ctrl.topology.topology_type in (TopologyType.LINEAR, TopologyType.SINGLE):
                ctrl.controller._load_topology()
    except Exception as e:
        print(f"[TopologyAPI] Could not reload device controllers: {e}")


@eel.expose
def get_device_topology(device_id: str) -> dict:
    """
    Get topology configuration for a specific device

    Args:
        device_id: Device identifier (e.g., "LedStripScrivania::linear")

    Returns:
        {
            "success": bool,
            "device_id": str,
            "zones": List[dict],  # Zone configurations
            "error": str (optional)
        }
    """
    try:
        config = _load_topologies()
        topologies = config.get("topologies", {})

        # Exact device key only (utils.device_keys): no fallback to another device's entry
        if device_id not in topologies:
            return {
                "success": False,
                "device_id": device_id,
                "zones": [],
                "error": f"No topology configured for device: {device_id}"
            }
        topology = topologies[device_id]
        return {
            "success": True,
            "device_id": device_id,
            "zones": topology.get("zones", []),
            "effect_center": topology.get("effect_center", {"x": 50, "y": 50}),  # Default center if not set
            "last_modified": topology.get("last_modified", None)
        }

    except Exception as e:
        return {
            "success": False,
            "device_id": device_id,
            "zones": [],
            "error": str(e)
        }


@eel.expose
def save_device_topology(device_id: str, zones: List[dict], effect_center: Optional[dict] = None) -> dict:
    """
    Save topology configuration for a device

    Args:
        device_id: Device identifier
        zones: List of zone configurations [{
            "id": int,
            "name": str,
            "zone_index": int,
            "led_count": int,
            "position": {"x": float, "y": float},
            "rotation": int,  # degrees
            "direction": str  # "forward" | "reverse"
        }]
        effect_center: Optional global effect center {"x": float 0-100, "y": float 0-100}

    Returns:
        {
            "success": bool,
            "message": str,
            "error": str (optional)
        }
    """
    try:
        from datetime import datetime

        # Validate zones
        if not isinstance(zones, list):
            return {
                "success": False,
                "message": "Invalid zones data",
                "error": "zones must be a list"
            }

        # Validate effect_center if provided
        if effect_center is not None:
            if not isinstance(effect_center, dict) or "x" not in effect_center or "y" not in effect_center:
                effect_center = {"x": 50, "y": 50}  # Default if invalid

        # Load current config
        config = _load_topologies()
        topologies = config.get("topologies", {})

        # Preserve existing effect_center if not provided
        if effect_center is None and device_id in topologies:
            effect_center = topologies[device_id].get("effect_center", {"x": 50, "y": 50})
        elif effect_center is None:
            effect_center = {"x": 50, "y": 50}

        # Update topology for this device
        topologies[device_id] = {
            "device_id": device_id,
            "effect_center": effect_center,
            "zones": zones,
            "last_modified": datetime.now().isoformat(),
            "zone_count": len(zones),
            "total_leds": sum(z.get("led_count", 0) for z in zones)
        }

        config["topologies"] = topologies

        # Save to disk
        if _save_topologies(config):
            print(f"[TopologyAPI] Saved topology for {device_id}: {len(zones)} zones, "
                  f"{topologies[device_id]['total_leds']} total LEDs")
            return {
                "success": True,
                "message": f"Topology saved: {len(zones)} zones configured"
            }
        else:
            return {
                "success": False,
                "message": "Failed to save topology",
                "error": "File write error"
            }

    except Exception as e:
        return {
            "success": False,
            "message": "Error saving topology",
            "error": str(e)
        }


@eel.expose
def get_all_device_topologies() -> dict:
    """
    Get all configured device topologies

    Returns:
        {
            "success": bool,
            "topologies": {
                "device_id": {
                    "zones": [...],
                    "zone_count": int,
                    "total_leds": int,
                    "last_modified": str
                }
            }
        }
    """
    try:
        config = _load_topologies()
        return {
            "success": True,
            "topologies": config.get("topologies", {})
        }
    except Exception as e:
        return {
            "success": False,
            "topologies": {},
            "error": str(e)
        }


@eel.expose
def delete_device_topology(device_id: str) -> dict:
    """
    Delete topology configuration for a device

    Args:
        device_id: Device identifier

    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        config = _load_topologies()
        topologies = config.get("topologies", {})

        if device_id in topologies:
            del topologies[device_id]
            config["topologies"] = topologies

            if _save_topologies(config):
                return {
                    "success": True,
                    "message": f"Topology deleted for {device_id}"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to save after deletion"
                }
        else:
            return {
                "success": False,
                "message": f"No topology found for {device_id}"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting topology: {str(e)}"
        }


@eel.expose
def reset_device_topology(device_id: str) -> dict:
    """
    Reset topology to default layout (simple linear arrangement)

    Args:
        device_id: Device identifier

    Returns:
        {
            "success": bool,
            "zones": List[dict],
            "message": str
        }
    """
    try:
        # Create default linear layout
        # Note: In real implementation, this would query device zones from OpenRGB
        default_zones = [
            {
                "id": 0,
                "name": "Zone 1",
                "device_id": device_id,
                "zone_index": 0,
                "led_count": 10,
                "position": {"x": 5, "y": 5},
                "rotation": 0,
                "direction": "forward",
                "color": "#FF6600"
            }
        ]

        # Save default layout
        result = save_device_topology(device_id, default_zones)

        if result["success"]:
            return {
                "success": True,
                "zones": default_zones,
                "message": "Topology reset to default"
            }
        else:
            return {
                "success": False,
                "zones": [],
                "message": "Failed to reset topology",
                "error": result.get("error", "Unknown error")
            }

    except Exception as e:
        return {
            "success": False,
            "zones": [],
            "message": f"Error resetting topology: {str(e)}"
        }


def _read_openrgb_zones(device) -> list:
    """
    Zones (or segments, when a zone has them - E1.31/ARGB devices) as reported
    by the hardware.

    zone_index is a progressive counter over every zone/segment of the device,
    in hardware order: unique even when several zones have segments, and equal
    to the zone position for devices without segments.
    """
    zones = []
    for zone in device.zones:
        if hasattr(zone, 'segments') and len(zone.segments) > 0:
            for segment in zone.segments:
                idx = len(zones)
                zones.append({
                    "zone_index": idx,
                    "name": segment.name if hasattr(segment, 'name') else f"Segment {idx}",
                    "led_count": segment.leds_count if hasattr(segment, 'leds_count') else (len(segment.leds) if hasattr(segment, 'leds') else 0),
                    "start_index": segment.start_idx if hasattr(segment, 'start_idx') else 0
                })
        else:
            zones.append({
                "zone_index": len(zones),
                "name": zone.name,
                "led_count": len(zone.leds)
            })
    return zones


def _has_duplicate_indexes(zones: list) -> bool:
    indexes = [z.get("zone_index") for z in zones]
    return len(indexes) != len(set(indexes))


def _renumber_legacy_zones(zones: list) -> list:
    """
    Topologies saved with segments by older versions have repeated zone_index
    values (the segment counter restarted for every zone). The saved list is in
    hardware order, so renumber it by position. A list without repeated indexes
    is returned untouched.
    """
    if not _has_duplicate_indexes(zones):
        return zones
    print("[TopologyAPI] Repeated zone indexes found in saved topology - renumbered by position")
    return [{**z, "zone_index": i} for i, z in enumerate(zones)]


def _find_device_by_key(device_key: str):
    """The DeviceEffectController with this device key, or None."""
    if not _unified_manager:
        return None
    for ctrl in _unified_manager.devices:
        if device_key_of(ctrl) == device_key:
            return ctrl
    return None


def _load_device_flags() -> dict:
    """devices section of config/device_config.json (topology_editor flag etc.)."""
    path = Path('config/device_config.json')
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f).get('devices', {})
    except Exception as e:
        print(f"[TopologyAPI] Could not read device_config.json: {e}")
        return {}


def _diff_topology_with_hardware(saved_zones: list, hw_zones: list) -> list:
    """
    Structural differences between a saved topology and the hardware zones:
    zones added/removed and LED count changes. Zone names are NOT compared:
    the editor lets the user rename zones, a rename is not a divergence.
    """
    diff = []
    if _has_duplicate_indexes(saved_zones):
        diff.append("repeated zone indexes renumbered")
    saved = {z.get("zone_index"): z for z in _renumber_legacy_zones(saved_zones)}
    hw = {z["zone_index"]: z for z in hw_zones}
    for idx in sorted(saved.keys() | hw.keys(), key=lambda i: (i is None, i)):
        s, h = saved.get(idx), hw.get(idx)
        if s is None:
            diff.append(f"zone '{h['name']}' added")
        elif h is None:
            diff.append(f"zone '{s.get('name')}' removed")
        elif s.get("led_count") != h["led_count"]:
            diff.append(f"zone '{s.get('name')}' LEDs {s.get('led_count')}->{h['led_count']}")
    return diff


def sync_topologies_with_hardware() -> List[str]:
    """
    Make saved topologies agree with the hardware OpenRGB reports (hardware wins).

    Runs from init_topology_api, which is called at startup and after every
    OpenRGB (re)connection: the app only sees hardware changes when it
    enumerates devices, so this is the only check that is needed.

    Only LINEAR devices with topology_editor enabled that already have a
    topology are checked. A divergence (zone added/removed, LED count changed)
    is re-synced with reload_device_from_openrgb, keeping position, rotation,
    direction, spacing and the zone names chosen in the editor. Devices without
    a topology are left alone. The file is backed up before the first rewrite.

    Returns the topology keys that were rewritten.
    """
    changed: List[str] = []
    if not _unified_manager:
        return changed

    import shutil
    from effects.device_topology import TopologyType

    flags = _load_device_flags()
    known = _load_topologies().get("topologies", {})
    backed_up = False

    for device_ctrl in _unified_manager.devices:
        if device_ctrl.topology.topology_type != TopologyType.LINEAR:
            continue
        config_key = device_key_of(device_ctrl)
        if not flags.get(config_key, {}).get('topology_editor', False):
            continue

        existing = known.get(config_key)
        if existing is None:
            continue

        diff = _diff_topology_with_hardware(
            existing.get("zones", []), _read_openrgb_zones(device_ctrl.topology.device)
        )
        if not diff:
            continue

        if not backed_up:
            try:
                shutil.copy2(TOPOLOGY_CONFIG_FILE,
                             TOPOLOGY_CONFIG_FILE.with_name('device_topologies.sync.bak.json'))
            except Exception as e:
                print(f"[TopologyAPI] Could not back up topologies before sync: {e}")
            backed_up = True

        result = reload_device_from_openrgb(config_key, keep_names=True)
        if result.get("success"):
            changed.append(config_key)  # controllers and ambilight zones refreshed on save
            status = "re-synced"
        else:
            status = f"re-sync failed ({result.get('error')})"
        print(f"[TopologyAPI] '{config_key}' differs from hardware, {status}: " + "; ".join(diff))

    return changed


@eel.expose
def reload_device_from_openrgb(device_id: str, keep_names: bool = False) -> dict:
    """
    Reload zone configuration from OpenRGB hardware and update topology JSON.

    This synchronizes the saved topology with the current OpenRGB device configuration,
    updating LED counts for each zone.

    Args:
        device_id: Device identifier (e.g., "LedStripScrivania::linear")
        keep_names: Keep the saved zone names instead of the hardware ones
            (used by the automatic sync; the editor lets the user rename zones)

    Returns:
        {
            "success": bool,
            "device_id": str,
            "zones": List[dict],  # Updated zone configurations
            "changes": dict,  # Summary of changes detected
            "error": str (optional)
        }
    """
    try:
        # Lazy connection: Ensure OpenRGB is available
        from api.settings_api import try_ensure_openrgb
        if not try_ensure_openrgb():
            return {
                "success": False,
                "device_id": device_id,
                "error": "OpenRGB not available. Please ensure OpenRGB is running and try again."
            }

        # After try_ensure_openrgb, _unified_manager should be initialized
        global _unified_manager
        if not _unified_manager:
            return {
                "success": False,
                "device_id": device_id,
                "error": "UnifiedEffectManager not initialized after OpenRGB connection"
            }

        # Find the device in unified manager by its device key
        device_ctrl = _find_device_by_key(device_id)

        if not device_ctrl:
            return {
                "success": False,
                "device_id": device_id,
                "error": f"Device not found in UnifiedEffectManager: {device_id}"
            }

        device = device_ctrl.topology.device

        # Debug: log device info
        print(f"\n[TopologyAPI] === OpenRGB Device Structure Debug ===")
        print(f"Device: {device.name}")
        print(f"  Total LEDs: {len(device.leds)}")
        print(f"  Zone count: {len(device.zones)}")

        # Debug each zone in detail
        for zone_idx, zone in enumerate(device.zones):
            print(f"\n  Zone {zone_idx}: '{zone.name}'")
            print(f"    LED count: {len(zone.leds)}")
            print(f"    Zone type: {zone.type if hasattr(zone, 'type') else 'N/A'}")

            # *** CHECK FOR SEGMENTS! ***
            if hasattr(zone, 'segments'):
                print(f"    HAS SEGMENTS! Count: {len(zone.segments)}")
                for seg_idx, segment in enumerate(zone.segments):
                    print(f"      Segment {seg_idx}: {segment}")
                    if hasattr(segment, 'name'):
                        print(f"        Name: '{segment.name}'")
                    if hasattr(segment, 'leds'):
                        print(f"        LED count: {len(segment.leds)}")
                    if hasattr(segment, 'start_idx'):
                        print(f"        Start index: {segment.start_idx}")
            else:
                print(f"    No segments attribute found")

            # Check if zone has segments or named LEDs
            if hasattr(zone, 'leds') and len(zone.leds) > 0:
                # Sample first few LEDs to check for names
                sample_leds = zone.leds[:min(5, len(zone.leds))]
                for led_idx, led in enumerate(sample_leds):
                    if hasattr(led, 'name'):
                        print(f"      LED {led_idx}: name='{led.name}'")

                # Check if ALL LEDs have names (might be segments)
                if hasattr(zone.leds[0], 'name'):
                    all_led_names = [led.name for led in zone.leds]
                    print(f"    All LED names: {all_led_names[:20]}...")  # First 20

        print(f"[TopologyAPI] === End Debug ===\n")

        # Read current zone configuration from OpenRGB
        # IMPORTANT: Check for segments first (E1.31 devices)
        openrgb_zones = _read_openrgb_zones(device)

        # Load current topology JSON
        config = _load_topologies()
        topologies = config.get("topologies", {})

        # Find existing topology or create a new one
        existing_zones = topologies.get(device_id, {}).get("zones", [])
        existing_zones = _renumber_legacy_zones(existing_zones)

        # Color palette for visual distinction between zones
        ZONE_COLORS = [
            "#FF6600",  # Orange
            "#00FFFF",  # Cyan
            "#00FF00",  # Green
            "#FF00FF",  # Magenta
            "#FFFF00",  # Yellow
            "#FF0088",  # Pink
            "#00FF88",  # Mint
            "#8800FF",  # Purple
        ]

        # Update LED counts in existing zones, preserving spatial config
        updated_zones = []
        changes = {
            "led_count_changes": [],
            "new_zones": [],
            "removed_zones": []
        }

        for openrgb_zone in openrgb_zones:
            zone_idx = openrgb_zone["zone_index"]

            # Find matching zone in existing config
            existing_zone = None
            for ez in existing_zones:
                if ez.get("zone_index") == zone_idx:
                    existing_zone = ez
                    break

            if existing_zone:
                # Update LED count, preserve other config
                old_count = existing_zone.get("led_count", 0)
                new_count = openrgb_zone["led_count"]

                updated_zone = existing_zone.copy()
                updated_zone["led_count"] = new_count
                if not keep_names:
                    updated_zone["name"] = openrgb_zone["name"]  # Also update name
                updated_zone["color"] = ZONE_COLORS[zone_idx % len(ZONE_COLORS)]  # Update color from palette
                # Ensure all required rendering fields exist (may be missing in old saved configs)
                updated_zone.setdefault("position", {"x": 0, "y": zone_idx})
                updated_zone.setdefault("rotation", 0)
                updated_zone.setdefault("direction", "forward")
                updated_zone.setdefault("hasOverlap", False)
                updated_zone.setdefault("device_id", device_id)
                updated_zone.setdefault("id", zone_idx)
                updated_zone.setdefault("zone_index", zone_idx)

                if old_count != new_count:
                    changes["led_count_changes"].append({
                        "zone": openrgb_zone["name"],
                        "old": old_count,
                        "new": new_count
                    })

                updated_zones.append(updated_zone)
            else:
                # New zone detected
                new_zone = {
                    "id": zone_idx,
                    "name": openrgb_zone["name"],
                    "device_id": device_id,
                    "zone_index": zone_idx,
                    "led_count": openrgb_zone["led_count"],
                    "position": {"x": 0, "y": zone_idx},  # Default position
                    "rotation": 0,
                    "direction": "forward",
                    "color": ZONE_COLORS[zone_idx % len(ZONE_COLORS)],  # Cycle through color palette
                    "hasOverlap": False
                }
                updated_zones.append(new_zone)
                changes["new_zones"].append(openrgb_zone["name"])

        # Detect removed zones
        for ez in existing_zones:
            if ez.get("zone_index") not in [z["zone_index"] for z in openrgb_zones]:
                changes["removed_zones"].append(ez.get("name", f"Zone {ez.get('zone_index')}"))

        # Preserve existing effect_center when reloading zones
        existing_effect_center = {"x": 50, "y": 50}  # Default
        if device_id in topologies:
            existing_effect_center = topologies[device_id].get("effect_center", existing_effect_center)

        # Update topology in config
        topologies[device_id] = {
            "device_id": device_id,
            "effect_center": existing_effect_center,  # Preserve existing center
            "zones": updated_zones,
            "last_modified": datetime.now().isoformat(),
            "zone_count": len(updated_zones),
            "total_leds": sum(z["led_count"] for z in updated_zones)
        }
        config["topologies"] = topologies

        # Save updated config
        if not _save_topologies(config):
            return {
                "success": False,
                "device_id": device_id,
                "error": "Failed to save updated topology"
            }

        print(f"[TopologyAPI] Reloaded {device_id} from OpenRGB:")
        print(f"  - LED count changes: {len(changes['led_count_changes'])}")
        print(f"  - New zones: {len(changes['new_zones'])}")
        print(f"  - Removed zones: {len(changes['removed_zones'])}")

        return {
            "success": True,
            "device_id": device_id,
            "zones": updated_zones,
            "changes": changes,
            "message": f"Successfully reloaded {len(updated_zones)} zones from OpenRGB"
        }

    except Exception as e:
        import traceback
        print(f"[TopologyAPI] Error reloading from OpenRGB: {e}")
        print(traceback.format_exc())
        return {
            "success": False,
            "device_id": device_id,
            "error": str(e)
        }


@eel.expose
def flash_topology_device(device_id: str) -> dict:
    """
    Flash a topology device with a white pulse to help physically identify it.
    Bridges from topology device_id (string with ::N suffix) to devices_api.flash_device(int).
    """
    try:
        from api.settings_api import try_ensure_openrgb
        if not try_ensure_openrgb():
            return {'success': False, 'error': 'OpenRGB not available'}

        global _unified_manager
        if not _unified_manager:
            return {'success': False, 'error': 'Manager not initialized'}

        # devices_api.flash_device takes the position in the device list
        device_idx = next((i for i, ctrl in enumerate(_unified_manager.devices)
                           if device_key_of(ctrl) == device_id), None)
        if device_idx is None:
            return {'success': False, 'error': f'Device not found: {device_id}'}

        from api.devices_api import flash_device
        return flash_device(device_idx)

    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def get_topology_devices() -> dict:
    """
    Return all LINEAR devices that have topology_editor=True in device_config.json,
    with their current topology state (zone_count, has_topology).
    """
    try:
        from pathlib import Path as _Path
        import json as _json
        from effects.device_topology import TopologyType

        # Load device config flags
        device_config_path = _Path('config/device_config.json')
        device_cfg = {}
        if device_config_path.exists():
            with open(device_config_path, 'r', encoding='utf-8') as f:
                device_cfg = _json.load(f).get('devices', {})

        # Load saved topologies
        topologies = _load_topologies().get('topologies', {})

        if not _unified_manager:
            return {'success': False, 'error': 'Manager not initialized', 'devices': []}

        result = []
        for device_ctrl in _unified_manager.devices:
            if device_ctrl.topology.topology_type != TopologyType.LINEAR:
                continue
            # The device key is unique per device ('#N' on duplicate names)
            config_key = device_key_of(device_ctrl)
            if not device_cfg.get(config_key, {}).get('topology_editor', False):
                continue
            topo = topologies.get(config_key, {})
            result.append({
                'device_id': config_key,
                'name': display_name(device_ctrl, _unified_manager.devices),
                'led_count': device_ctrl.topology.led_count,
                'zone_count': topo.get('zone_count', 0),
                'has_topology': config_key in topologies,
            })

        return {'success': True, 'devices': result}
    except Exception as e:
        print(f"[TopologyAPI] get_topology_devices error: {e}")
        return {'success': False, 'error': str(e), 'devices': []}


# ── Screen rectangle ──────────────────────────────────────────────────────────
#
# Dove sta lo schermo nella scena (coordinate editor, y verso l'alto). Il lato
# dello schermo che un LED legge dipende da dove il LED e' disegnato rispetto a
# questo rettangolo, mai dal nome della zona. Vive in device_topologies.json come
# chiave di primo livello "screen_rect": gli effetti non la leggono.

_RECT_KEYS = ("x_min", "x_max", "y_min", "y_max")


def _screen_size():
    """(larghezza, altezza) dello schermo catturato dall'ambilight: l'ultimo frame,
    altrimenti il display primario secondo Windows. None se ignoto."""
    try:
        from api.ambilight_api import _ambilight_service
        size = getattr(_ambilight_service, "frame_size", None)
        if size and size[0] > 0 and size[1] > 0:
            return tuple(size)
    except Exception:
        pass
    try:
        import ctypes
        user32 = ctypes.windll.user32
        w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        return (w, h) if w > 0 and h > 0 else None
    except Exception:
        return None


def _ambilight_scene_keys():
    """Device accesi nell'ambilight (None = tutti): definiscono il riquadro automatico."""
    try:
        from api.ambilight_api import _ambilight_service
        return _ambilight_service._scene_keys() if _ambilight_service else None
    except Exception:
        return None


@eel.expose
def get_screen_rect() -> dict:
    """Dove sta lo schermo nella scena (coordinate editor, y su).

    mode: "manual" (c'e' un rettangolo salvato) oppure "auto" (nessuno: il riquadro
    dei LED dei device accesi, alle proporzioni dello schermo reale). `suggested`
    e' quel riquadro, il punto di partenza per l'editor ("Fit")."""
    from effects.ambilight_service import screen_frame, suggest_screen_rect
    data = _load_topologies()
    size = _screen_size()
    aspect = size[0] / size[1] if size else None
    keys = _ambilight_scene_keys()
    mode, _ = screen_frame(data, keys, aspect)
    return {
        "success":   True,
        "mode":      mode,
        "rect":      data.get("screen_rect") if mode == "manual" else None,
        "suggested": suggest_screen_rect(data, keys, aspect),
        "screen":    list(size) if size else None,     # [larghezza, altezza] dello schermo reale
        # Device i cui LED definiscono il riquadro automatico (None = tutti): l'editor
        # lo ricalcola dal vivo con lo stesso criterio.
        "scene_keys": sorted(keys) if keys else None,
    }


@eel.expose
def set_screen_rect(rect) -> dict:
    """Salva il rettangolo schermo (None lo rimuove: si torna all'automatico)."""
    try:
        data = _load_topologies()
        if rect is None:
            data.pop("screen_rect", None)
        else:
            clean = {k: float(rect[k]) for k in _RECT_KEYS}
            if clean["x_max"] <= clean["x_min"] or clean["y_max"] <= clean["y_min"]:
                return {"success": False, "error": "The rectangle has no area"}
            data["screen_rect"] = clean
        if not _save_topologies(data):
            return {"success": False, "error": "Could not write device_topologies.json"}
        return {"success": True}
    except (KeyError, TypeError, ValueError) as e:
        return {"success": False, "error": f"Invalid rectangle: {e}"}


@eel.expose
def get_scene_topology() -> dict:
    """
    Load all enabled LINEAR device zones for the unified scene editor.
    Returns all zones from all devices plus the global effect center.
    """
    try:
        config = _load_topologies()
        topologies = config.get("topologies", {})
        global_effect_center = config.get("global_effect_center", {"x": 50, "y": 50, "enabled": False})

        devices_result = get_topology_devices()
        if not devices_result['success']:
            return {'success': False, 'error': devices_result.get('error', 'Failed to list devices'), 'zones': [], 'devices': []}

        all_zones = []
        device_meta = []

        for dev in devices_result['devices']:
            device_id = dev['device_id']
            # Resolve topology (indexed key → base key fallback)
            topo = topologies.get(device_id, {})
            zones = topo.get('zones', [])

            default_color = '#FF6600'
            if zones:
                default_color = zones[0].get('color', default_color)

            for zone in zones:
                z = zone.copy()
                z['device_id'] = device_id   # ensure device_id is stamped on each zone
                all_zones.append(z)

            device_meta.append({
                'device_id': device_id,
                'name': dev['name'],
                'led_count': dev['led_count'],
                'zone_count': len(zones),
                'color': default_color,
            })

        return {
            'success': True,
            'zones': all_zones,
            'devices': device_meta,
            'global_effect_center': global_effect_center,
        }

    except Exception as e:
        print(f"[TopologyAPI] get_scene_topology error: {e}")
        return {'success': False, 'error': str(e), 'zones': [], 'devices': []}


@eel.expose
def save_scene_topology(zones: list, global_effect_center: dict) -> dict:
    """
    Save all device zones + global effect center in one call.
    zones: flat list where each zone has device_id stamped on it.
    global_effect_center: {x, y, enabled} percentages 0-100.
    """
    try:
        config = _load_topologies()
        topologies = config.get("topologies", {})

        # Group zones by device_id
        by_device: Dict[str, list] = {}
        for zone in zones:
            did = zone.get('device_id')
            if did:
                by_device.setdefault(did, []).append(zone)

        # Save each device's zones — always use the full indexed device_id as key
        for device_id, device_zones in by_device.items():
            target_key = device_id  # never fall back to base key: that would merge two devices into one

            if target_key not in topologies:
                topologies[target_key] = {'device_id': target_key}

            topologies[target_key]['zones'] = device_zones
            topologies[target_key]['zone_count'] = len(device_zones)
            topologies[target_key]['total_leds'] = sum(z.get('led_count', 0) for z in device_zones)
            topologies[target_key]['last_modified'] = datetime.now().isoformat()

        config['topologies'] = topologies
        config['global_effect_center'] = global_effect_center
        _save_topologies(config)

        total = sum(len(v) for v in by_device.values())
        print(f"[TopologyAPI] Scene saved: {total} zones across {len(by_device)} devices")
        return {'success': True, 'message': f'Scene saved: {total} zones across {len(by_device)} devices'}

    except Exception as e:
        print(f"[TopologyAPI] save_scene_topology error: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def reload_scene_from_openrgb() -> dict:
    """
    Reload zone LED counts from OpenRGB for ALL enabled LINEAR devices at once.
    Returns merged result with per-device change summaries.
    """
    try:
        devices_result = get_topology_devices()
        if not devices_result['success']:
            return {'success': False, 'error': devices_result.get('error', 'Failed to list devices'), 'zones': []}

        all_zones = []
        all_changes = {}

        for dev in devices_result['devices']:
            result = reload_device_from_openrgb(dev['device_id'])
            if result['success']:
                for zone in result.get('zones', []):
                    z = zone.copy()
                    z['device_id'] = dev['device_id']
                    all_zones.append(z)
                all_changes[dev['name']] = result.get('changes', {})
            else:
                print(f"[TopologyAPI] reload_scene: failed for {dev['device_id']}: {result.get('error')}")

        return {
            'success': True,
            'zones': all_zones,
            'changes': all_changes,
            'message': f'Reloaded {len(all_zones)} zones across {len(all_changes)} devices',
        }

    except Exception as e:
        print(f"[TopologyAPI] reload_scene_from_openrgb error: {e}")
        return {'success': False, 'error': str(e), 'zones': []}


def init_topology_api(unified_manager=None):
    """Initialize topology API module"""
    if unified_manager:
        global _unified_manager
        _unified_manager = unified_manager
        print("[TopologyAPI] Initialized with UnifiedEffectManager")

    _ensure_config_exists()
    try:
        sync_topologies_with_hardware()
    except Exception as e:
        # A sync problem must never prevent the app (or a reconnection) from starting
        print(f"[TopologyAPI] Topology sync with hardware failed: {e}")
    config = _load_topologies()
    topology_count = len(config.get("topologies", {}))
    print(f"[TopologyAPI] Initialized ({topology_count} device topologies configured)")


def _plan_led_data(plan: dict) -> list:
    """Map the editor's calibration plan to physical LEDs.

    plan = {zones: [{device_id, zone_index, led_count}],
            leds:  [{device_id, zone_index, led_index, ring, center}]}
    computed by the editor from what it draws (live zones, unsaved edits
    included). Here only the mapping to hardware happens: a zone's first LED is
    the sum of the LED counts of the device's zones with a lower zone_index, the
    same convention as the ambilight (build_device_zones).
    Returns [(device_ctrl, hw_idx, ring_idx, is_center)]."""
    ctrl_by_key = {device_key_of(d): d for d in _unified_manager.devices}

    offsets: Dict[tuple, int] = {}
    by_device: Dict[str, list] = {}
    for z in plan.get('zones', []):
        by_device.setdefault(z['device_id'], []).append(z)
    for dev_id, zones in by_device.items():
        off = 0
        for z in sorted(zones, key=lambda z: z['zone_index']):
            offsets[(dev_id, z['zone_index'])] = off
            off += int(z['led_count'])

    led_data = []
    for led in plan.get('leds', []):
        ctrl = ctrl_by_key.get(led['device_id'])
        off = offsets.get((led['device_id'], led['zone_index']))
        if ctrl is None or off is None:
            continue
        hw_idx = off + int(led['led_index'])
        if hw_idx >= ctrl.topology.led_count:
            continue   # the editor counts more LEDs than the device has
        led_data.append((ctrl, hw_idx, int(led['ring']), bool(led.get('center'))))
    return led_data


@eel.expose
def test_topology_calibration(effect_center: dict, ring_spacing: float, blink_config: dict = None,
                              plan: dict = None) -> dict:
    """
    Start animated concentric ring calibration on physical LED strips.
    blink_config: per-element {blink: bool, period_ms: int} for center/white/red/blue/green.
    plan: rings and center LED as the editor draws them (see _plan_led_data). When
        given, the LEDs show exactly the canvas; without it (old callers) rings are
        computed here from the SAVED topology of every linear device.
    Calling again restarts with new parameters (e.g. when center is dragged).
    """
    if blink_config is None:
        blink_config = {'center': {'blink': True, 'period_ms': 333}}
    global _calib_thread, _calib_stop, _calib_active

    from api.settings_api import try_ensure_openrgb
    try_ensure_openrgb()

    if not _unified_manager:
        return {'success': False, 'error': 'Manager not initialized'}

    # Pause Ambilight so it does not overwrite calibration colors
    _calib_active = True
    try:
        from api.ambilight_api import _ambilight_service
        if _ambilight_service is not None:
            _ambilight_service.pause()
    except Exception:
        pass

    # Stop any existing calibration thread before restarting
    _calib_stop.set()
    if _calib_thread and _calib_thread.is_alive():
        _calib_thread.join(timeout=0.3)

    if plan:
        try:
            led_data = _plan_led_data(plan)
            if not led_data:
                return {'success': False, 'error': 'No LED of the scene matches a connected device'}
            _calib_stop = threading.Event()
            _calib_thread = threading.Thread(
                target=_calibration_loop,
                args=(led_data, _calib_stop, blink_config),
                daemon=True,
                name='TopologyCalibration'
            )
            _calib_thread.start()
            return {'success': True, 'leds_colored': len(led_data)}
        except Exception as e:
            print(f"[TopologyAPI] test_topology_calibration (plan) error: {e}")
            return {'success': False, 'error': str(e)}

    try:
        from effects.device_topology import TopologyType
        from effects import topology_geometry as geo

        # Reload topology from disk for all linear devices before computing positions.
        # Linear1D caches zones in-memory at startup; without this reload, a topology
        # saved in the editor during the current session would not be reflected here.
        for device_ctrl in _unified_manager.devices:
            if device_ctrl.topology.topology_type == TopologyType.LINEAR:
                device_ctrl.controller._load_topology()

        # Collect all linear LED world positions + all zones.
        # Geometria unica (topology_geometry): la stessa che usano gli effetti
        # spaziali e l'ambilight, e che l'editor disegna (rotazione continua,
        # direction, centro del LED nel suo quadrato).
        device_leds = []   # (device_ctrl, hw_idx, wx, wy)
        all_zones = []     # tutte le zone della scena (per la bbox da corner)
        for device_ctrl in _unified_manager.devices:
            if device_ctrl.topology.topology_type != TopologyType.LINEAR:
                continue
            linear = device_ctrl.controller
            all_zones.extend(linear._zones)
            for hw_idx in range(device_ctrl.topology.led_count):
                zone_idx, local_idx = linear.get_zone_and_local_index(hw_idx)
                zone = linear._zones[zone_idx]
                wx, wy = geo.led_world_position(zone, local_idx)
                device_leds.append((device_ctrl, hw_idx, wx, wy))

        if not device_leds:
            return {'success': False, 'error': 'No linear topology devices with zones found'}

        # Global bbox dai CORNER delle zone — identica a calculateBoundingBox() del frontend
        min_x, max_x, min_y, max_y = geo.scene_bbox(all_zones)

        cx = min_x + (max_x - min_x) * (effect_center.get('x', 50) / 100.0)
        cy = min_y + (max_y - min_y) * (effect_center.get('y', 50) / 100.0)
        spacing = max(0.01, float(ring_spacing))

        # Find center LED: the single LED closest to (cx, cy) across all devices
        min_dist = float('inf')
        center_key = None
        for device_ctrl, hw_idx, wx, wy in device_leds:
            d = math.hypot(wx - cx, wy - cy)
            if d < min_dist:
                min_dist = d
                center_key = (device_ctrl, hw_idx)

        # Build (device_ctrl, hw_idx, ring_idx, is_center) list for the loop
        led_data = []
        for device_ctrl, hw_idx, wx, wy in device_leds:
            dist = math.hypot(wx - cx, wy - cy)
            ring_idx = int(dist / spacing)
            is_center = (device_ctrl, hw_idx) == center_key
            led_data.append((device_ctrl, hw_idx, ring_idx, is_center))

        _calib_stop = threading.Event()
        _calib_thread = threading.Thread(
            target=_calibration_loop,
            args=(led_data, _calib_stop, blink_config),
            daemon=True,
            name='TopologyCalibration'
        )
        _calib_thread.start()
        return {'success': True, 'leds_colored': len(device_leds)}

    except Exception as e:
        print(f"[TopologyAPI] test_topology_calibration error: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def stop_topology_calibration() -> dict:
    """Stop calibration thread and turn off LED strips.

    No-op if no calibration is active, so it is safe to call on every page
    leave / browser disconnect without stopping effects or resuming the
    ambilight during normal navigation."""
    global _calib_thread, _calib_stop, _calib_active
    if not _calib_active and _calib_thread is None:
        return {'success': True, 'already_stopped': True}
    _calib_active = False
    _calib_stop.set()
    if _calib_thread and _calib_thread.is_alive():
        _calib_thread.join(timeout=0.5)
    _calib_thread = None
    if _unified_manager:
        try:
            _unified_manager.stop_all_effects()
        except Exception:
            pass
    # Resume Ambilight now that calibration is over
    try:
        from api.ambilight_api import _ambilight_service
        if _ambilight_service is not None:
            _ambilight_service.resume()
    except Exception:
        pass
    return {'success': True}
