"""
Visual Effect Renderer - Plays sequences of Base Effects on devices.

This renderer takes a Visual Effect (sequence of Base Effect Steps) and plays
them sequentially on one or more devices, handling loop_infinite steps and
post-sequence behaviors.

Architecture notes:
- IOBatcher: intercepts apply_color_map() calls from effect threads, buffers
  the resulting color arrays, and flushes them in LED-count order (largest
  device first) within the render loop thread.  This serialises all hardware
  I/O through a single thread and ensures the keyboard (105 LEDs) is always
  sent before smaller devices, eliminating the "keyboard always lags" issue.
- Callback-based step advancement: each spatial effect is started with an
  on_complete callback that posts (device_id, step_idx) to a thread-safe
  queue.  The render loop drains that queue at the top of every tick and
  advances/restores immediately, minimising the window during which the
  hardware is stuck in a near-black end-of-animation frame.
"""

import json
import time
import queue
import threading
from pathlib import Path
from typing import Dict, Optional, Callable, List, Any, Tuple

from utils.openrgb_client import RGBColor

from .base_effects import (
    VisualEffect, BaseEffectStep, BaseEffectType
)
from effects.device_topology import TopologyType
from effects.spatial_effects_2d import (
    Animated2DEffect, HorizontalSweepEffect, VerticalSweepEffect,
    RippleEffect, WaveEffect, BumpEffect2D, ColorCycleEffect2D, BloomEffect, ExplosionEffect,
    ImplodingCirclesEffect, DiagonalSweepEffect, GlitchEffect2D,
    FireEffect2D, MatrixRainEffect2D, OceanWavesEffect2D, PlasmaEffect2D,
    AuroraEffect2D, ParallaxStarsEffect2D, LightningEffect2D,
    DirectionalFlashEffect
)
from effects.pulse_2d import PulseEffect2D, FadeEffect2D, BreathEffect2D
from effects.gradient_2d import GradientEffect2D
from effects.corner_gradient_2d import CornerGradientEffect2D
from effects.spatial_effects_1d import (
    Animated1DEffect, WaveEffect1D, ColorCycleEffect1D, ScannerEffect1D,
    ChaseEffect1D, RainbowEffect1D, FillEffect1D, SparkleEffect1D,
    PulseEffect1D, FadeEffect1D, CenterOutEffect1D, PulseFromCenterEffect1D,
    GradientShiftEffect1D, BreathEffect1D
)
from core._bbox import GlobalBoundingBox
from core._io_batcher import _IOBatcher
from core._active_effect import ActiveVisualEffect

# Effects that manage their own fade internally — skip external fade_in injection.
_EFFECTS_WITH_INTRINSIC_FADE = {
    BaseEffectType.STATIC_TRANSITION,
    BaseEffectType.BREATH,
}

# ---------------------------------------------------------------------------
# Windows timer resolution helper
# ---------------------------------------------------------------------------

def _set_windows_timer_resolution():
    """Set Windows multimedia timer resolution to 1ms (default is ~15ms).

    Improves sleep() precision so effect threads hit their frame deadlines
    without drifting, eliminating subtle LED stutter at 30 fps.
    Safe no-op on non-Windows platforms.
    """
    try:
        import ctypes
        winmm = ctypes.windll.winmm  # type: ignore[attr-defined]
        winmm.timeBeginPeriod(1)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_keyboard_preset_colors(preset_id: str) -> dict:
    """Load led_colors for a keyboard preset from keyboard_presets.json.

    Returns {int_led_index: (R, G, B)} or empty dict if not found.
    """
    import json as _json
    from pathlib import Path as _Path
    try:
        data = _json.loads(_Path('config/keyboard_presets.json').read_text(encoding='utf-8'))
        raw = data.get('presets', {}).get(str(preset_id), {}).get('led_colors', {})
        return {int(k): tuple(v) for k, v in raw.items()}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class VisualEffectRenderer:
    """
    Renderer for Visual Effects (sequences of Base Effects).

    Handles:
    - Sequential playback of Base Effect Steps
    - loop_infinite step handling (don't advance)
    - Post-sequence behaviors (turn off, static color, loop effect, color scheme)
    - Simulator mode for visual preview
    - Serialised hardware I/O via IOBatcher (keyboard-first ordering)
    - Callback-based step advancement (near-zero latency between effect end and restore)
    """

    # Fallback guard: if a step's on_complete callback is never fired
    # (e.g. effect thread crashed), advance after duration_ms + this margin.
    _STEP_TIMEOUT_MARGIN_MS = 500

    def __init__(self):
        """Initialize the Visual Effect Renderer."""
        # Improve sleep() precision to ~1ms on Windows (default is ~15ms).
        # This reduces frame-timing drift between effect threads and render loop,
        # which otherwise causes subtle LED stutter at 30fps.
        _set_windows_timer_resolution()

        self.active_effects: Dict[str, ActiveVisualEffect] = {}
        # RLock (reentrant) because start_effect() calls _cancel_effect() which
        # both need the lock — same thread must re-acquire without deadlock.
        self._active_lock = threading.RLock()
        self.running = False
        self.render_thread = None
        self.fps = 30
        self.simulator_callback: Optional[Callable] = None

        # LED state snapshots: device_id -> List[(r,g,b)]
        self._saved_states: Dict[str, List[Tuple[int, int, int]]] = {}

        # Coordinate normalization (Phase 1.1)
        self._device_world_positions: Dict[str, List[Tuple[float, float]]] = {}
        self._global_bbox: Optional[GlobalBoundingBox] = None

        # IO batching
        self._io_batcher = _IOBatcher()

        # Callback-based step completion (thread-safe)
        self._completion_queue: queue.Queue = queue.Queue()
        # Wakeup event: effect threads set this so the render loop wakes
        # immediately instead of waiting for the full 1/fps sleep.
        self._wakeup_event = threading.Event()

        # Error tracking for Tier 3 triggering
        self._device_errors: Dict[str, List[Exception]] = {}
        self._error_threshold = 8   # Trigger Tier 3 after 8 errors
        self._error_window = 30.0  # seconds — wider window avoids transient spikes
        # NOTE: Tier 3 flag now stored in api.effects_api global state (persists after _manager invalidation)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_simulator_callback(self, callback: Callable):
        """Set callback for simulator updates."""
        self.simulator_callback = callback

    def is_playing(self) -> bool:
        """Return True if any effect is currently active on any device."""
        with self._active_lock:
            return bool(self.active_effects)

    def start_effect(
        self,
        device_id: str,
        device_controller,
        visual_effect: VisualEffect,
        simulator_mode: bool = False,
        blocking: bool = False,
        on_complete: Optional[Callable] = None
    ):
        """
        Start playing a Visual Effect (sequence of Base Effects).

        Args:
            device_id: Unique identifier for the device
            device_controller: DeviceEffectController instance
            visual_effect: VisualEffect to play
            simulator_mode: If True, only update simulator (no hardware)
            blocking: If True, blocks until effect completes
            on_complete: Callback function when effect finishes
        """
        # Cancel any existing effect on this device WITHOUT restoring state.
        self._cancel_effect(device_id)

        from utils.log_buffer import log_led
        dev_name = device_controller.topology.device.name
        n_steps = len(visual_effect.steps)
        log_led(dev_name, "effect_start",
                f"'{visual_effect.name}'  {n_steps} step(s)  "
                f"post={visual_effect.post_behavior.value}")

        # Snapshot LED state before the sequence starts (only if no snapshot yet).
        if not simulator_mode:
            self._save_led_state(device_id, device_controller)

        # Register IOBatcher intercept on the device controller so that all
        # apply_color_map() calls from effect threads post to the batcher
        # instead of sending directly to hardware.
        if not simulator_mode:
            self._register_batcher(device_id, device_controller)

        # Create spatial effect only for the first step now.
        # Subsequent steps are created lazily in _start_step so that effects like
        # FadeEffect (Static Transition) read device.colors AFTER the previous step
        # has finished — capturing the correct hardware state as start_colors.
        spatial_effects = [None] * len(visual_effect.steps)
        try:
            spatial_effects[0] = self._create_spatial_effect_from_step(
                device_controller, visual_effect.steps[0]
            )
        except Exception as e:
            print(f"[Renderer] Error creating spatial effect for step 0: {e}")

        # Create active effect entry
        active = ActiveVisualEffect(
            visual_effect=visual_effect,
            device_controller=device_controller,
            spatial_effects=spatial_effects,
            current_step_index=0,
            step_start_time=time.time(),
            simulator_mode=simulator_mode,
            on_complete=on_complete
        )

        with self._active_lock:
            self.active_effects[device_id] = active

        # Invalidate global bbox cache (device set changed)
        self._global_bbox = None

        # Start first step
        self._start_step(device_id, active, 0)

        # Start render loop if not already running or if previous thread died
        thread_dead = (self.render_thread is not None and not self.render_thread.is_alive())
        if not self.running or thread_dead:
            self.running = True
            if blocking:
                self._run_render_loop()
            else:
                self.render_thread = threading.Thread(
                    target=self._run_render_loop,
                    daemon=True
                )
                self.render_thread.start()

    # ------------------------------------------------------------------
    # LED state save / restore
    # ------------------------------------------------------------------

    def _save_led_state(self, device_id: str, device_controller) -> bool:
        """
        Snapshot the current LED colors into memory before a sequence starts.

        Only saves if no snapshot already exists for this device.
        """
        if device_id in self._saved_states:
            return True
        try:
            device = device_controller.controller.device
            self._saved_states[device_id] = [
                (c.red, c.green, c.blue) for c in device.colors
            ]
            return True
        except Exception as e:
            print(f"[Renderer] Could not save LED state for {device_id}: {e}")
            return False

    def _restore_led_state(self, device_id: str, device_controller):
        """Restore LED colors from the saved snapshot and clear it."""
        if device_id not in self._saved_states:
            return
        try:
            device = device_controller.controller.device
            snapshot = self._saved_states[device_id]
            device.set_colors([RGBColor(r, g, b) for r, g, b in snapshot])
        except Exception as e:
            print(f"[Renderer] Could not restore LED state for {device_id}: {e}")
        finally:
            self._saved_states.pop(device_id, None)

    # ------------------------------------------------------------------
    # IOBatcher registration
    # ------------------------------------------------------------------

    def _register_batcher(self, device_id: str, device_controller):
        """Attach IOBatcher intercept to the device controller."""
        controller = device_controller.controller
        if not hasattr(controller, '_frame_intercept'):
            return  # Controller type doesn't support batching

        led_count = len(controller.device.colors)
        device = controller.device
        batcher = self._io_batcher

        def _intercept(colors: list):
            batcher.post(device_id, led_count, device, colors)

        controller._frame_intercept = _intercept

    def _unregister_batcher(self, device_id: str, device_controller):
        """Detach IOBatcher intercept and discard any pending frame."""
        controller = device_controller.controller
        if hasattr(controller, '_frame_intercept'):
            controller._frame_intercept = None
        self._io_batcher.discard(device_id)

    # ------------------------------------------------------------------
    # Coordinate Normalization (Phase 1.1)
    # ------------------------------------------------------------------

    def _get_device_world_positions(self, device_id: str, device_controller) -> List[Tuple[float, float]]:
        """
        Get world coordinates for all LEDs of a device.

        Args:
            device_id: Device identifier
            device_controller: DeviceEffectController instance

        Returns:
            List of (world_x, world_y) tuples for each LED
        """
        # Check cache first
        if device_id in self._device_world_positions:
            return self._device_world_positions[device_id]

        positions = []
        controller = device_controller.controller

        # MATRIX device (KeyboardMatrix2D)
        if hasattr(controller, 'matrix_map') and hasattr(controller, 'rows') and hasattr(controller, 'cols'):
            matrix = controller
            for row in range(matrix.rows):
                for col in range(matrix.cols):
                    led_idx = matrix.get_led_index(row, col)
                    if led_idx is not None:
                        # Direct mapping: col→X, row→Y
                        world_x, world_y = float(col), float(row)
                        positions.append((world_x, world_y))

        # LINEAR device (Linear1D)
        elif hasattr(controller, 'led_count') and hasattr(controller, 'get_led_world_position'):
            linear = controller
            for led_idx in range(linear.led_count):
                try:
                    zone_idx, local_idx = linear.get_zone_and_local_index(led_idx)
                    world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)
                    positions.append((world_x, world_y))
                except:
                    # Fallback: sequential positioning
                    positions.append((float(led_idx), 0.0))

        # SINGLE or unknown - place at origin
        else:
            led_count = len(controller.device.colors) if hasattr(controller, 'device') else 1
            for i in range(led_count):
                positions.append((0.0, 0.0))

        # Cache for future calls
        self._device_world_positions[device_id] = positions
        return positions

    def _calculate_global_bbox(self) -> GlobalBoundingBox:
        """
        Calculate bounding box that encloses all active devices.

        Returns:
            GlobalBoundingBox spanning all device LED positions
        """
        if not self.active_effects:
            # No active devices - return unit square
            return GlobalBoundingBox(0.0, 0.0, 1.0, 1.0)

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        for device_id, active in self.active_effects.items():
            # Exclude MATRIX (keyboard) devices from scene bounding box — they use their own coordinate system
            if active.device_controller.topology.topology_type == TopologyType.MATRIX:
                continue
            # Get all LED world positions for this device
            positions = self._get_device_world_positions(device_id, active.device_controller)

            for world_x, world_y in positions:
                min_x = min(min_x, world_x)
                min_y = min(min_y, world_y)
                max_x = max(max_x, world_x)
                max_y = max(max_y, world_y)

        # Add padding (10% on each side) to avoid edge clipping
        width = max_x - min_x
        height = max_y - min_y
        padding_x = width * 0.1 if width > 0 else 1.0
        padding_y = height * 0.1 if height > 0 else 1.0

        return GlobalBoundingBox(
            min_x - padding_x,
            min_y - padding_y,
            max_x + padding_x,
            max_y + padding_y
        )

    def _calculate_global_bbox_with_center(
        self,
        center_x_pct: float,
        center_y_pct: float
    ) -> GlobalBoundingBox:
        """
        Calculate bbox expanded to center a custom point.

        This enables radial effects (Bloom, Explosion, Plasma) to originate from
        a user-specified center point instead of the geometric center. The bbox
        is expanded symmetrically so that the custom center becomes the geometric
        center of the expanded bbox.

        Args:
            center_x_pct: Centro X in percentuale 0-100
            center_y_pct: Centro Y in percentuale 0-100

        Returns:
            GlobalBoundingBox expanded to center the specified point

        Example:
            >>> # Original bbox: [0,7] × [0,5], center at (3.5, 2.5)
            >>> # Custom center: 85% X, 80% Y → world (6.0, 4.0)
            >>> # Result: bbox expands to [0,12] × [0,8] to make (6,4) the center
        """
        standard_bbox = self._calculate_global_bbox()

        # Convert percentage to normalized [0,1]
        cx_norm = max(0.0, min(1.0, center_x_pct / 100.0))
        cy_norm = max(0.0, min(1.0, center_y_pct / 100.0))

        # Convert to world coords
        width = standard_bbox.max_x - standard_bbox.min_x
        height = standard_bbox.max_y - standard_bbox.min_y
        cx_world = standard_bbox.min_x + cx_norm * width
        cy_world = standard_bbox.min_y + cy_norm * height

        # Calculate distances from center to edges
        dist_left = cx_world - standard_bbox.min_x
        dist_right = standard_bbox.max_x - cx_world
        dist_bottom = cy_world - standard_bbox.min_y
        dist_top = standard_bbox.max_y - cy_world

        # Symmetric expansion: use maximum distance
        half_width = max(dist_left, dist_right)
        half_height = max(dist_bottom, dist_top)

        # Apply 10% padding (same as standard bbox)
        expanded_width = 2 * half_width
        expanded_height = 2 * half_height
        padding_x = expanded_width * 0.1 if expanded_width > 0 else 1.0
        padding_y = expanded_height * 0.1 if expanded_height > 0 else 1.0

        return GlobalBoundingBox(
            cx_world - half_width - padding_x,
            cy_world - half_height - padding_y,
            cx_world + half_width + padding_x,
            cy_world + half_height + padding_y
        )

    def _has_custom_center(self, device_controller) -> bool:
        """
        Check if device has custom effect center in topology.

        Args:
            device_controller: Device controller (Linear1D or KeyboardMatrix2D)

        Returns:
            True if device has effect_center configured in topology
        """
        # Check if device controller has topology loaded
        if not hasattr(device_controller, '_topology'):
            return False

        topology = device_controller._topology
        if not topology or not isinstance(topology, dict):
            return False

        # Check if effect_center exists
        if 'effect_center' not in topology:
            return False

        effect_center = topology.get('effect_center', {})
        if not isinstance(effect_center, dict):
            return False

        # Check if enabled flag is present and True
        # Field is inside effect_center: {"x": 50, "y": 50, "enabled": true}
        enabled = effect_center.get('enabled', False)
        return enabled is True

    def _get_device_center(self, device_controller) -> Tuple[float, float]:
        """
        Get custom effect center from device topology.

        Args:
            device_controller: Device controller (Linear1D or KeyboardMatrix2D)

        Returns:
            (center_x_pct, center_y_pct) in 0-100 range
        """
        if not hasattr(device_controller, '_topology'):
            return (50.0, 50.0)

        topology = device_controller._topology
        if not topology or not isinstance(topology, dict):
            return (50.0, 50.0)

        effect_center = topology.get('effect_center', {})
        if not effect_center:
            return (50.0, 50.0)

        # Read x, y percentages (default to 50% if missing)
        center_x = float(effect_center.get('x', 50.0))
        center_y = float(effect_center.get('y', 50.0))

        # Clamp to [0, 100] range
        center_x = max(0.0, min(100.0, center_x))
        center_y = max(0.0, min(100.0, center_y))

        return (center_x, center_y)

    def _load_global_effect_center(self) -> Optional[dict]:
        """Load global_effect_center from scene topology JSON (root level)."""
        try:
            from pathlib import Path as _Path
            import json as _json
            p = _Path('config/device_topologies.json')
            if p.exists():
                config = _json.loads(p.read_text(encoding='utf-8'))
                return config.get('global_effect_center')
        except Exception:
            pass
        return None

    def _compute_global_bbox(self) -> GlobalBoundingBox:
        """
        Compute global bbox using the scene global_effect_center when available.

        Priority:
        1. global_effect_center from scene topology JSON (enabled=True) → centered bbox for all LINEAR devices
        2. Per-device effect_center (single device, backward compat)
        3. Standard geometric bbox
        """
        # Priority 1: global scene center (applies across all LINEAR devices)
        global_center = self._load_global_effect_center()
        if global_center:
            cx = float(global_center.get('x', 50))
            cy = float(global_center.get('y', 50))
            return self._calculate_global_bbox_with_center(cx, cy)

        # Priority 2: per-device center (backward compat, single device only)
        if len(self.active_effects) == 1:
            device_id = list(self.active_effects.keys())[0]
            device_controller = self.active_effects[device_id].device_controller
            if self._has_custom_center(device_controller):
                center_x, center_y = self._get_device_center(device_controller)
                return self._calculate_global_bbox_with_center(center_x, center_y)

        # Priority 3: standard geometric bbox
        return self._calculate_global_bbox()

    def _get_normalized_coords(self, device_id: str, led_index: int) -> Tuple[float, float]:
        """
        Get normalized [0,1] coordinates for a specific LED.

        Args:
            device_id: Device identifier
            led_index: LED index within device

        Returns:
            (norm_x, norm_y) in [0,1] space
        """
        # Ensure global bbox is computed (with custom center if applicable)
        if self._global_bbox is None:
            self._global_bbox = self._compute_global_bbox()

        # Get device positions
        if device_id not in self.active_effects:
            return (0.5, 0.5)  # Fallback to center

        positions = self._get_device_world_positions(device_id, self.active_effects[device_id].device_controller)

        if led_index >= len(positions):
            return (0.5, 0.5)  # Fallback to center

        world_x, world_y = positions[led_index]

        # Normalize to [0,1]
        return self._global_bbox.normalize_point(world_x, world_y)

    def get_all_normalized_positions(self, device_id: str) -> List[Tuple[float, float, int]]:
        """
        Get normalized coordinates for ALL LEDs of a device.

        Args:
            device_id: Device identifier

        Returns:
            List of (norm_x, norm_y, led_index) tuples
        """
        if self._global_bbox is None:
            self._global_bbox = self._compute_global_bbox()

        if device_id not in self.active_effects:
            return []

        positions = self._get_device_world_positions(device_id, self.active_effects[device_id].device_controller)

        normalized = []
        for led_idx, (world_x, world_y) in enumerate(positions):
            norm_x, norm_y = self._global_bbox.normalize_point(world_x, world_y)
            normalized.append((norm_x, norm_y, led_idx))

        return normalized

    # ------------------------------------------------------------------
    # Effect control
    # ------------------------------------------------------------------

    def _cancel_effect(self, device_id: str):
        """
        Stop a running effect WITHOUT restoring LED state.

        Used by start_effect() when a new sequence preempts an existing one;
        the saved snapshot is intentionally kept.

        Order matters:
          1. Stop animation thread (no new frames added after this)
          2. Flush batcher → triggers device.set_colors() + update() → device.colors
             now reflects the last rendered frame (hardware truth)
          3. Unregister batcher (discard is now a no-op, batcher already empty)
        This ensures the next effect's FadeEffect reads current per-LED colors.
        """
        # Pop under lock so start_effect's cancel+assign is atomic vs render loop.
        with self._active_lock:
            active = self.active_effects.pop(device_id, None)
        if active is not None:
            if active.current_effect:
                try:
                    active.current_effect.stop()
                except Exception:
                    pass
            # Flush AFTER stop so no new frames are added during flush.
            # sync_colors=True: manually sync device.colors from sent data —
            # equivalent to fast=False but without the network round-trip.
            # FadeEffect2D reads device.colors at __init__ time to build
            # per-LED start colors for the next transition.
            self._io_batcher.flush(sync_colors=True)
            self._unregister_batcher(device_id, active.device_controller)

            # Invalidate global bbox cache (device set changed)
            self._global_bbox = None

    def stop_effect(self, device_id: str):
        """Stop an active Visual Effect and restore its LED state."""
        with self._active_lock:
            active = self.active_effects.pop(device_id, None)
        if active is None:
            return
        device_controller = active.device_controller
        simulator_mode = active.simulator_mode

        self._unregister_batcher(device_id, device_controller)

        if active.current_effect:
            try:
                active.current_effect.stop()
            except Exception:
                pass

        # Invalidate global bbox cache (device set changed)
        self._global_bbox = None
        # Remove cached world positions for this device — avoids stale entries
        # accumulating when devices are repeatedly stopped and restarted.
        self._device_world_positions.pop(device_id, None)

        if not simulator_mode:
            self._restore_led_state(device_id, device_controller)

    def stop_all(self):
        """Stop all active Visual Effects and restore every device's LED state."""
        for device_id in list(self.active_effects.keys()):
            self.stop_effect(device_id)
        self.running = False

    # ------------------------------------------------------------------
    # Error tracking (Tier 3 - Connection Lost Modal)
    # ------------------------------------------------------------------

    def _record_device_error(self, device_id: str, error: Exception):
        """Record error for threshold tracking."""
        if device_id not in self._device_errors:
            self._device_errors[device_id] = []

        # Add timestamp
        error._timestamp = time.time()
        self._device_errors[device_id].append(error)

        # Keep only last 10 errors
        self._device_errors[device_id] = self._device_errors[device_id][-10:]

    def _check_error_threshold(self, device_id: str) -> bool:
        """Check if device has exceeded error threshold."""
        if device_id not in self._device_errors:
            return False

        now = time.time()
        recent_errors = [
            err for err in self._device_errors[device_id]
            if hasattr(err, '_timestamp') and (now - err._timestamp) < self._error_window
        ]

        total_errors = len(self._device_errors[device_id])
        recent_count = len(recent_errors)
        threshold_met = recent_count >= self._error_threshold

        print(f"[Renderer] Threshold check for '{device_id}': {recent_count}/{self._error_threshold} "
              f"recent errors (total: {total_errors}, window: {self._error_window}s)")

        return threshold_met

    def _trigger_connection_lost_modal(self, affected_devices: List[str]):
        """
        Trigger Tier 3: Set flag for connection lost modal.
        Frontend polls this state via get_connection_lost_status() API.

        Args:
            affected_devices: List of device names that exceeded threshold
        """
        try:
            # NOTE: NO stop_all() call here - it blocks for ~1 minute on disconnected OpenRGB!
            # Effects should already be stopped by Tier 1 (after 5 consecutive errors).
            # self.stop_all()  # ← REMOVED: blocks for 1 minute on disconnected hardware

            # Set global flag via API (persists even after _manager invalidation)
            from api.effects_api import set_connection_lost_flag
            set_connection_lost_flag(True, affected_devices)

            print(f"[Renderer] Triggered connection lost flag (Tier 3) for {len(affected_devices)} devices")
            print(f"[Renderer] Frontend polling will detect this and show modal")

        except Exception as e:
            print(f"[Renderer] Failed to trigger connection lost flag: {e}")

    # ------------------------------------------------------------------
    # Step management
    # ------------------------------------------------------------------

    def _start_step(self, device_id: str, active: ActiveVisualEffect, step_idx: int):
        """Start a spatial effect for the given step with completion callback."""
        if step_idx >= len(active.spatial_effects):
            return

        # Lazy creation: build the spatial effect now so that effects like
        # FadeEffect (Static Transition) read device.colors at this moment —
        # after the previous step has flushed its final frame to hardware.
        if active.spatial_effects[step_idx] is None:
            step_to_create = active.visual_effect.steps[step_idx]
            try:
                active.spatial_effects[step_idx] = self._create_spatial_effect_from_step(
                    active.device_controller, step_to_create
                )
            except Exception as e:
                print(f"[Renderer] Error creating spatial effect for step {step_idx}: {e}")

        effect = active.spatial_effects[step_idx]
        step = active.visual_effect.steps[step_idx]
        dev_name = active.device_controller.topology.device.name
        n_steps = len(active.visual_effect.steps)

        from utils.log_buffer import log_led
        if not effect:
            # No effect for this step (e.g. keyboard_default on a non-MATRIX device):
            # fire completion immediately so the sequence advances without delay.
            log_led(dev_name, "step_skip",
                    f"step {step_idx+1}/{n_steps}  type={step.effect_type.value}  (not applicable for this topology)")
            active.step_start_time = time.time()
            completion_q = self._completion_queue
            wakeup = self._wakeup_event
            completion_q.put((device_id, step_idx))
            wakeup.set()
            return

        colors_repr = str(step.params.colors[:3])[:-1] + ("..." if len(step.params.colors) > 3 else "]")
        log_led(dev_name, "step_start",
                f"step {step_idx+1}/{n_steps}  type={step.effect_type.value}  "
                f"dur={step.params.duration_ms}ms  colors={colors_repr}")

        active.current_effect = effect
        active.step_start_time = time.time()

        completion_q = self._completion_queue
        wakeup = self._wakeup_event

        def _on_step_done():
            completion_q.put((device_id, step_idx))
            wakeup.set()

        effect.start(blocking=False, on_complete=_on_step_done)

    def _advance_step(self, device_id: str, active: ActiveVisualEffect):
        """
        Stop current effect and move to the next step (or complete the sequence).
        Must be called from the render-loop thread.

        Key ordering for sequence completion (non-simulator):
          1. Stop effect thread (if still running)
          2. Post post-behavior colors to batcher  <-- OVERWRITES final animation frame
          3. Flush batcher  <-- single device.set_colors() call, no timing race
          4. Unregister batcher from controller
        """
        if active.current_effect:
            try:
                active.current_effect.stop()
            except Exception:
                pass

        # Check for effect errors (Tier 3 trigger)
        if active.current_effect:
            if hasattr(active.current_effect, 'get_last_error'):
                last_error = active.current_effect.get_last_error()

                if last_error:
                    self._record_device_error(device_id, last_error)

                    if self._check_error_threshold(device_id):
                        print(f"[Renderer] ERROR THRESHOLD EXCEEDED for {device_id}")
                        self._trigger_connection_lost_modal([device_id])

        active.current_step_index += 1

        if active.current_step_index >= len(active.visual_effect.steps):
            # Sequence complete
            from utils.log_buffer import log_led
            dev_name = active.device_controller.topology.device.name
            post_b = active.visual_effect.post_behavior.value
            post_color = (active.visual_effect.post_behavior_data or {}).get("color")

            # If this MATRIX device ran a keyboard_default step, that step IS
            # already the intended final state (preset restored). Skip the
            # effect-level post-behavior so it doesn't overwrite the preset.
            _has_kbd_default = any(
                s.effect_type == BaseEffectType.KEYBOARD_DEFAULT
                for s in active.visual_effect.steps
            )
            _is_matrix = (
                active.device_controller.topology.topology_type == TopologyType.MATRIX
            )
            _skip_post_behavior = _is_matrix and _has_kbd_default

            log_led(dev_name, "sequence_complete",
                    f"post_behavior={post_b}  "
                    f"post_color={post_color if post_color else '(keep last frame)'}"
                    + ("  [skipped: keyboard_default is final state]" if _skip_post_behavior else ""))
            if not active.simulator_mode and not _skip_post_behavior:
                # 1. Post post-behavior to batcher BEFORE flush.
                #    Overwrites any pending final animation frame: single flush
                #    sends only the post-behavior color (no timing race).
                self._post_post_behavior_to_batcher(device_id, active)
                # fast=False: triggers update() round-trip so device.colors is
                # synchronised with the actual hardware state after the sequence.
                # Critical: FadeEffect2D reads device.colors as start_colors when
                # the NEXT effect begins — without this sync it reads stale colors
                # (e.g. violet even though the keyboard is now yellow).
                self._io_batcher.flush(sync_colors=True)
                # 2. Unregister batcher so future calls go directly to hardware.
                self._unregister_batcher(device_id, active.device_controller)
                # 3. Belt-and-suspenders: direct call after batcher is unregistered.
                #    Guarantees post-behavior even if batcher flush had an issue.
                self._apply_post_behavior_direct(device_id, active)
                self._saved_states.pop(device_id, None)
            else:
                self._io_batcher.flush()
                self._unregister_batcher(device_id, active.device_controller)

            return True  # Signal: remove from active_effects (on_complete called by render loop AFTER pop)
        else:
            # Non-final step: flush the completed step's final frame then start next.
            # fast=False: round-trip that synchronises device.colors with real hardware
            # state — critical so the next FadeEffect (Static Transition) reads the
            # correct per-LED start colors instead of stale pre-effect values.
            self._io_batcher.flush(sync_colors=True)
            self._start_step(device_id, active, active.current_step_index)
            return False

    # ------------------------------------------------------------------
    # Render loop
    # ------------------------------------------------------------------

    def _run_render_loop(self):
        """
        Main rendering loop.

        Each tick:
        1. Drain the completion queue → advance steps / restore immediately.
        2. Flush the IOBatcher → send all buffered frames in LED-count order.
        3. Fallback timeout check for effects whose callback was never fired.
        4. Sleep until next tick OR a completion event wakes us early.
        """
        while self.running and self.active_effects:

            # --- 1. Process callback-based completions ---
            devices_to_remove = []
            while True:
                try:
                    device_id, completed_step_idx = self._completion_queue.get_nowait()
                except queue.Empty:
                    break

                if device_id not in self.active_effects:
                    continue
                active = self.active_effects[device_id]
                # Guard: only process if this is still the current step
                if active.current_step_index != completed_step_idx:
                    continue
                if not active.visual_effect.steps[completed_step_idx].params.loop_infinite:
                    if self._advance_step(device_id, active):
                        devices_to_remove.append((device_id, active))
                else:
                    # loop_infinite=True: restart the same step indefinitely
                    self._start_step(device_id, active, active.current_step_index)

            for device_id, completed_active in devices_to_remove:
                self.active_effects.pop(device_id, None)
                # Call on_complete AFTER pop: any effect registered inside
                # on_complete (e.g. idle Disable Fade) won't be wiped by this pop.
                if completed_active.on_complete:
                    try:
                        completed_active.on_complete()
                    except Exception as e:
                        print(f"[Renderer] on_complete error for {device_id}: {e}")

            # --- 2. Flush IOBatcher (keyboard first) ---
            self._io_batcher.flush()

            # --- 2b. Process flush errors for Tier 3 tracking ---
            flush_errors = self._io_batcher.get_and_clear_recent_errors()
            if flush_errors:
                # Record all errors first
                for device_identifier, error in flush_errors:
                    self._record_device_error(device_identifier, error)

                # Calculate GLOBAL error count (all devices combined)
                now = time.time()
                global_recent_errors = []
                for device_id, errors in self._device_errors.items():
                    recent = [
                        err for err in errors
                        if hasattr(err, '_timestamp') and (now - err._timestamp) < self._error_window
                    ]
                    global_recent_errors.extend(recent)

                global_error_count = len(global_recent_errors)
                print(f"[Renderer] Global error count: {global_error_count}/{self._error_threshold} "
                      f"(window: {self._error_window}s, across {len(self._device_errors)} devices)")

                # Trigger Tier 3 modal if GLOBAL threshold exceeded
                if global_error_count >= self._error_threshold:
                    from datetime import datetime
                    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    affected_devices = list(self._device_errors.keys())
                    print(f"[{ts}] [Renderer] [WARNING] THRESHOLD EXCEEDED! "
                          f"({global_error_count}/{self._error_threshold}) "
                          f"Affected: {', '.join(affected_devices)}")
                    self._trigger_connection_lost_modal(affected_devices)
                    # Stop processing - modal will handle user interaction
                    break
                else:
                    print(f"[Renderer] Global threshold not exceeded yet ({global_error_count}/{self._error_threshold})")

            # --- 3. Fallback timeout check ---
            current_time = time.time()
            devices_to_remove = []  # list of (device_id, active)

            with self._active_lock:
                active_snapshot = list(self.active_effects.items())
            for device_id, active in active_snapshot:
                try:
                    current_step = active.visual_effect.steps[active.current_step_index]
                    elapsed_ms = (current_time - active.step_start_time) * 1000

                    if active.simulator_mode and self.simulator_callback:
                        self._update_simulator(device_id, active)

                    if current_step.params.loop_infinite:
                        continue

                    # Use the spatial effect's actual duration (e.g. for Breath
                    # with num_loops > 1: actual = cycle_ms * loop_count).
                    # For LOOP_EFFECT the looped effect has duration_ms=999999999
                    # so the timeout never fires.
                    if active.current_effect:
                        effect_duration_ms = active.current_effect.duration_ms or 1000
                    else:
                        effect_duration_ms = current_step.params.duration_ms or 1000
                    timeout_ms = effect_duration_ms + self._STEP_TIMEOUT_MARGIN_MS
                    if elapsed_ms >= timeout_ms:
                        # Callback was never fired; advance by fallback
                        print(
                            f"[Renderer] Fallback timeout for {device_id} "
                            f"step {active.current_step_index} "
                            f"({elapsed_ms:.0f}ms >= {timeout_ms:.0f}ms)"
                        )
                        if self._advance_step(device_id, active):
                            devices_to_remove.append((device_id, active))

                except Exception as e:
                    print(f"[Renderer] render loop error for {device_id}: {e}")
                    devices_to_remove.append((device_id, None))

            for device_id, completed_active in devices_to_remove:
                # Identity check: don't pop a NEW effect that replaced the completed one.
                with self._active_lock:
                    if self.active_effects.get(device_id) is completed_active:
                        self.active_effects.pop(device_id, None)
                if completed_active and completed_active.on_complete:
                    try:
                        completed_active.on_complete()
                    except Exception as e:
                        print(f"[Renderer] on_complete error for {device_id}: {e}")

            # --- 4. Sleep until next tick or early wakeup ---
            self._wakeup_event.wait(timeout=1.0 / self.fps)
            self._wakeup_event.clear()

        self.running = False

    # ------------------------------------------------------------------
    # Simulator support
    # ------------------------------------------------------------------

    def _update_simulator(self, device_id: str, active: ActiveVisualEffect):
        """Update simulator with current LED colors."""
        try:
            controller = active.device_controller.controller
            topology = active.device_controller.topology

            if hasattr(controller, 'get_current_colors'):
                color_map = controller.get_current_colors()
                if hasattr(topology, 'matrix_map') and topology.matrix_map:
                    self.simulator_callback(color_map, topology.matrix_map)
                else:
                    self.simulator_callback(color_map, None)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Spatial effect factory
    # ------------------------------------------------------------------

    def _create_spatial_effect_from_step(self, device_controller, step: BaseEffectStep):
        """Create a spatial effect instance from a Base Effect Step."""
        effect_type = step.effect_type
        params = step.params
        topology = device_controller.topology.topology_type

        if topology == TopologyType.MATRIX:
            return self._create_2d_effect(device_controller, effect_type, params)
        elif topology == TopologyType.LINEAR:
            return self._create_1d_effect(device_controller, effect_type, params)
        else:
            return self._create_1d_effect(device_controller, effect_type, params)

    def _create_2d_effect(self, device_controller, effect_type: BaseEffectType, params):
        """Create 2D spatial effect for keyboards."""
        matrix = device_controller.controller
        duration = params.duration_ms
        colors = params.colors
        primary_color = colors[0] if colors else (255, 255, 255)

        if effect_type == BaseEffectType.STATIC_TRANSITION:
            # FadeEffect2D reads per-LED start colors from matrix.device.colors internally.
            # Ensure device.colors is current before calling (see _cancel_effect fix).
            effect = FadeEffect2D(matrix, duration, end_color=primary_color)

        elif effect_type == BaseEffectType.BREATH:
            color1 = colors[0] if len(colors) > 0 else (255, 255, 255)
            color2 = colors[1] if len(colors) > 1 else (0, 0, 0)
            loop_count = params.num_loops or 1
            effect = BreathEffect2D(matrix, duration, color1=color1, color2=color2,
                                  loop_count=loop_count)

        elif effect_type == BaseEffectType.COLOR_CYCLE:
            direction = params.direction or "left"
            speed = params.speed if params.speed is not None else 1.0
            effect = ColorCycleEffect2D(
                matrix,
                duration,
                colors=colors,
                direction=direction,
                speed=speed
            )

        elif effect_type == BaseEffectType.TWO_COLOR_NUANCE:
            color1 = colors[0] if len(colors) > 0 else (255, 255, 255)
            color2 = colors[1] if len(colors) > 1 else (0, 0, 0)
            direction = params.direction or "right"
            effect = GradientEffect2D(
                matrix,
                duration,
                color1=color1,
                color2=color2,
                direction=direction
            )

        elif effect_type == BaseEffectType.FOUR_CORNER_NUANCE:
            color_tl = colors[0] if len(colors) > 0 else (255, 0, 0)
            color_tr = colors[1] if len(colors) > 1 else (0, 255, 0)
            color_bl = colors[2] if len(colors) > 2 else (255, 255, 0)
            color_br = colors[3] if len(colors) > 3 else (0, 0, 255)
            effect = CornerGradientEffect2D(
                matrix,
                duration,
                color_tl=color_tl,
                color_tr=color_tr,
                color_br=color_br,
                color_bl=color_bl
            )

        elif effect_type == BaseEffectType.BLOOM:
            expansion_factor = params.expansion_factor if params.expansion_factor is not None else 2.0
            effect = BloomEffect(matrix, duration,
                               colors=colors if colors else None,
                               expansion_factor=expansion_factor)

        elif effect_type == BaseEffectType.EXPLOSION:
            ring_width = params.ring_width if params.ring_width is not None else 0.1
            decay_rate = params.decay_rate if params.decay_rate is not None else 0.4
            expansion_factor = params.expansion_factor if params.expansion_factor is not None else 2.0
            effect = ExplosionEffect(matrix, duration,
                                   colors=colors if colors else None,
                                   ring_width=ring_width,
                                   decay_rate=decay_rate,
                                   expansion_factor=expansion_factor)

        elif effect_type == BaseEffectType.WAVE:
            color_peak = colors[0] if len(colors) > 0 else (255, 128, 0)
            color_bg   = colors[1] if len(colors) > 1 else (0, 0, 0)
            direction  = params.direction or "right"
            num_loops  = params.num_loops or 1
            effect = WaveEffect(matrix, duration, color=color_peak, color_bg=color_bg,
                              direction=direction, wavelength=params.speed or 8.0,
                              num_loops=num_loops)

        elif effect_type == BaseEffectType.BUMP:
            color_bg   = colors[0] if len(colors) > 0 else (0, 0, 0)      # Color 1 = edges
            color_peak = colors[1] if len(colors) > 1 else (255, 128, 0)  # Color 2 = center
            direction  = params.direction or "right"
            num_loops  = params.num_loops or 1
            effect = BumpEffect2D(matrix, duration, color=color_peak, color_bg=color_bg,
                                direction=direction, num_loops=num_loops)

        elif effect_type == BaseEffectType.GLITCH:
            base_color    = colors[0] if len(colors) > 0 else (0, 0, 255)
            glitch_colors = colors[1:4] if len(colors) > 1 else None
            effect = GlitchEffect2D(
                matrix,
                duration_ms=duration,
                base_color=base_color,
                glitch_colors=glitch_colors if glitch_colors else None,
                glitch_percentage=params.glitch_percentage or 0.15,
                glitch_duration_ms=params.glitch_duration_ms or 150,
                duration_variability=params.duration_variability or 0.5,
                persistence_percentage=params.persistence_percentage or 0.3,
                color_variation=params.color_variation or 0.2,
            )

        elif effect_type == BaseEffectType.FIRE:
            effect = FireEffect2D(matrix, params)

        elif effect_type == BaseEffectType.MATRIX_RAIN:
            effect = MatrixRainEffect2D(matrix, params)

        elif effect_type == BaseEffectType.OCEAN_WAVES:
            effect = OceanWavesEffect2D(matrix, params)

        elif effect_type == BaseEffectType.PLASMA:
            effect = PlasmaEffect2D(matrix, params)

        elif effect_type == BaseEffectType.AURORA:
            effect = AuroraEffect2D(matrix, params)

        elif effect_type == BaseEffectType.PARALLAX_STARS:
            effect = ParallaxStarsEffect2D(matrix, params)

        elif effect_type == BaseEffectType.LIGHTNING:
            effect = LightningEffect2D(matrix, params)

        elif effect_type == BaseEffectType.DIRECTIONAL_FLASH:
            color_bg  = colors[0] if len(colors) > 0 else (20, 0, 0)
            color_hit = colors[1] if len(colors) > 1 else (255, 20, 0)
            direction = params.direction or 'right'
            num_loops = params.num_loops or 1
            effect = DirectionalFlashEffect(
                matrix, duration,
                color_bg=tuple(color_bg), color_hit=tuple(color_hit),
                direction=direction, num_loops=num_loops
            )

        elif effect_type == BaseEffectType.KEYBOARD_DEFAULT:
            preset_id = params.direction or '1'
            from effects.spatial_effects_2d import KeyboardPresetEffect

            if preset_id == 'fill':
                # Solid fill: use params.colors[0] as the uniform colour.
                # target_colors covers every valid LED in the matrix.
                fill_rgb = tuple(params.colors[0]) if params.colors else (255, 102, 0)
                target_colors = {
                    led_idx: fill_rgb
                    for led_idx in matrix.led_to_coord.keys()
                }
            else:
                # Load a saved preset (P1 / P2 / P3) from keyboard_presets.json
                target_colors = _load_keyboard_preset_colors(preset_id)

            effect = KeyboardPresetEffect(matrix, params.duration_ms or 800, target_colors)

        else:
            raise ValueError(f"Unknown base effect type: {effect_type}")

        # Inject fade-in parameter if applicable (skip effects with intrinsic fade)
        if params.fade_in_ms and effect_type not in _EFFECTS_WITH_INTRINSIC_FADE:
            effect.fade_in_ms = params.fade_in_ms

        return effect

    def _create_1d_effect(self, device_controller, effect_type: BaseEffectType, params):
        """Create 1D spatial effect for linear devices."""
        linear = device_controller.controller
        duration = params.duration_ms
        colors = params.colors
        primary_color = colors[0] if colors else (255, 255, 255)

        # KEYBOARD_DEFAULT is a keyboard-only concept (restore preset via
        # KeyboardPresetEffect on MATRIX devices).  On LINEAR/strip/mouse devices
        # there is no preset to restore, so this step is a no-op: returning None
        # causes _start_step() to skip it immediately and let the post-behavior
        # (configured per-effect in the editor) define the final device color.
        if effect_type == BaseEffectType.KEYBOARD_DEFAULT:
            return None

        if effect_type == BaseEffectType.STATIC_TRANSITION:
            # FadeEffect1D reads per-LED start colors from linear.device.colors internally.
            effect = FadeEffect1D(linear, duration, end_color=primary_color)

        elif effect_type == BaseEffectType.BREATH:
            color1 = colors[0] if len(colors) > 0 else (255, 255, 255)
            color2 = colors[1] if len(colors) > 1 else (0, 0, 0)
            loop_count = params.num_loops or 1
            effect = BreathEffect1D(linear, duration, color1=color1, color2=color2,
                                  loop_count=loop_count)

        elif effect_type == BaseEffectType.COLOR_CYCLE:
            direction = params.direction or "forward"
            speed = params.speed if params.speed is not None else 1.0
            effect = ColorCycleEffect1D(
                linear,
                duration,
                colors=colors,
                direction=direction,
                speed=speed,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.TWO_COLOR_NUANCE:
            color1 = colors[0] if len(colors) > 0 else (255, 255, 255)
            color2 = colors[1] if len(colors) > 1 else (0, 0, 0)
            direction = params.direction or 'right'
            effect = GradientShiftEffect1D(
                linear, duration,
                color1=color1,
                color2=color2,
                direction=direction,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.FOUR_CORNER_NUANCE:
            from effects.spatial_effects_1d import CornerGradientEffect1D
            color_tl = colors[0] if len(colors) > 0 else (255, 0, 0)
            color_tr = colors[1] if len(colors) > 1 else (0, 255, 0)
            color_bl = colors[2] if len(colors) > 2 else (255, 255, 0)
            color_br = colors[3] if len(colors) > 3 else (0, 0, 255)
            effect = CornerGradientEffect1D(
                linear, duration,
                color_tl=color_tl,
                color_tr=color_tr,
                color_br=color_br,
                color_bl=color_bl
            )

        elif effect_type == BaseEffectType.DIRECTIONAL_FLASH:
            from effects.spatial_effects_1d import DirectionalFlashEffect1D
            color_bg = colors[0] if len(colors) > 0 else (20, 0, 0)
            color_hit = colors[1] if len(colors) > 1 else (255, 20, 0)
            direction = params.direction or 'right'
            num_loops = params.num_loops or 1
            effect = DirectionalFlashEffect1D(
                linear, duration,
                color_bg=tuple(color_bg), color_hit=tuple(color_hit),
                direction=direction, num_loops=num_loops,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.BLOOM:
            from effects.spatial_effects_1d import BloomEffect1D
            expansion_factor = params.expansion_factor if params.expansion_factor is not None else 2.0
            _gc = self._load_global_effect_center()
            _cx = _gc.get('x', 50) / 100.0 if _gc else None
            _cy = _gc.get('y', 50) / 100.0 if _gc else None
            effect = BloomEffect1D(linear, duration, colors=colors if colors else None,
                                 expansion_factor=expansion_factor,
                                 use_normalized=True,
                                 center_x=_cx, center_y=_cy)

        elif effect_type == BaseEffectType.EXPLOSION:
            from effects.spatial_effects_1d import ExplosionEffect1D
            ring_width = params.ring_width if params.ring_width is not None else 0.1  # QUICK WIN: narrower ring
            decay_rate = params.decay_rate if params.decay_rate is not None else 0.4
            expansion_factor = params.expansion_factor if params.expansion_factor is not None else 2.0
            _gc = self._load_global_effect_center()
            _cx = _gc.get('x', 50) / 100.0 if _gc else None
            _cy = _gc.get('y', 50) / 100.0 if _gc else None
            effect = ExplosionEffect1D(
                linear, duration,
                colors=colors if colors else None,
                ring_width=ring_width,
                decay_rate=decay_rate,
                expansion_factor=expansion_factor,
                use_normalized=True,
                center_x=_cx, center_y=_cy
            )

        elif effect_type == BaseEffectType.WAVE:
            from effects.spatial_effects_1d import WaveEffect1D
            color = colors[0] if len(colors) > 0 else (255, 128, 0)
            color_bg = colors[1] if len(colors) > 1 else (0, 0, 0)
            direction = params.direction or "horizontal"
            wavelength = params.speed if params.speed is not None else 4.0
            speed = 1.0  # Default speed for 1D wave
            effect = WaveEffect1D(
                linear, duration,
                color=color,
                color_bg=color_bg,
                wavelength=wavelength,
                speed=speed,
                direction=direction,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.BUMP:
            from effects.spatial_effects_1d import BumpEffect1D
            color = colors[0] if len(colors) > 0 else (255, 128, 0)
            color_bg = colors[1] if len(colors) > 1 else (0, 0, 0)
            direction = params.direction or "right"
            num_loops = params.num_loops or 1
            effect = BumpEffect1D(
                linear, duration,
                color=color,
                color_bg=color_bg,
                direction=direction,
                num_loops=num_loops,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.OCEAN_WAVES:
            from effects.spatial_effects_1d import OceanWavesEffect1D
            speed = params.speed if params.speed is not None else 1.0
            effect = OceanWavesEffect1D(
                linear, duration,
                colors=colors if len(colors) >= 3 else None,
                speed=speed,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.FIRE:
            from effects.spatial_effects_1d import FireEffect1D
            intensity = params.intensity if params.intensity is not None else 0.85
            direction = params.direction if params.direction else 'down'
            effect = FireEffect1D(
                linear, duration,
                colors=colors if len(colors) >= 2 else None,
                intensity=intensity,
                direction=direction,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.GLITCH:
            from effects.spatial_effects_1d import GlitchEffect1D
            base_color = colors[0] if len(colors) > 0 else (0, 0, 255)
            glitch_colors = colors[1:4] if len(colors) > 1 else None
            effect = GlitchEffect1D(
                linear, duration,
                base_color=base_color,
                glitch_colors=glitch_colors,
                glitch_percentage=params.intensity if params.intensity else 0.15
                # Note: GlitchEffect1D doesn't use coordinates, so use_normalized is not applicable
            )

        elif effect_type == BaseEffectType.MATRIX_RAIN:
            from effects.spatial_effects_1d import MatrixRainEffect1D
            color_off = colors[0] if len(colors) > 0 else (0, 0, 0)
            color_trail = colors[1] if len(colors) > 1 else (0, 64, 0)
            color_head = colors[2] if len(colors) > 2 else (0, 255, 70)
            effect = MatrixRainEffect1D(
                linear, duration,
                color_off=color_off,
                color_trail=color_trail,
                color_head=color_head,
                density=params.density if params.density else 1.0,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.AURORA:
            from effects.spatial_effects_1d import AuroraEffect1D
            effect = AuroraEffect1D(
                linear, duration,
                colors=colors if len(colors) > 0 else None,
                height=params.height if params.height else 0.45,
                tail_length=params.tail_length if params.tail_length else 0.7,
                wave_frequency=params.wave_frequency if params.wave_frequency else 0.8,
                ripple=params.ripple if params.ripple else 0.3,
                speed=params.speed if params.speed else 0.5,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.PARALLAX_STARS:
            from effects.spatial_effects_1d import ParallaxStarsEffect1D
            effect = ParallaxStarsEffect1D(
                linear, duration,
                colors=colors if len(colors) > 0 else None,
                speed=params.speed if params.speed else 9.0,
                density=params.density if params.density else 1.0,
                direction=params.direction if params.direction else 'left',
                use_normalized=True
            )

        elif effect_type == BaseEffectType.LIGHTNING:
            from effects.spatial_effects_1d import LightningEffect1D
            color_sky = colors[0] if len(colors) > 0 else (5, 5, 20)
            color_bolt = colors[1] if len(colors) > 1 else (255, 255, 255)
            # Always use normalized coords for 1D devices: world-space Y-span is 0
            # for flat linear strips (all LEDs at same Y), which would trigger fallback.
            effect = LightningEffect1D(
                linear, duration,
                color_sky=color_sky,
                color_bolt=color_bolt,
                bolt_interval_ms=params.bolt_interval_ms if params.bolt_interval_ms else 2000,
                use_normalized=True
            )

        elif effect_type == BaseEffectType.PLASMA:
            from effects.spatial_effects_1d import PlasmaEffect1D
            effect = PlasmaEffect1D(
                linear, duration,
                colors=colors if len(colors) > 0 else None,
                speed=params.speed if params.speed else 1.0,
                wave_weights=params.wave_weights if params.wave_weights else None,
                use_normalized=True
            )

        else:
            raise ValueError(f"Unknown base effect type: {effect_type}")

        # Inject fade-in parameter if applicable (skip effects with intrinsic fade)
        if params.fade_in_ms and effect_type not in _EFFECTS_WITH_INTRINSIC_FADE:
            effect.fade_in_ms = params.fade_in_ms

        return effect

    # ------------------------------------------------------------------
    # Coordinate Normalization Helper Methods
    # ------------------------------------------------------------------

    def _calculate_global_bbox(self, device_controller) -> dict:
        """
        Calculate global bounding box for device LED positions.

        For now, returns bbox for single device. In future, will support
        multi-device topologies from device_topologies.json.

        Args:
            device_controller: Device controller with topology info

        Returns:
            dict with keys: min_x, max_x, min_y, max_y (in LED units)
        """
        topology = device_controller.topology

        if topology.topology_type == TopologyType.MATRIX:
            # For keyboards: matrix_map is [rows][cols]
            rows, cols = topology.dimensions
            return {
                'min_x': 0,
                'max_x': cols,
                'min_y': 0,
                'max_y': rows
            }
        elif topology.topology_type == TopologyType.LINEAR:
            # For linear devices: all LEDs along X axis
            led_count = topology.led_count
            return {
                'min_x': 0,
                'max_x': led_count,
                'min_y': 0,
                'max_y': 1  # Height of 1 LED unit
            }
        else:
            # SINGLE or UNKNOWN: treat as single point
            return {
                'min_x': 0,
                'max_x': 1,
                'min_y': 0,
                'max_y': 1
            }

    def _get_normalized_coords(self, device_controller, led_index: int) -> Tuple[float, float]:
        """
        Get LED position in normalized 0-1 coordinates.

        Coordinates are relative to device bounding box:
        - (0.0, 0.0) = bottom-left of bbox
        - (1.0, 1.0) = top-right of bbox

        Args:
            device_controller: Device controller with topology info
            led_index: LED index within device

        Returns:
            (norm_x, norm_y) tuple where 0.0 <= norm_x, norm_y <= 1.0
        """
        topology = device_controller.topology
        bbox = self._calculate_global_bbox(device_controller)

        bbox_width = bbox['max_x'] - bbox['min_x']
        bbox_height = bbox['max_y'] - bbox['min_y']

        # Avoid division by zero
        if bbox_width == 0:
            bbox_width = 1
        if bbox_height == 0:
            bbox_height = 1

        if topology.topology_type == TopologyType.MATRIX:
            # Find LED position in matrix_map
            matrix_map = topology.matrix_map
            if not matrix_map:
                return (0.5, 0.5)  # Fallback to center

            # Search for led_index in matrix_map
            for row_idx, row in enumerate(matrix_map):
                for col_idx, led_id in enumerate(row):
                    if led_id == led_index:
                        # Convert to normalized coords
                        # X: column position (left to right)
                        # Y: row position (bottom to top, so invert)
                        rows = len(matrix_map)
                        norm_x = (col_idx - bbox['min_x']) / bbox_width
                        norm_y = ((rows - 1 - row_idx) - bbox['min_y']) / bbox_height
                        return (norm_x, norm_y)

            # LED not found in matrix_map - fallback
            return (0.5, 0.5)

        elif topology.topology_type == TopologyType.LINEAR:
            # Linear: LED index is X position, Y is always center (0.5)
            norm_x = (led_index - bbox['min_x']) / bbox_width
            norm_y = 0.5  # Center of 1-unit height
            return (norm_x, norm_y)

        else:
            # SINGLE or UNKNOWN: center point
            return (0.5, 0.5)

    # ------------------------------------------------------------------
    # Post-sequence behavior
    # ------------------------------------------------------------------

    def _post_post_behavior_to_batcher(self, device_id: str, active: ActiveVisualEffect):
        """
        Post post-sequence behavior colors directly to the IOBatcher.

        Calling this BEFORE flush() overwrites any pending animation frame in the
        batcher buffer. The subsequent flush() sends only the post-behavior color
        via a single device.set_colors() call — eliminating the timing race.

        CRITICAL FIX: If no explicit post_behavior color is configured and the
        batcher is empty (because render loop already flushed with fast=True),
        re-post the current hardware colors to ensure the subsequent flush(sync_colors=True)
        performs a hardware sync, preventing residual LED colors.
        """
        data = active.visual_effect.post_behavior_data or {}
        device = active.device_controller.controller.device
        n = len(device.colors)

        try:
            raw = data.get("color")
            if raw is not None:
                # Explicit static color configured: override final animation frame.
                from utils.log_buffer import log_led
                log_led(device.name, "post_batcher_explicit",
                        f"setting {n} LEDs to RGB({int(raw[0])},{int(raw[1])},{int(raw[2])})")
                c = RGBColor(int(raw[0]), int(raw[1]), int(raw[2]))
                self._io_batcher.post(device_id, n, device, [c] * n)
            else:
                # No explicit color: force hardware state sync directly.
                from utils.log_buffer import log_led
                log_led(device.name, "post_batcher_sync",
                        f"reading current hardware state for {n} LEDs (no explicit color)")
                # Problem: batcher was flushed with fast=True (fire-and-forget), so
                # device.colors is stale (doesn't reflect the final black frame yet).
                # Solution: Force device.update() to read actual hardware state, then
                # re-post to batcher so flush(sync_colors=True) can sync correctly.
                import time
                # Check frame presence under lock (fast, no I/O)
                needs_sync = False
                with self._io_batcher._lock:
                    needs_sync = device_id not in self._io_batcher._frames

                if needs_sync:
                    # Give hardware 100ms to process the fast=True command
                    # (USB latency + firmware processing can vary).
                    # Sleep and device.update() are OUTSIDE the lock — holding
                    # the lock for 100ms would block all effect threads from
                    # posting frames (~30x/sec each), causing a visible LED freeze.
                    time.sleep(0.1)
                    try:
                        # Force read actual hardware colors (including final black frame)
                        device.update()
                    except Exception:
                        pass
                    # Re-acquire lock only to write the frame
                    with self._io_batcher._lock:
                        self._io_batcher._frames[device_id] = (n, device, list(device.colors))
        except Exception as e:
            print(f"[Renderer] Error posting post-behavior to batcher: {e}")

    def _apply_post_behavior_direct(self, device_id: str, active: ActiveVisualEffect):
        """
        Direct fallback post-behavior call, executed AFTER the batcher is
        unregistered.  Since _frame_intercept is None at this point, the
        controller routes the call straight to device.set_color() — no batcher
        involved.  This guarantees the post-behavior is applied even if the
        batcher flush silently failed (e.g. length mismatch, exception).
        """
        data = active.visual_effect.post_behavior_data or {}
        controller = active.device_controller.controller
        device_name = active.device_controller.topology.device.name
        from utils.log_buffer import log_led
        try:
            color = data.get("color")
            if color is not None:
                # Explicit static color configured: apply it as belt-and-suspenders.
                log_led(device_name, "post_direct_apply",
                        f"RGB({int(color[0])},{int(color[1])},{int(color[2])})")
                controller.set_all_leds(tuple(int(c) for c in color))
            else:
                log_led(device_name, "post_direct_skip",
                        "no explicit color — keeping last animation frame")
        except Exception as e:
            print(f"[Renderer] Error in direct post-behavior fallback: {e}")
