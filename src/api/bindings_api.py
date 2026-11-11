"""
Bindings API — Elite Dangerous keybinding color profile.

Exposes:
  browse_bindings_file()       — opens native OS file dialog, returns selected path
  get_keybind_categories()     — parses .binds file, returns key→category map
  apply_keyboard_profile(data) — sends a {led_index: "#RRGGBB"} map to hardware
  clear_keyboard_profile()     — turns off keyboard LEDs
"""

import eel
from typing import Optional

_manager  = None   # UnifiedEffectManager (may be None if OpenRGB offline)
_settings = None   # Settings (for custom bindings path if configured)


from api.settings_api import try_ensure_openrgb, with_openrgb_check, _get_browser_hwnd, _native_file_dialog


def init_bindings_api(settings, manager=None):
    global _manager, _settings
    _settings = settings
    _manager  = manager
    print("[OK] Bindings API initialized")


# ── Default path ─────────────────────────────────────────────────────────

@eel.expose
def get_default_bindings_path():
    """
    Return the expected default path for Custom.3.0.binds without reading it.
    Used to pre-populate the path input so the user knows where we look.

    Returns:
        str — full path (may not exist yet if ED was never launched)
    """
    from journal.bindings_reader import BindingsReader
    reader = BindingsReader()
    # Try to find an existing file first
    found = reader.find_bindings_file()
    if found:
        return str(found)
    # Otherwise return the conventional path for the current latest version
    from pathlib import Path
    import os
    return str(
        Path(os.environ.get('LOCALAPPDATA', '')) /
        'Frontier Developments' / 'Elite Dangerous' /
        'Options' / 'Bindings' / 'Custom.4.2.binds'
    )


# ── File browser ─────────────────────────────────────────────────────────

@eel.expose
def browse_bindings_file():
    """
    Open a native Windows file picker for .binds files via Win32 GetOpenFileNameW.

    Uses ctypes directly (no PowerShell, no subprocess) so the gevent hub
    stays responsive and the dialog appears owned by the browser window.

    Returns:
        str | None  — absolute path to selected .binds file, or None if cancelled
    """
    try:
        from journal.bindings_reader import BindingsReader

        # Sensible starting directory (first existing search path)
        initial_dir = ""
        for p in BindingsReader._SEARCH_PATHS:
            if p.exists():
                initial_dir = str(p)
                break

        path = _native_file_dialog(
            parent_hwnd=_get_browser_hwnd(),
            title="Select Elite Dangerous keybindings file",
            initial_dir=initial_dir,
            filter_pairs=[
                ("Bindings files (*.binds)", "*.binds"),
                ("All files (*.*)",          "*.*"),
            ],
            default_ext="binds",
        )
        return path if path else None

    except Exception as e:
        print(f"[ERROR] browse_bindings_file: {e}")
        return None


# ── Read keybindings ──────────────────────────────────────────────────────

@eel.expose
def get_keybind_categories(file_path: Optional[str] = None):
    """
    Parse the Elite Dangerous .binds file and return a key→category map.

    Args:
        file_path: Optional explicit path. If None, auto-detects the
                   standard Custom.3.0.binds location.

    Returns:
        {
            'success':    bool,
            'file_path':  str,
            'categories': { display_key: category },   e.g. { 'w': 'flight' }
            'colors':     { category: [r,g,b] },
            'stats':      { category: count },
            'error':      str  (on failure only)
        }
    """
    try:
        from journal.bindings_reader import BindingsReader
        reader = BindingsReader()
        return reader.read(file_path)
    except Exception as e:
        print(f"[ERROR] get_keybind_categories: {e}")
        return {'success': False, 'error': str(e)}


# ── Apply profile to hardware ─────────────────────────────────────────────

@eel.expose
@with_openrgb_check
def apply_keyboard_profile(led_colors: dict):
    """
    Apply a color profile directly to keyboard LEDs via OpenRGB.

    Uses KeyboardMatrix2D.apply_color_map() — the same path used by
    all other effects in the codebase — which reads device.colors as
    base and sends a single UPDATELEDS packet.

    Args:
        led_colors: { "23": "#0066FF", "45": "#FF0000", ... }

    Returns:
        { 'success': bool, 'applied': int, 'error': str }
    """
    if not try_ensure_openrgb():
        return {'success': False, 'error': 'OpenRGB not reachable'}

    try:
        from effects.device_topology import TopologyType

        # Find first MATRIX keyboard device
        keyboard_ctrl = None
        for ctrl in _manager.devices:
            if ctrl.topology.topology_type == TopologyType.MATRIX:
                keyboard_ctrl = ctrl
                break

        if not keyboard_ctrl:
            return {'success': False, 'error': 'No MATRIX keyboard device found'}

        device    = keyboard_ctrl.topology.device
        led_count = keyboard_ctrl.topology.led_count
        matrix    = keyboard_ctrl.controller   # KeyboardMatrix2D instance

        # Ensure device is in direct/custom mode before sending colors
        try:
            device.set_custom_mode()
        except Exception:
            pass  # Already in custom mode or device doesn't support it

        # Build color_map: { led_index(int) → (r, g, b) }
        color_map = {}
        for idx_str, hex_color in led_colors.items():
            try:
                idx = int(idx_str)
            except ValueError:
                continue
            if idx < 0 or idx >= led_count:
                continue
            h = hex_color.lstrip('#')
            if len(h) != 6:
                continue
            color_map[idx] = (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

        if not color_map:
            return {'success': False, 'error': 'No valid LED colors in payload'}

        # Use apply_color_map: reads device.colors as base, overwrites mapped LEDs
        matrix.apply_color_map(color_map)
        print(f"[OK] Keyboard profile applied: {len(color_map)} LEDs colored")
        return {'success': True, 'applied': len(color_map)}

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] apply_keyboard_profile: {e}")
        return {'success': False, 'error': str(e)}


@eel.expose
@with_openrgb_check
def clear_keyboard_profile():
    """Turn off all LEDs on the first MATRIX keyboard device."""
    if not try_ensure_openrgb():
        return {'success': False, 'error': 'OpenRGB not reachable'}

    try:
        from effects.device_topology import TopologyType

        for ctrl in _manager.devices:
            if ctrl.topology.topology_type == TopologyType.MATRIX:
                # set_all_leds sends a single packet with all zeros
                ctrl.controller.set_all_leds((0, 0, 0))
                print(f"[OK] Keyboard LEDs cleared")
                return {'success': True}

        return {'success': False, 'error': 'No MATRIX keyboard found'}

    except Exception as e:
        print(f"[ERROR] clear_keyboard_profile: {e}")
        return {'success': False, 'error': str(e)}
