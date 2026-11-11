"""
Device Config API — persistent enable/disable and on-disable behavior per device.

Stores config in config/device_config.json.
Keys use the format  "DeviceName::topology_type"  (e.g. "ASUS TUF K7::matrix"),
with "#2", "#3" on devices that share name and type (see utils/device_keys.py).
"""
import eel
import json
from pathlib import Path

from utils.device_keys import device_key_of

_manager = None
_config_path = Path("config/device_config.json")
_config: dict = {"version": 1, "devices": {}}


def init_device_config_api(manager):
    """Load persisted config and sync disabled state into the effect manager."""
    global _manager
    _manager = manager
    _load_config()
    if manager:
        _apply_disabled_to_manager()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _device_key(device_ctrl) -> str:
    """The config key: 'DeviceName::topology_type', '#N' on duplicates (utils.device_keys)."""
    return device_key_of(device_ctrl)


def _load_config():
    global _config
    if _config_path.exists():
        try:
            with open(_config_path, 'r', encoding='utf-8') as f:
                _config = json.load(f)
        except Exception:
            _config = {"version": 1, "devices": {}}


def _save_config():
    _config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_config_path, 'w', encoding='utf-8') as f:
        json.dump(_config, f, indent=2, ensure_ascii=False)


def _apply_disabled_to_manager():
    """Push the full disabled-key set into the effect manager."""
    if not _manager:
        return
    disabled = {k for k, v in _config.get("devices", {}).items()
                if not v.get("enabled", True)}
    _manager.set_disabled_devices(disabled)


def _play_fade_to_color(device_ctrl, color: tuple):
    """
    Play a 1-second static transition to the given RGB color on a single device.
    Creates a temporary VisualEffect (not saved to library) and sends it
    directly to the visual renderer.
    """
    if not _manager or not _manager.visual_renderer:
        return
    try:
        from core.base_effects import (
            VisualEffect, BaseEffectStep, BaseEffectParams,
            BaseEffectType, PostSequenceBehavior
        )
        r, g, b = int(color[0]), int(color[1]), int(color[2])
        step = BaseEffectStep(
            step_id="disable_fade",
            effect_type=BaseEffectType.STATIC_TRANSITION,
            params=BaseEffectParams(
                colors=[(r, g, b)],
                duration_ms=1000
            )
        )
        effect = VisualEffect(
            id="__disable_fade__",
            name="Disable Fade",
            description="",
            steps=[step],
            topology_support=["2D", "1D", "0D"],
            post_behavior=PostSequenceBehavior.STATIC_COLOR,
            post_behavior_data={"color": [r, g, b]}
        )
        _manager.visual_renderer.start_effect(
            device_id=device_ctrl.device_id,
            device_controller=device_ctrl,
            visual_effect=effect,
            simulator_mode=False,
            blocking=False
        )
    except Exception as e:
        print(f"[DeviceConfig] Could not play fade to color on {device_ctrl.topology.device.name}: {e}")


def _apply_on_disable_behavior(device_ctrl, config_key: str):
    """
    Apply the chosen behavior to a device immediately when it gets disabled.

    Options:
        keep     — leave LEDs as-is
        off      — set all LEDs to black (instant)
        hardware — activate first available hardware mode (firmware animation)
        color    — 1-second fade transition to the configured disable_color
    """
    devices_cfg = _config.get("devices", {})
    device_cfg = devices_cfg.get(config_key, {})
    on_disable = device_cfg.get("on_disable", "keep")
    device = device_ctrl.topology.device
    led_count = device_ctrl.topology.led_count

    if on_disable == "off":
        from utils.openrgb_client import RGBColor
        try:
            device.set_colors([RGBColor(0, 0, 0)] * led_count)
        except Exception as e:
            print(f"[DeviceConfig] Could not turn off {device.name}: {e}")

    elif on_disable == "hardware":
        if device.modes:
            try:
                device.set_mode(device.modes[0])
            except Exception as e:
                print(f"[DeviceConfig] Could not set hardware mode on {device.name}: {e}")

    elif on_disable == "color":
        raw = device_cfg.get("disable_color", [0, 0, 0])
        _play_fade_to_color(device_ctrl, tuple(raw))

    # "ambilight": idle handled by AmbilightService; disabling the device here
    # is a no-op — leave LEDs as-is (same as "keep").
    # "keep": do nothing — LEDs stay at their current state


# ── Eel-exposed endpoints ─────────────────────────────────────────────────────

@eel.expose
def get_device_config():
    """Return persisted config for all known devices."""
    return {"success": True, "config": _config.get("devices", {})}


@eel.expose
def set_device_enabled(config_key: str, enabled: bool):
    """
    Enable or disable a device.

    When disabling, applies the configured on_disable behavior immediately.
    Persists to disk and updates the effect manager.
    """
    try:
        devices_cfg = _config.setdefault("devices", {})

        # Create entry with defaults if not seen before
        if config_key not in devices_cfg:
            devices_cfg[config_key] = {"enabled": True, "on_disable": "keep"}

        old_enabled = devices_cfg[config_key].get("enabled", True)
        devices_cfg[config_key]["enabled"] = enabled

        _save_config()
        _apply_disabled_to_manager()

        # Apply on_disable behavior only when transitioning from enabled → disabled
        if old_enabled and not enabled and _manager:
            for d in _manager.devices:
                if _device_key(d) == config_key:
                    _apply_on_disable_behavior(d, config_key)
                    break

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def set_device_on_disable(config_key: str, on_disable: str):
    """
    Set the behavior applied when this device is disabled.

    Valid values: "keep" | "hardware" | "off" | "color"
    """
    try:
        if on_disable not in ("keep", "hardware", "off", "color", "ambilight"):
            return {"success": False, "error": f"Invalid on_disable value: {on_disable!r}"}

        devices_cfg = _config.setdefault("devices", {})
        if config_key not in devices_cfg:
            devices_cfg[config_key] = {"enabled": True, "on_disable": on_disable}
        else:
            devices_cfg[config_key]["on_disable"] = on_disable

        _save_config()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def set_device_topology_editor(config_key: str, enabled: bool):
    """Enable or disable this device in the Topology Editor (LINEAR devices only)."""
    try:
        devices_cfg = _config.setdefault("devices", {})
        if config_key not in devices_cfg:
            devices_cfg[config_key] = {"enabled": True, "on_disable": "keep"}
        devices_cfg[config_key]["topology_editor"] = enabled
        _save_config()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@eel.expose
def set_device_disable_color(config_key: str, color: list):
    """
    Set the color used when on_disable == "color".

    Args:
        config_key: device key (e.g. "LedStripScrivania::linear")
        color: [R, G, B] with values 0-255
    """
    try:
        if len(color) != 3:
            return {"success": False, "error": "color must be [R, G, B]"}
        r, g, b = int(color[0]), int(color[1]), int(color[2])

        devices_cfg = _config.setdefault("devices", {})
        if config_key not in devices_cfg:
            devices_cfg[config_key] = {"enabled": True, "on_disable": "keep"}
        devices_cfg[config_key]["disable_color"] = [r, g, b]

        _save_config()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
