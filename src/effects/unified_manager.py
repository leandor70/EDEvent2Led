"""
Unified Effect Manager for Fused Effects.

Manages fused effects across all detected RGB devices, handling
device topology detection and coordinated multi-device playback.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Optional
from utils.openrgb_client import OpenRGBClient
from utils.openrgb_client import RGBColor
from effects.device_topology import TopologyDetector, DeviceTopology, TopologyType
from effects.keyboard_matrix_2d import KeyboardMatrix2D
from effects.linear_1d import Linear1D
from core.visual_effect_library import VisualEffectLibrary
from core.color_scheme_library import ColorSchemeLibrary
from core.visual_effect_renderer import VisualEffectRenderer
from utils.device_keys import assign_keys, base_key, type_name, device_key_of
from utils.openrgb_safe import (
    check_device_mode_support,
    safe_set_mode,
    create_color_array,
    safe_set_colors,
    DeviceSafetyError,
    retry_on_disconnect
)


class DeviceEffectController:
    """
    Wrapper for a single device with its topology and effect controller.
    """

    def __init__(self, topology: DeviceTopology, global_idx: int = 0, device_key: str = ""):
        """
        Initialize device controller.

        Args:
            topology: DeviceTopology object for this device
            global_idx: Position of this device in UnifiedEffectManager.devices list
            device_key: Key of this device in every per-device config file
                        (see utils.device_keys); '#N' suffix on duplicate names
        """
        self.topology = topology
        self.global_idx = global_idx
        self.device_key = device_key or base_key(topology.device.name, type_name(topology.topology_type))
        self.controller = self._create_controller()
        self.device_id = f"{topology.device.name}_{id(topology.device)}"

    def _create_controller(self):
        """Create appropriate controller based on topology."""
        if self.topology.topology_type == TopologyType.MATRIX:
            return KeyboardMatrix2D(
                self.topology.matrix_map,
                self.topology.device
            )
        elif self.topology.topology_type == TopologyType.LINEAR:
            return Linear1D(
                self.topology.device,
                self.topology.led_count,
                global_idx=self.global_idx,
                device_key=self.device_key
            )
        else:  # SINGLE or UNKNOWN
            return Linear1D(
                self.topology.device,
                self.topology.led_count,
                global_idx=self.global_idx,
                device_key=self.device_key
            )

    def apply_effect(self, effect_name: str, params: dict, blocking: bool = False):
        """
        Apply a spatial effect directly to this device.

        Args:
            effect_name: Name of spatial effect (e.g., "pulse", "wave", "ripple")
            params: Effect parameters including duration_ms
            blocking: Whether to block until effect completes
        """
        import threading
        import time
        from effects.spatial_effects_2d import (
            HorizontalSweepEffect, VerticalSweepEffect, RippleEffect,
            WaveEffect, BloomEffect, ExplosionEffect, ImplodingCirclesEffect, DiagonalSweepEffect
        )
        from effects.spatial_effects_1d import (
            WaveEffect1D, ScannerEffect1D, ChaseEffect1D, RainbowEffect1D,
            FillEffect1D, SparkleEffect1D, PulseEffect1D, CenterOutEffect1D,
            PulseFromCenterEffect1D, GradientShiftEffect1D
        )

        duration_ms = params.pop('duration_ms', 3000)

        # Map effect names to classes
        effects_2d = {
            "horizontal_sweep": HorizontalSweepEffect,
            "vertical_sweep": VerticalSweepEffect,
            "ripple": RippleEffect,
            "wave": WaveEffect,
            "bloom": BloomEffect,
            "explosion": ExplosionEffect,
            "explosion_ring": ExplosionEffect,
            "imploding_circles": ImplodingCirclesEffect,
            "diagonal_sweep": DiagonalSweepEffect
        }

        effects_1d = {
            "wave": WaveEffect1D,
            "scanner": ScannerEffect1D,
            "chase": ChaseEffect1D,
            "rainbow": RainbowEffect1D,
            "fill": FillEffect1D,
            "sparkle": SparkleEffect1D,
            "pulse": PulseEffect1D,
            "center_out": CenterOutEffect1D,
            "pulse_from_center": PulseFromCenterEffect1D,
            "gradient_shift": GradientShiftEffect1D
        }

        # Select effect class based on topology
        try:
            if self.topology.topology_type == TopologyType.MATRIX:
                if effect_name not in effects_2d:
                    raise ValueError(f"Unknown 2D effect: {effect_name}")
                effect = effects_2d[effect_name](self.controller, duration_ms=duration_ms, **params)
            else:
                if effect_name not in effects_1d:
                    raise ValueError(f"Unknown 1D effect: {effect_name}")
                effect = effects_1d[effect_name](self.controller, duration_ms=duration_ms, **params)

            # Run effect in thread
            def run_effect():
                try:
                    effect.start()
                    if blocking:
                        time.sleep(duration_ms / 1000.0)
                        effect.stop()
                except Exception as e:
                    print(f"[apply_effect] ERROR: {e}")

            if blocking:
                run_effect()
            else:
                threading.Thread(target=run_effect, daemon=True).start()

        except Exception as e:
            print(f"[apply_effect] EXCEPTION: {type(e).__name__}: {e}")
            raise


class UnifiedEffectManager:
    """
    Unified manager for fused effects across all RGB devices.

    Handles:
    - Device topology detection
    - Fused effect playback across multiple devices
    - Coordinated multi-device effects
    - Effect library management
    """

    def __init__(self, client: OpenRGBClient):
        """
        Initialize unified effect manager.

        Args:
            client: OpenRGBClient instance
        """
        self.client = client
        self.devices: List[DeviceEffectController] = []
        self.disabled_device_keys: set = set()  # Populated by device_config_api
        self._keyboard_locked: bool = False      # Set by Keyboard Default effect with lock=True

        # Reconnection state tracking
        self._connection_lost = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._last_reconnect_time = 0.0  # float for time.time()
        self._reconnect_cooldown = 5.0  # seconds

        # Visual Effects (new system)
        self.visual_library = VisualEffectLibrary()
        self.visual_renderer = VisualEffectRenderer()

        # Color Schemes
        self.color_scheme_library = ColorSchemeLibrary()

        # Detect all devices
        self._detect_devices()

    @retry_on_disconnect(max_retries=2, delay=0.1)
    def _detect_devices_protected(self):
        """Protected device detection with automatic retry."""
        detector = TopologyDetector()
        detected = []  # (device, topology), controllers are created after the keys are known

        for device in self.client.devices:  # ← NOW PROTECTED
            # Verify Direct mode support before attempting to set it
            if not check_device_mode_support(device, "Direct"):
                print(f"  [WARNING] {device.name} does not support Direct mode - effects may not work")
                print(f"            Available modes: {[m.name for m in device.modes]}")
                # Still add device but mark incompatibility
            else:
                # Switch to Direct (custom) mode so per-LED UPDATELEDS packets are
                # visible on the hardware. If device is in a static/rainbow/
                # MODE_SPECIFIC firmware mode, Device._set_device_colors() still
                # sends the packet but the hardware ignores it.
                try:
                    safe_set_mode(device, "Direct", operation="unified_manager:device_init")
                    print(f"  [OK] {device.name} switched to Direct mode")

                    # Clear all LEDs to black (off) after switching to Direct mode
                    # to ensure clean initial state (prevents white LEDs from previous session)
                    try:
                        led_count = len(device.leds)
                        black_colors = create_color_array(0, 0, 0, led_count)
                        safe_set_colors(device, black_colors, fast=True, operation="unified_manager:init_clear")
                        print(f"  [OK] {device.name} LEDs cleared to black ({led_count} LEDs)")
                    except Exception as clear_err:
                        print(f"  [WARNING] Could not clear {device.name} LEDs: {clear_err}")

                except DeviceSafetyError as e:
                    print(f"  [WARNING] Mode validation failed for {device.name}: {e}")
                except Exception as e:
                    print(f"  [WARNING] Could not set {device.name} to Direct mode: {e}")

            topology = detector.detect(device)
            detected.append((device, topology))

            active = device.modes[device.active_mode]
            print(f"Detected: {device.name}")
            print(f"  Type: {topology.topology_type.name}")
            print(f"  LEDs: {topology.led_count}")
            print(f"  Mode: '{active.name}' (color_mode={active.color_mode})")
            if topology.topology_type == TopologyType.MATRIX:
                print(f"  Matrix: {topology.dimensions[0]}x{topology.dimensions[1]}")

        # Keys first, then the one-time migration of the config files, then the
        # controllers: Linear1D reads its topology (by key) while being built.
        keys = assign_keys((t.device.name, type_name(t.topology_type)) for _, t in detected)
        self._migrate_device_keys(detected, keys)
        for global_idx, ((_, topology), key) in enumerate(zip(detected, keys)):
            if key != base_key(topology.device.name, type_name(topology.topology_type)):
                print(f"[UnifiedManager] Duplicate device '{topology.device.name}' -> key '{key}'")
            self.devices.append(DeviceEffectController(topology, global_idx=global_idx, device_key=key))

    @staticmethod
    def _migrate_device_keys(detected: list, keys: list):
        """Bring the per-device config files to the current key scheme (idempotent)."""
        try:
            from utils.device_key_migration import migrate_device_keys
            migrate_device_keys([
                {"idx": i, "name": topo.device.name, "type": type_name(topo.topology_type), "key": key}
                for i, ((_, topo), key) in enumerate(zip(detected, keys))
            ])
        except Exception as e:
            print(f"[WARNING] Device key migration failed: {e}")

    def _detect_devices(self):
        """Detect and classify all connected RGB devices."""
        try:
            self._detect_devices_protected()
        except Exception as e:
            print(f"[ERROR] Device detection failed after retries: {e}")
            raise  # Propagate to Tier 2

    def _reconnect_openrgb(self) -> bool:
        """
        Attempt to reconnect to OpenRGB server.

        Returns:
            True if reconnection successful, False otherwise
        """
        from utils.openrgb_client import OpenRGBDisconnected
        import time

        # Check cooldown
        now = time.time()
        if now - self._last_reconnect_time < self._reconnect_cooldown:
            return False

        self._last_reconnect_time = now
        self._reconnect_attempts += 1

        if self._reconnect_attempts > self._max_reconnect_attempts:
            print(f"[UnifiedManager] Max reconnect attempts exceeded")
            return False

        try:
            # Ping existing client: a real request (ee_devices was a local filter
            # that could never fail, so this branch never reconnected)
            self.client.ping()
            self._connection_lost = False
            self._reconnect_attempts = 0
            return True

        except OpenRGBDisconnected:
            try:
                # Create new client
                from utils.openrgb_client import OpenRGBClient
                import settings as _settings

                host = _settings.get_openrgb_host() if hasattr(_settings, 'get_openrgb_host') else 'localhost'
                port = _settings.get_openrgb_port() if hasattr(_settings, 'get_openrgb_port') else 6742

                new_client = OpenRGBClient(host, port)
                new_client.ping()  # Verify

                # Update client reference
                self.client = new_client
                self._connection_lost = False
                self._reconnect_attempts = 0

                # Re-detect devices
                self._redetect_devices()

                print(f"[UnifiedManager] Reconnected to {host}:{port}")
                return True

            except Exception as e:
                print(f"[UnifiedManager] Reconnection failed: {e}")
                self._connection_lost = True
                return False

    def _redetect_devices(self):
        """Re-detect all devices after reconnection."""
        print("[UnifiedManager] Re-detecting devices...")
        old_count = len(self.devices)
        self.devices.clear()
        self._detect_devices()
        print(f"[UnifiedManager] Devices: {old_count} -> {len(self.devices)}")

    def set_disabled_devices(self, disabled_keys: set):
        """Update the set of device keys that should be excluded from effect playback."""
        self.disabled_device_keys = disabled_keys

    def set_keyboard_lock(self, locked: bool):
        """
        Lock or unlock keyboard (MATRIX) devices from being overridden by other effects.

        When locked=True, play_visual_effect() skips MATRIX devices entirely,
        preserving the keyboard colors set by the Keyboard Default effect.
        Lock is reset by stop_all_effects() and clear_all().
        """
        self._keyboard_locked = locked

    @staticmethod
    def _make_device_key(device_ctrl) -> str:
        """Return the config key of a device: 'DeviceName::topology_type', '#N' on duplicates."""
        return device_key_of(device_ctrl)

    def print_device_summary(self):
        """Print summary of all detected devices."""
        print("\n=== Device Summary ===")
        matrix_count = sum(1 for d in self.devices if d.topology.topology_type == TopologyType.MATRIX)
        linear_count = sum(1 for d in self.devices if d.topology.topology_type == TopologyType.LINEAR)
        single_count = sum(1 for d in self.devices if d.topology.topology_type == TopologyType.SINGLE)

        print(f"  2D Matrix: {matrix_count}")
        print(f"  1D Linear: {linear_count}")
        print(f"  Single LED: {single_count}")
        print(f"  Total: {len(self.devices)}")

    def stop_all_effects(self):
        """Stop all active effects on all devices. Also releases keyboard lock."""
        self._keyboard_locked = False
        self.visual_renderer.stop_all()

    def is_effect_playing(self) -> bool:
        """Return True if any visual effect is currently active on any device."""
        return self.visual_renderer.is_playing()

    def apply_direct_colors(self, device_key: str, colors: list) -> bool:
        """
        Apply RGB colors directly to a device, bypassing the effect system.
        Used by AmbilightService for idle LED updates.

        Args:
            device_key: Device key in format "DeviceName::topology_type"
            colors: List of (R, G, B) tuples, length must match device LED count

        Returns:
            True if applied successfully, False if device not found or error.
        """
        if device_key in self.disabled_device_keys:
            return False
        for device_ctrl in self.devices:
            if self._make_device_key(device_ctrl) == device_key:
                try:
                    rgb_colors = [RGBColor(r, g, b) for r, g, b in colors]
                    safe_set_colors(
                        device_ctrl.topology.device,
                        rgb_colors,
                        fast=True,
                        operation="ambilight:direct",
                    )
                    return True
                except Exception as exc:
                    print(f"[apply_direct_colors] {device_key}: {exc}")
                    return False
        return False

    def apply_direct_leds(self, device_key: str, led_colors: dict) -> bool:
        """
        Scrive SOLO i LED indicati, lasciando gli altri come sono.

        Usato dall'ambilight: i LED che non pilota (fuori schermo, zone spente)
        restano a chi li usa (effetti, OpenRGB). Se i LED indicati sono tutti quelli
        del device parte un solo pacchetto; altrimenti un pacchetto per ogni zona
        OpenRGB interamente coperta e uno per ogni altro LED.

        Args:
            device_key: chiave device ("Nome::tipo")
            led_colors: {indice LED hardware: (R, G, B)}

        Returns:
            True se applicato, False se device non trovato, disabilitato o errore.
        """
        if device_key in self.disabled_device_keys or not led_colors:
            return False
        for device_ctrl in self.devices:
            if self._make_device_key(device_ctrl) != device_key:
                continue
            device = device_ctrl.topology.device
            total = device_ctrl.topology.led_count
            try:
                if len(led_colors) >= total and all(i in led_colors for i in range(total)):
                    full = [RGBColor(*led_colors[i]) for i in range(total)]
                    safe_set_colors(device, full, fast=True, operation="ambilight:direct")
                    return True
                sent = set()
                for zone in device.zones:
                    ids = [led.id for led in zone.leds]
                    if ids and all(i in led_colors for i in ids):
                        zone.set_colors([RGBColor(*led_colors[i]) for i in ids], fast=True)
                        sent.update(ids)
                for i, color in led_colors.items():
                    if i not in sent and 0 <= i < total:
                        device.leds[i].set_color(RGBColor(*color), fast=True)
                return True
            except Exception as exc:
                print(f"[apply_direct_leds] {device_key}: {exc}")
                return False
        return False

    def clear_all(self):
        """Clear all LEDs on all devices (set to black)."""
        self.stop_all_effects()
        for device_ctrl in self.devices:
            try:
                # Set all LEDs to black in batch mode
                black = RGBColor(0, 0, 0)
                colors = [black] * device_ctrl.topology.led_count
                device_ctrl.topology.device.set_colors(colors)
            except Exception as e:
                print(f"Error clearing device {device_ctrl.topology.device.name}: {e}")

    def get_device_by_name(self, name: str) -> Optional[DeviceEffectController]:
        """Get device controller by device name."""
        for device_ctrl in self.devices:
            if name.lower() in device_ctrl.topology.device.name.lower():
                return device_ctrl
        return None

    def get_devices_by_topology(self, topology_type: TopologyType) -> List[DeviceEffectController]:
        """Get all devices of a specific topology type."""
        return [
            device_ctrl for device_ctrl in self.devices
            if device_ctrl.topology.topology_type == topology_type
        ]

    def reload_visual_library(self):
        """Reload visual effects from disk."""
        self.visual_library = VisualEffectLibrary()
        print(f"Reloaded visual effect library: {len(self.visual_library.effects)} effects")

    def reload_color_schemes(self):
        """Reload color schemes from disk."""
        self.color_scheme_library = ColorSchemeLibrary()
        print(f"Reloaded color scheme library: {len(self.color_scheme_library.schemes)} schemes")

    # ============================================================
    # VISUAL EFFECTS (NEW SYSTEM)
    # ============================================================

    def play_visual_effect(
        self,
        effect_id: str,
        devices: Optional[List[DeviceEffectController]] = None,
        blocking: bool = False
    ):
        """
        Play a Visual Effect (sequence of Base Effects) on specified devices.

        Args:
            effect_id: ID of visual effect from library
            devices: List of devices to play on (None = all devices)
            blocking: Whether to wait for effect to complete
        """
        # Load effect from library
        visual_effect = self.visual_library.get_effect(effect_id)
        if not visual_effect:
            print(f"Error: Visual Effect '{effect_id}' not found in library")
            return

        # Default to all devices if not specified
        if devices is None:
            devices = self.devices

        # Exclude disabled devices
        devices = [d for d in devices if self._make_device_key(d) not in self.disabled_device_keys]
        if not devices:
            print(f"[UnifiedManager] play_visual_effect '{effect_id}': all devices disabled or none available")
            return

        # Skip MATRIX (keyboard) devices when keyboard lock is active,
        # unless the effect being played IS the keyboard_default (which sets the lock).
        from core.visual_effect_library import KEYBOARD_DEFAULT_ID
        if self._keyboard_locked and effect_id != KEYBOARD_DEFAULT_ID:
            devices = [d for d in devices
                       if self._get_topology_string(d) != "2D"]
            if not devices:
                return

        # Start effect on each device
        # The renderer will automatically create appropriate fallback effects for each device topology
        for device_ctrl in devices:
            try:
                on_complete = self._make_idle_callback(device_ctrl, visual_effect)
                self.visual_renderer.start_effect(
                    device_id=device_ctrl.device_id,
                    device_controller=device_ctrl,
                    visual_effect=visual_effect,
                    simulator_mode=False,
                    blocking=False,  # Always non-blocking per device
                    on_complete=on_complete
                )
            except Exception as e:
                print(f"Error playing visual effect on {device_ctrl.topology.device.name}: {e}")

        # If this is the keyboard_default effect, apply lock setting from presets config
        if effect_id == KEYBOARD_DEFAULT_ID:
            try:
                import json as _json
                with open('config/keyboard_presets.json', 'r', encoding='utf-8') as _f:
                    _pdata = _json.load(_f)
                self._keyboard_locked = bool(_pdata.get('lock_keyboard', False))
            except Exception:
                pass

        # If blocking requested, wait for effect duration
        if blocking:
            import time
            duration_s = visual_effect.total_duration_ms() / 1000.0
            if duration_s > 0:
                time.sleep(duration_s)

    def play_visual_effect_object(
        self,
        visual_effect,
        devices: Optional[List[DeviceEffectController]] = None,
        blocking: bool = False
    ):
        """
        Play a VisualEffect object directly, without library lookup.
        Used for inline effects embedded in event_mappings.json / status_mappings.json.
        """
        if devices is None:
            devices = self.devices

        devices = [d for d in devices if self._make_device_key(d) not in self.disabled_device_keys]
        if not devices:
            return

        from core.visual_effect_library import KEYBOARD_DEFAULT_ID
        if self._keyboard_locked and getattr(visual_effect, 'id', '') != KEYBOARD_DEFAULT_ID:
            devices = [d for d in devices if self._get_topology_string(d) != "2D"]
            if not devices:
                return

        for device_ctrl in devices:
            try:
                on_complete = self._make_idle_callback(device_ctrl, visual_effect)
                self.visual_renderer.start_effect(
                    device_id=device_ctrl.device_id,
                    device_controller=device_ctrl,
                    visual_effect=visual_effect,
                    simulator_mode=False,
                    blocking=False,
                    on_complete=on_complete
                )
            except Exception as e:
                print(f"Error playing inline effect on {device_ctrl.topology.device.name}: {e}")

        if blocking:
            import time
            duration_s = visual_effect.total_duration_ms() / 1000.0
            if duration_s > 0:
                time.sleep(duration_s)

    def play_visual_effect_on_device(
        self,
        effect_id: str,
        device_id: str,
        blocking: bool = False
    ):
        """
        Play a Visual Effect on a specific device by ID.

        Args:
            effect_id: ID of visual effect from library
            device_id: Device identifier (device_ctrl.device_id)
            blocking: Whether to wait for effect to complete
        """
        # Find device by ID
        device_ctrl = next(
            (d for d in self.devices if d.device_id == device_id),
            None
        )

        if device_ctrl:
            self.play_visual_effect(effect_id, [device_ctrl], blocking)
        else:
            print(f"Error: Device with ID '{device_id}' not found")

    def apply_color_scheme(
        self,
        scheme_id: str,
        devices: Optional[List[DeviceEffectController]] = None
    ):
        """
        Apply a Color Scheme to specified devices (typically keyboards).

        Args:
            scheme_id: ID of color scheme from library
            devices: List of devices to apply to (None = all keyboards)
        """
        # Load scheme from library
        scheme = self.color_scheme_library.get_scheme(scheme_id)
        if not scheme:
            print(f"Error: Color Scheme '{scheme_id}' not found in library")
            return

        # Default to all 2D devices (keyboards) if not specified
        if devices is None:
            devices = self.get_devices_by_topology(TopologyType.MATRIX)

        # Apply scheme to each device
        for device_ctrl in devices:
            try:
                # Get current colors array
                colors = device_ctrl.topology.device.colors

                # Apply LED colors from scheme to array (batch mode)
                for led_index, color in scheme.led_colors.items():
                    if led_index < len(colors):
                        colors[led_index] = RGBColor(*color)

                # Set all colors at once (batch update)
                device_ctrl.topology.device.set_colors(colors)
                print(f"Applied color scheme '{scheme.name}' to {device_ctrl.topology.device.name}")

            except Exception as e:
                print(f"Error applying color scheme to {device_ctrl.topology.device.name}: {e}")

    def apply_color_scheme_to_device(
        self,
        scheme_id: str,
        device_id: str
    ):
        """
        Apply a Color Scheme to a specific device.

        Args:
            scheme_id: ID of color scheme from library
            device_id: Device identifier
        """
        # Find device by ID
        device_ctrl = next(
            (d for d in self.devices if d.device_id == device_id),
            None
        )

        if device_ctrl:
            self.apply_color_scheme(scheme_id, [device_ctrl])
        else:
            print(f"Error: Device with ID '{device_id}' not found")

    def _make_idle_callback(self, device_ctrl, visual_effect):
        """
        Return an on_complete callback that applies the device's idle behavior
        (on_disable config) after the effect finishes.

        Skipped for:
        - Internal effects (__disable_fade__, keyboard_default) to prevent loops
        - MATRIX devices whose effect contains a keyboard_default step (the
          preset restore IS the final state; idle behavior would overwrite it)
        """
        from core.visual_effect_library import KEYBOARD_DEFAULT_ID
        from core.base_effects import BaseEffectType

        # Effects that must NOT trigger idle behavior after they end
        _internal_ids = {'__disable_fade__', KEYBOARD_DEFAULT_ID}

        has_kbd_default = any(
            s.effect_type == BaseEffectType.KEYBOARD_DEFAULT
            for s in visual_effect.steps
        )
        is_matrix = device_ctrl.topology.topology_type == TopologyType.MATRIX

        def on_complete():
            if visual_effect.id in _internal_ids:
                return
            if is_matrix and has_kbd_default:
                return
            try:
                from api.device_config_api import _apply_on_disable_behavior, _device_key
                config_key = _device_key(device_ctrl)
                _apply_on_disable_behavior(device_ctrl, config_key)
            except Exception as e:
                print(f"[UnifiedManager] idle behavior error for "
                      f"{device_ctrl.topology.device.name}: {e}")

        return on_complete

    def _get_topology_string(self, device_ctrl: DeviceEffectController) -> str:
        """
        Get topology string for a device.

        Args:
            device_ctrl: DeviceEffectController

        Returns:
            Topology string: "2D", "1D", or "0D"
        """
        topo_map = {
            TopologyType.MATRIX: "2D",
            TopologyType.LINEAR: "1D",
            TopologyType.SINGLE: "0D",
            TopologyType.UNKNOWN: "1D"  # Default to 1D for unknown
        }
        return topo_map.get(device_ctrl.topology.topology_type, "1D")
