"""
Keyboard API - Keyboard matrix visualization and testing.

Provides keyboard device enumeration, matrix mapping, and live preview functionality.

Connection strategy
-------------------
OpenRGB may not be running when the app starts. All hardware-dependent
functions call _try_ensure_connected() as their first step. That helper:

  1. Returns immediately if _manager is already initialised.
  2. Pings the OpenRGB socket (1-second timeout).
  3. On success, delegates to settings_api._initialize_hardware() which
     creates a fresh UnifiedEffectManager and re-inits ALL API modules
     (effects, devices, keyboard) in one shot.
  4. Returns True/False so the caller can give the user a clear message.

This means the user can start OpenRGB *after* the web-app and simply
retry any keyboard operation — the reconnection is transparent.
"""
import eel
import json
import time
from typing import Optional, Dict, List, Tuple

from api.settings_api import with_openrgb_check

# Global references (set by init_keyboard_api, may be None until OpenRGB connects)
_manager = None
_client  = None


def init_keyboard_api(manager, client=None):
    """
    Store manager + client references.  Called at startup and again after
    every successful lazy reconnection via _try_ensure_connected().
    """
    global _manager, _client
    _manager = manager
    _client  = client

    if _manager:
        print("[OK] Keyboard API initialized (with hardware support)")
    else:
        print("[OK] Keyboard API initialized (no hardware - stub mode)")


# ── Single connection-check / auto-connect entry point ────────────────────

def _try_ensure_connected() -> bool:
    """
    Delegates to settings_api.try_ensure_openrgb() — the single canonical
    implementation of the lazy-connection logic for all API modules.
    """
    from api.settings_api import try_ensure_openrgb
    return try_ensure_openrgb()


# ========================================
# KEYBOARD DEVICE ENUMERATION
# ========================================

@eel.expose
@with_openrgb_check
def get_keyboard_devices():
    """
    Get list of keyboard devices with MATRIX topology only.

    Returns:
        dict: {
            'success': bool,
            'devices': [
                {
                    'id': int,
                    'name': str,
                    'type': 'keyboard',
                    'topology': 'MATRIX',
                    'led_count': int,
                    'dimensions': [rows, cols]
                },
                ...
            ],
            'count': int
        }
    """
    try:
        if not _try_ensure_connected():
            return {'success': False, 'error': 'OpenRGB not reachable', 'devices': [], 'count': 0}

        keyboards = []

        for i, device_ctrl in enumerate(_manager.devices):
            topology = device_ctrl.topology

            # Filter: Only MATRIX topology devices (keyboards)
            from effects.device_topology import TopologyType
            if topology.topology_type != TopologyType.MATRIX:
                continue

            # Only include devices that look like keyboards
            device_name_lower = topology.name.lower()
            if not ('keyboard' in device_name_lower or 'k70' in device_name_lower or
                   'k95' in device_name_lower or 'corsair' in device_name_lower):
                # Still include if it has MATRIX topology (might be a keyboard with unusual name)
                pass

            keyboard_info = {
                'id': i,
                'name': topology.name,
                'type': 'keyboard',
                'topology': 'MATRIX',
                'led_count': topology.led_count,
                'dimensions': list(topology.dimensions) if topology.dimensions else [0, 0]
            }

            keyboards.append(keyboard_info)

        return {
            'success': True,
            'devices': keyboards,
            'count': len(keyboards)
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to get keyboard devices: {str(e)}',
            'devices': [],
            'count': 0
        }


# ========================================
# KEYBOARD MATRIX RETRIEVAL
# ========================================

@eel.expose
@with_openrgb_check
def get_keyboard_matrix(device_id: int):
    """
    Get 2D LED matrix map for a keyboard device.

    Matrix map shows LED index at each position, or -1 (0xFFFFFFFF in OpenRGB) for empty cells.

    Args:
        device_id: Device index (0-based)

    Returns:
        dict: {
            'success': bool,
            'device_id': int,
            'device_name': str,
            'dimensions': {'rows': int, 'cols': int},
            'matrix_map': [[int, ...], ...],  # -1 = empty cell, 0+ = LED index
            'led_count': int
        }
    """
    try:
        if device_id < 0 or device_id >= len(_manager.devices):
            return {
                'success': False,
                'error': f'Invalid device_id: {device_id}. Valid range: 0-{len(_manager.devices)-1}'
            }

        device_ctrl = _manager.devices[device_id]
        topology = device_ctrl.topology

        # Verify it's a MATRIX device
        from effects.device_topology import TopologyType
        if topology.topology_type != TopologyType.MATRIX:
            return {
                'success': False,
                'error': f'Device {topology.name} is not a MATRIX device (topology: {topology.topology_type.name})'
            }

        if not topology.matrix_map:
            return {
                'success': False,
                'error': f'Device {topology.name} has no matrix map'
            }

        # Serialize matrix_map: Convert None -> -1 for JSON compatibility
        # OpenRGB uses 0xFFFFFFFF (4294967295) for empty cells, we use -1 for clarity
        serialized_matrix = []
        for row in topology.matrix_map:
            serialized_row = []
            for cell in row:
                if cell is None or cell == 0xFFFFFFFF:
                    serialized_row.append(-1)
                else:
                    serialized_row.append(cell)
            serialized_matrix.append(serialized_row)

        rows, cols = topology.dimensions

        # Include LED names from the device so the frontend can do name-based
        # key matching instead of fragile positional mapping.
        # Format: {led_index_str: "Key: Z"} — empty if device.leds unavailable.
        led_names = {}
        try:
            for i, led in enumerate(topology.device.leds):
                if hasattr(led, 'name') and led.name:
                    led_names[str(i)] = led.name
        except Exception:
            pass

        return {
            'success': True,
            'device_id': device_id,
            'device_name': topology.name,
            'dimensions': {'rows': rows, 'cols': cols},
            'matrix_map': serialized_matrix,
            'led_count': topology.led_count,
            'led_names': led_names
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to get keyboard matrix: {str(e)}'
        }


# ========================================
# LIVE PREVIEW & KEY CONTROL
# ========================================

@eel.expose
@with_openrgb_check
def get_led_names(device_id: int):
    """Return {led_index: led_name} for all LEDs on a device (debug)."""
    try:
        if not _try_ensure_connected():
            return {'success': False, 'error': 'OpenRGB not reachable'}
        if device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device_id: {device_id}'}
        device = _manager.devices[device_id].topology.device
        names = {i: led.name for i, led in enumerate(device.leds)}
        return {'success': True, 'names': names}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def set_key_color(device_id: int, led_index: int, color_hex: str):
    """
    Set color for a single key LED (for live preview mode).

    Args:
        device_id: Device index (0-based)
        led_index: LED index within device (0-based)
        color_hex: Color in hex format (e.g., "#FF0000" or "FF0000")

    Returns:
        dict: {'success': bool, 'error': str (optional)}
    """
    try:
        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device_id: {device_id}'}

        device_ctrl = _manager.devices[device_id]
        topology = device_ctrl.topology

        if led_index < 0 or led_index >= topology.led_count:
            return {'success': False, 'error': f'Invalid led_index: {led_index}. Valid range: 0-{topology.led_count-1}'}

        # Parse hex color
        color_hex = color_hex.lstrip('#')
        if len(color_hex) != 6:
            return {'success': False, 'error': f'Invalid color format: {color_hex}. Expected 6-digit hex (e.g., FF0000)'}

        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)

        # Set a single LED color by building a full colors array.
        # device.set_colors() is the standard OpenRGB approach and avoids
        # any quirks with device.leds[i].set_color() on specific hardware.
        from utils.openrgb_client import RGBColor
        device = topology.device
        led_count = topology.led_count
        try:
            colors = list(device.colors)
        except Exception:
            colors = []
        if len(colors) < led_count:
            colors = [RGBColor(0, 0, 0)] * led_count
        colors[led_index] = RGBColor(r, g, b)
        device.set_colors(colors)

        return {'success': True}

    except Exception as e:
        return {'success': False, 'error': f'Failed to set key color: {str(e)}'}


# ========================================
# GRADIENT PREVIEW
# ========================================

@eel.expose
@with_openrgb_check
def test_gradient_preview(device_id: int, start_color: str, end_color: str, direction: str):
    """
    Preview a gradient effect on the keyboard.

    Args:
        device_id: Device index (0-based)
        start_color: Start color in hex (e.g., "#FF0000")
        end_color: End color in hex (e.g., "#0000FF")
        direction: Gradient direction - "horizontal", "vertical", "diagonal", "radial"

    Returns:
        dict: {'success': bool, 'error': str (optional)}
    """
    try:
        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device_id: {device_id}'}

        device_ctrl = _manager.devices[device_id]

        # Verify MATRIX topology
        from effects.device_topology import TopologyType
        if device_ctrl.topology.topology_type != TopologyType.MATRIX:
            return {'success': False, 'error': 'Gradient preview only works on MATRIX keyboards'}

        # Parse colors
        def parse_color(hex_str):
            hex_str = hex_str.lstrip('#')
            if len(hex_str) != 6:
                raise ValueError(f'Invalid color: {hex_str}')
            return (
                int(hex_str[0:2], 16),
                int(hex_str[2:4], 16),
                int(hex_str[4:6], 16)
            )

        start_rgb = parse_color(start_color)
        end_rgb = parse_color(end_color)

        # Build gradient directly from the matrix topology
        from utils.openrgb_client import RGBColor

        topology = device_ctrl.topology
        led_count = topology.led_count
        matrix_map = topology.matrix_map      # list[list[int|None]]
        rows, cols = topology.dimensions      # (rows, cols) for MATRIX

        def lerp(c1, c2, t):
            return (
                int(c1[0] + (c2[0] - c1[0]) * t),
                int(c1[1] + (c2[1] - c1[1]) * t),
                int(c1[2] + (c2[2] - c1[2]) * t),
            )

        # Build per-LED color array initialised to black
        led_colors = [RGBColor(0, 0, 0)] * led_count

        for r in range(rows):
            for c in range(cols):
                led_idx = matrix_map[r][c]
                if led_idx is None or led_idx == 0xFFFFFFFF:
                    continue

                if direction == 'horizontal':
                    t = c / max(cols - 1, 1)
                elif direction == 'vertical':
                    t = r / max(rows - 1, 1)
                elif direction == 'diagonal':
                    t = (c + r) / max(cols + rows - 2, 1)
                else:  # radial
                    cx, cy = cols / 2.0, rows / 2.0
                    max_d = (cx ** 2 + cy ** 2) ** 0.5
                    t = min(((c - cx) ** 2 + (r - cy) ** 2) ** 0.5 / max(max_d, 1), 1.0)

                rgb = lerp(start_rgb, end_rgb, t)
                if led_idx < led_count:
                    led_colors[led_idx] = RGBColor(*rgb)

        topology.device.set_colors(led_colors)
        return {'success': True}

    except Exception as e:
        return {'success': False, 'error': f'Failed to preview gradient: {str(e)}'}


# ========================================
# KEYBOARD PRESETS
# ========================================

_PRESETS_FILE = 'config/keyboard_presets.json'


def _load_presets_data() -> dict:
    """Load keyboard_presets.json, returning default structure if missing."""
    try:
        with open(_PRESETS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            'active_preset': '1',
            'lock_keyboard': False,
            'presets': {
                '1': {'name': 'Preset 1', 'led_colors': {}},
                '2': {'name': 'Preset 2', 'led_colors': {}},
                '3': {'name': 'Preset 3', 'led_colors': {}},
            },
        }


def _save_presets_data(data: dict):
    """Persist keyboard_presets.json."""
    from pathlib import Path as _Path
    _Path(_PRESETS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(_PRESETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@eel.expose
def get_keyboard_presets():
    """
    Return all keyboard preset metadata (without full led_colors payload).

    Returns:
        dict: {
            'success': bool,
            'active_preset': str,       # '1', '2', or '3'
            'lock_keyboard': bool,
            'presets': {
                '1': {'name': str, 'has_data': bool},
                ...
            }
        }
    """
    try:
        data = _load_presets_data()
        presets_meta = {
            pid: {'name': p['name'], 'has_data': bool(p.get('led_colors'))}
            for pid, p in data.get('presets', {}).items()
        }
        return {
            'success': True,
            'active_preset': data.get('active_preset', '1'),
            'lock_keyboard': data.get('lock_keyboard', False),
            'presets': presets_meta,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def save_keyboard_preset(preset_id: str, led_colors: dict):
    """
    Save current keyboard colors to a preset slot.

    Args:
        preset_id: '1', '2', or '3'
        led_colors: {led_index_str: [r, g, b], ...}

    Returns:
        dict: {'success': bool, 'saved_leds': int}
    """
    try:
        data = _load_presets_data()
        if preset_id not in data.get('presets', {}):
            return {'success': False, 'error': f'Invalid preset_id: {preset_id}'}
        data['presets'][preset_id]['led_colors'] = led_colors
        _save_presets_data(data)
        print(f'[OK] Keyboard preset {preset_id} saved: {len(led_colors)} LEDs')
        return {'success': True, 'saved_leds': len(led_colors)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def load_keyboard_preset(preset_id: str):
    """
    Load a preset and apply its colors to the keyboard hardware.

    Args:
        preset_id: '1', '2', or '3'

    Returns:
        dict: {'success': bool, 'led_colors': dict, 'applied_leds': int}
    """
    try:
        data = _load_presets_data()
        if preset_id not in data.get('presets', {}):
            return {'success': False, 'error': f'Invalid preset_id: {preset_id}'}

        led_colors = data['presets'][preset_id].get('led_colors', {})

        # Try to connect to hardware; apply colors only if successful
        _try_ensure_connected()
        applied = 0
        if _manager:
            from effects.device_topology import TopologyType
            from utils.openrgb_client import RGBColor
            for device_ctrl in _manager.devices:
                if device_ctrl.topology.topology_type != TopologyType.MATRIX:
                    continue
                device = device_ctrl.topology.device
                led_count = device_ctrl.topology.led_count
                colors = list(device.colors) if hasattr(device, 'colors') and device.colors else [RGBColor(0, 0, 0)] * led_count
                if len(colors) < led_count:
                    colors += [RGBColor(0, 0, 0)] * (led_count - len(colors))

                # Build new color array: start from black, fill preset
                new_colors = [RGBColor(0, 0, 0)] * led_count
                for idx_str, rgb in led_colors.items():
                    idx = int(idx_str)
                    if 0 <= idx < led_count:
                        new_colors[idx] = RGBColor(*rgb)
                        applied += 1

                device.set_colors(new_colors)
                break  # Apply to first keyboard found

        return {'success': True, 'led_colors': led_colors, 'applied_leds': applied}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
def save_keyboard_default_config(active_preset: str, lock_keyboard: bool):
    """
    Persist the active preset selection and lock toggle for the Keyboard Default effect.

    Args:
        active_preset: '1', '2', or '3'
        lock_keyboard: True = other effects cannot override keyboard while this is active

    Returns:
        dict: {'success': bool}
    """
    try:
        data = _load_presets_data()
        data['active_preset'] = str(active_preset)
        data['lock_keyboard'] = bool(lock_keyboard)
        _save_presets_data(data)
        print(f'[OK] Keyboard Default config: preset={active_preset}, lock={lock_keyboard}')
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ========================================
# MATRIX EXPORT
# ========================================

@eel.expose
@with_openrgb_check
def fill_keyboard_preset(preset_id: str, color_hex: str):
    """
    Fill all keyboard LEDs in a preset with a single solid color.

    Enumerates every valid LED index from the first MATRIX device's matrix_map
    and saves them all with the specified color.  Requires OpenRGB to be connected
    so the matrix dimensions are known.

    Args:
        preset_id: '1', '2', or '3'
        color_hex: Color in hex format (e.g. '#FF0000' or 'FF0000')

    Returns:
        dict: {'success': bool, 'filled_leds': int, 'error': str}
    """
    try:
        if not _try_ensure_connected():
            return {'success': False, 'error': 'OpenRGB not reachable — cannot enumerate LED indices'}

        # Parse color
        h = color_hex.lstrip('#')
        if len(h) != 6:
            return {'success': False, 'error': f'Invalid color: {color_hex}'}
        rgb = [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)]

        # Find first MATRIX keyboard device
        from effects.device_topology import TopologyType
        keyboard_ctrl = next(
            (d for d in _manager.devices if d.topology.topology_type == TopologyType.MATRIX),
            None
        )
        if not keyboard_ctrl:
            return {'success': False, 'error': 'No MATRIX keyboard device found'}

        # Collect every valid LED index from the matrix_map
        matrix_map = keyboard_ctrl.topology.matrix_map
        led_colors = {}
        for row in matrix_map:
            for cell in row:
                if cell is not None and cell != 0xFFFFFFFF:
                    led_colors[str(cell)] = rgb

        if not led_colors:
            return {'success': False, 'error': 'No valid LEDs found in matrix'}

        # Save to preset
        data = _load_presets_data()
        if str(preset_id) not in data.get('presets', {}):
            return {'success': False, 'error': f'Invalid preset_id: {preset_id}'}

        data['presets'][str(preset_id)]['led_colors'] = led_colors
        _save_presets_data(data)

        n = len(led_colors)
        print(f'[OK] Preset {preset_id} filled with {color_hex} ({n} LEDs)')
        return {'success': True, 'filled_leds': n}

    except Exception as e:
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def export_matrix_json(device_id: int):
    """
    Export keyboard matrix as JSON data (for download).

    Args:
        device_id: Device index (0-based)

    Returns:
        dict: {
            'success': bool,
            'json_data': str,  # JSON string ready for download
            'filename': str    # Suggested filename
        }
    """
    try:
        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device_id: {device_id}'}

        device_ctrl = _manager.devices[device_id]
        topology = device_ctrl.topology

        # Get matrix data (reuse get_keyboard_matrix logic)
        matrix_result = get_keyboard_matrix(device_id)
        if not matrix_result['success']:
            return matrix_result

        # Build export data structure
        export_data = {
            'device_name': topology.name,
            'device_id': device_id,
            'topology': 'MATRIX',
            'dimensions': {
                'rows': topology.dimensions[0],
                'cols': topology.dimensions[1]
            },
            'led_count': topology.led_count,
            'matrix_map': matrix_result['matrix_map'],
            'metadata': {
                'exported_by': 'ED:Event2Led Keyboard Designer',
                'format_version': '1.0',
                'note': 'Matrix map: -1 = empty cell, 0+ = LED index'
            }
        }

        # Serialize to JSON string
        json_str = json.dumps(export_data, indent=2)

        # Suggest filename (sanitize device name)
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in topology.name)
        filename = f"{safe_name}_matrix.json"

        return {
            'success': True,
            'json_data': json_str,
            'filename': filename
        }

    except Exception as e:
        return {'success': False, 'error': f'Failed to export matrix: {str(e)}'}
