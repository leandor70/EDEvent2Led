"""
Devices API - RGB device control and testing.

Provides device enumeration, flash testing, effect testing, and hardware mode activation.
"""
import eel
import threading
import time
from typing import Optional, Dict, List
from utils.openrgb_client import RGBColor

# Import safety utilities for robust OpenRGB operations
from utils.openrgb_safe import (
    safe_set_colors,
    safe_get_colors,
    create_color_array,
    check_device_mode_support,
    DeviceSafetyError
)

# Global references (initialized by init_devices_api)
_manager = None
_client = None


from api.settings_api import try_ensure_openrgb, with_openrgb_check
from utils.device_keys import device_key_of, display_name

# OpenRGB DeviceType name -> label used by the frontend (icons in devices.js)
_DEVICE_TYPE_LABELS = {'LEDSTRIP': 'strip'}


def init_devices_api(manager, client):
    """
    Initialize devices API with manager and OpenRGB client instances.

    Args:
        manager: UnifiedEffectManager instance (can be None if OpenRGB unavailable)
        client: OpenRGBClient instance (can be None if OpenRGB unavailable)
    """
    global _manager, _client
    _manager = manager
    _client = client

    if _manager and _client:
        print("[OK] Devices API initialized (with hardware support)")
    else:
        print("[OK] Devices API initialized (no hardware - stub mode)")


# ========================================
# DEVICE ENUMERATION
# ========================================

@eel.expose
@with_openrgb_check
def get_devices():
    """
    Get list of all RGB devices with topology information.

    Returns:
        dict: {
            'success': bool,
            'devices': [
                {
                    'id': int,
                    'name': str,
                    'type': str,  # 'keyboard', 'mouse', 'strip', 'headset', etc.
                    'topology': str,  # 'MATRIX', 'LINEAR', 'SINGLE', 'UNKNOWN'
                    'led_count': int,
                    'dimensions': [rows, cols] | None,  # Only for MATRIX topology
                    'enabled': bool
                },
                ...
            ],
            'count': int
        }
    """
    try:

        devices_data = []

        for i, device_ctrl in enumerate(_manager.devices):
            topology = device_ctrl.topology

            # Serialize topology type enum to string
            topology_str = topology.topology_type.name  # 'MATRIX', 'LINEAR', etc.

            # Device type as reported by OpenRGB (not guessed from the name)
            raw_type = getattr(getattr(topology.device, 'type', None), 'name', 'UNKNOWN')
            device_type = _DEVICE_TYPE_LABELS.get(raw_type, raw_type.lower())

            # Build device info
            config_key = device_key_of(device_ctrl)
            device_info = {
                'id': i,
                'name': display_name(device_ctrl, _manager.devices),
                'type': device_type,
                'topology': topology_str,
                'led_count': topology.led_count,
                'dimensions': list(topology.dimensions) if topology.dimensions else None,
                'enabled': True,  # Initial value; real state from device_config_api
                'config_key': config_key
            }

            devices_data.append(device_info)

        return {
            'success': True,
            'devices': devices_data,
            'count': len(devices_data)
        }

    except Exception as e:
        print(f"[ERROR] get_devices failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'devices': [],
            'count': 0
        }


# ========================================
# FLASH TESTING
# ========================================

# Pausa dell'ambilight durante i flash. Contatore e non booleano: flash_all_devices
# li lancia in sequenza e i ripristini (300ms) si sovrappongono al flash successivo;
# l'ambilight riprende solo quando l'ultimo flash e' finito.
_flash_lock = threading.Lock()
_flash_active = 0


def _ambilight_for_device(device_ctrl):
    """Ritorna l'AmbilightService se pilota questo device, altrimenti None."""
    try:
        from api.ambilight_api import _ambilight_service
        if _ambilight_service is None:
            return None
        if _ambilight_service.is_device_enabled(_manager._make_device_key(device_ctrl)):
            return _ambilight_service
    except Exception:
        pass
    return None


def _flash_hold(svc) -> None:
    global _flash_active
    with _flash_lock:
        if _flash_active == 0:
            svc.pause()
        _flash_active += 1


def _flash_release(svc) -> None:
    global _flash_active
    with _flash_lock:
        _flash_active -= 1
        if _flash_active == 0:
            svc.resume()


@eel.expose
@with_openrgb_check
def flash_device(device_id: int):
    """
    Flash device with quick white pulse (300ms).

    Args:
        device_id: Device index

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:

        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device ID: {device_id}'}

        device_ctrl = _manager.devices[device_id]
        device_name = device_ctrl.topology.name

        # Se l'ambilight pilota questo device, sospendilo per tutta la durata del
        # flash: altrimenti il frame successivo sovrascrive il bianco. Il
        # ripristino finale dei colori lo fa poi l'ambilight stesso.
        ambilight = _ambilight_for_device(device_ctrl)
        if ambilight is not None:
            _flash_hold(ambilight)
        restore_started = False

        try:
            # Save original colors (using safe getter with fallback)
            device = device_ctrl.topology.device
            original_colors = safe_get_colors(device, operation="flash_device:backup")

            # Create white color array (validated for correct LED count)
            led_count = device_ctrl.topology.led_count
            white_colors = create_color_array(255, 255, 255, led_count)

            # Set all LEDs to white (with type & count validation)
            safe_set_colors(device, white_colors, fast=True, operation="flash_device:white")

            # Schedule restore after 300ms
            def restore_colors():
                time.sleep(0.3)
                try:
                    safe_set_colors(device, original_colors, fast=True, operation="flash_device:restore")
                except DeviceSafetyError as e:
                    print(f"[ERROR] Flash restore validation failed: {e}")
                except Exception as e:
                    print(f"[ERROR] Flash restore failed: {e}")
                finally:
                    if ambilight is not None:
                        _flash_release(ambilight)

            # Run restore in background thread
            threading.Thread(target=restore_colors, daemon=True).start()
            restore_started = True
        finally:
            # Se il thread di ripristino non e' partito, nessuno rilascerebbe la pausa
            if ambilight is not None and not restore_started:
                _flash_release(ambilight)

        return {
            'success': True,
            'message': f'Flashed device: {device_name}'
        }

    except Exception as e:
        print(f"[ERROR] flash_device failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def flash_all_devices():
    """
    Flash all devices sequentially with 100ms delay between each.

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:

        def flash_sequence():
            for i in range(len(_manager.devices)):
                result = flash_device(i)
                if not result['success']:
                    print(f"[WARNING] Flash failed for device {i}: {result.get('error')}")
                time.sleep(0.15)  # 150ms delay between flashes

        # Run sequence in background thread
        threading.Thread(target=flash_sequence, daemon=True).start()

        return {
            'success': True,
            'message': f'Flashing {len(_manager.devices)} devices'
        }

    except Exception as e:
        print(f"[ERROR] flash_all_devices failed: {e}")
        return {'success': False, 'error': str(e)}


# ========================================
# STATIC COLOR CONTROL
# ========================================

@eel.expose
@with_openrgb_check
def set_static_color(device_id: int, color_hex: str, brightness: float = 1.0):
    """
    Set device to uniform static color.

    Args:
        device_id: Device index
        color_hex: Color as hex string (e.g., "#FF0000")
        brightness: Brightness multiplier 0.0-1.0

    Returns:
        dict: {'success': bool}
    """
    try:

        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device ID: {device_id}'}

        device_ctrl = _manager.devices[device_id]

        # Convert hex to RGB tuple
        color_hex = color_hex.lstrip('#')
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)

        # Apply brightness
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)

        # Create color array with validation
        led_count = device_ctrl.topology.led_count
        color_array = create_color_array(r, g, b, led_count)

        # Set all LEDs to this color with validation
        device = device_ctrl.topology.device
        safe_set_colors(device, color_array, fast=True, operation="set_static_color")

        return {'success': True}

    except DeviceSafetyError as e:
        print(f"[ERROR] set_static_color validation failed: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        print(f"[ERROR] set_static_color failed: {e}")
        return {'success': False, 'error': str(e)}


# ========================================
# EFFECT TESTING
# ========================================

@eel.expose
@with_openrgb_check
def test_effect(device_id: int, effect_name: str, duration_ms: int = 3000, params: Optional[Dict] = None):
    """
    Test spatial effect on single device.

    Args:
        device_id: Device index
        effect_name: Effect name ('ripple', 'wave', 'pulse', 'scanner', etc.)
        duration_ms: Effect duration in milliseconds
        params: Effect parameters dict (colors, speed, direction, etc.)

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device ID: {device_id}'}

        device_ctrl = _manager.devices[device_id]
        device = device_ctrl.topology.device

        # Verify Direct mode support before testing effects
        if not check_device_mode_support(device, "Direct"):
            error_msg = f"Device '{device.name}' does not support Direct mode (required for effects)"
            print(f"[WARNING] {error_msg}")
            return {'success': False, 'error': error_msg}

        # Default params if not provided
        if params is None:
            params = {}

        # Ensure colors are provided (default to blue -> cyan)
        if 'colors' not in params:
            params['colors'] = [(0, 100, 255), (0, 255, 255)]

        # Add duration_ms to params
        params['duration_ms'] = duration_ms

        # Apply effect via DeviceEffectController
        device_ctrl.apply_effect(effect_name, params, blocking=False)

        return {
            'success': True,
            'message': f'Testing {effect_name} on {device_ctrl.topology.name}'
        }

    except DeviceSafetyError as e:
        print(f"[ERROR] test_effect validation failed: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        print(f"[ERROR] test_effect failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def test_effect_all(effect_name: str, duration_ms: int = 3000, params: Optional[Dict] = None):
    """
    Test spatial effect on all devices simultaneously.

    Args:
        effect_name: Effect name
        duration_ms: Effect duration in milliseconds
        params: Effect parameters dict

    Returns:
        dict: {'success': bool, 'message': str, 'count': int}
    """
    try:
        if not try_ensure_openrgb():
            return {'success': False, 'error': 'OpenRGB not reachable', 'count': 0}

        success_count = 0

        for i in range(len(_manager.devices)):
            result = test_effect(i, effect_name, duration_ms, params)
            if result['success']:
                success_count += 1
            else:
                print(f"[WARNING] Effect failed on device {i}: {result.get('error')}")

        return {
            'success': True,
            'message': f'Testing {effect_name} on {success_count}/{len(_manager.devices)} devices',
            'count': success_count
        }

    except Exception as e:
        print(f"[ERROR] test_effect_all failed: {e}")
        return {'success': False, 'error': str(e), 'count': 0}


# ========================================
# HARDWARE MODE CONTROL
# ========================================

@eel.expose
@with_openrgb_check
def get_hardware_modes(device_id: int):
    """
    Get available hardware modes for device.

    Args:
        device_id: Device index

    Returns:
        dict: {
            'success': bool,
            'modes': [
                {
                    'index': int,
                    'name': str,
                    'has_speed': bool,
                    'has_colors': bool,
                    'has_direction': bool
                },
                ...
            ]
        }
    """
    try:
        if not try_ensure_openrgb():
            return {'success': False, 'error': 'OpenRGB not reachable', 'modes': []}

        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device ID: {device_id}', 'modes': []}

        device_ctrl = _manager.devices[device_id]
        device = device_ctrl.topology.device

        modes_data = []

        for i, mode in enumerate(device.modes):
            # Use speed_min/speed_max to detect speed support — mode.speed is never None
            # for modes without the HAS_SPEED flag (the client sets it to None).
            has_speed = getattr(mode, 'speed_min', None) is not None

            # color_mode: 0=None, 1=Per-LED, 2=Mode-Specific, 3=Random.
            # mode.colors is always a list (possibly empty), never None — cannot use `is not None`.
            color_mode = getattr(mode, 'color_mode', 0)
            has_colors = color_mode in (1, 2)  # Per-LED or Mode-Specific

            has_direction = getattr(mode, 'direction', None) is not None

            mode_info = {
                'index': i,
                'name': mode.name,
                'has_speed': has_speed,
                'has_colors': has_colors,
                'has_direction': has_direction,
                'color_mode': color_mode
            }
            modes_data.append(mode_info)

        return {
            'success': True,
            'modes': modes_data
        }

    except Exception as e:
        print(f"[ERROR] get_hardware_modes failed: {e}")
        return {'success': False, 'error': str(e), 'modes': []}


@eel.expose
@with_openrgb_check
def activate_hardware_mode(device_id: int, mode_index: int, speed: Optional[int] = None, colors: Optional[List[str]] = None):
    """
    Activate hardware mode on device.

    Args:
        device_id: Device index
        mode_index: Mode index from get_hardware_modes()
        speed: Mode speed (0-100) if mode supports it
        colors: List of color hex strings if mode supports colors

    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device ID: {device_id}'}

        device_ctrl = _manager.devices[device_id]
        device = device_ctrl.topology.device

        if mode_index < 0 or mode_index >= len(device.modes):
            return {'success': False, 'error': f'Invalid mode index: {mode_index}'}

        mode = device.modes[mode_index]

        # Activate the mode with default parameters (no speed/color control)
        # OpenRGB SDK doesn't reliably support modifying Mode objects
        # Users can configure speed/colors directly in OpenRGB GUI if needed
        device.set_mode(mode_index)

        return {
            'success': True,
            'message': f'Activated mode: {mode.name}'
        }

    except Exception as e:
        print(f"[ERROR] activate_hardware_mode failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def restore_direct_mode(device_id: int):
    """
    Restore device to Direct mode for software control.

    Args:
        device_id: Device index

    Returns:
        dict: {'success': bool}
    """
    try:
        if device_id < 0 or device_id >= len(_manager.devices):
            return {'success': False, 'error': f'Invalid device ID: {device_id}'}

        device_ctrl = _manager.devices[device_id]
        device = device_ctrl.topology.device

        # Find Direct mode
        direct_mode_index = None
        for i, mode in enumerate(device.modes):
            if 'direct' in mode.name.lower():
                direct_mode_index = i
                break

        if direct_mode_index is None:
            return {'success': False, 'error': 'Direct mode not found on this device'}

        device.set_mode(direct_mode_index)

        # Clear all LEDs to black after switching to Direct mode
        # to prevent white/previous color artifacts
        try:
            led_count = len(device.leds)
            black_colors = [(0, 0, 0)] * led_count
            device.set_colors(black_colors, fast=True)
        except Exception as clear_err:
            print(f"[WARNING] Could not clear {device.name} LEDs: {clear_err}")

        return {'success': True}

    except Exception as e:
        print(f"[ERROR] restore_direct_mode failed: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
def toggle_device_enabled(device_id: int, enabled: bool):
    """
    Enable/disable device (placeholder for future implementation).

    Args:
        device_id: Device index
        enabled: Whether device should be enabled

    Returns:
        dict: {'success': bool}
    """
    try:
        # For now, this is a stub - we don't actually disable devices
        # In the future, this could be used to filter devices from effect playback
        return {
            'success': True,
            'message': f'Device {"enabled" if enabled else "disabled"} (stub)'
        }

    except Exception as e:
        print(f"[ERROR] toggle_device_enabled failed: {e}")
        return {'success': False, 'error': str(e)}
