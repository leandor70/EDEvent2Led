"""
Spatial 1D effects for linear LED devices with color override support.

These effects define HOW light moves across 1D linear devices (RAM, strips, mice).
They support dynamic color override from keyframe interpolation in fused effects.
"""
import time
import math
import threading
import random
from typing import Tuple, Optional, List
from utils.openrgb_client import RGBColor
from .linear_1d import Linear1D
from utils.color_utils import lerp_color as _lerp_color_util, hsv_to_rgb as _hsv_to_rgb_util


class Animated1DEffect:
    """Base class for animated 1D spatial effects."""

    def __init__(self, linear: Linear1D, duration_ms: int, fps: int = 30):
        """
        Initialize animated effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration in milliseconds
            fps: Frames per second
        """
        self.linear = linear
        self.duration_ms = duration_ms
        self.fps = fps
        self.frame_time_ms = 1000 / fps
        self.running = False
        self.thread = None
        self.current_color = None  # Color override from fused effect keyframes
        self.fade_in_ms = 0  # To be set externally by the renderer
        self._initial_colors: Optional[dict] = None  # Lazy-loaded initial LED colors for fade-in

        # Exception handling for thread safety
        self._last_error: Optional[Exception] = None
        self._consecutive_errors = 0
        self._max_consecutive_errors = 5  # Stop after 5 consecutive errors

    def get_last_error(self) -> Optional[Exception]:
        """Get last error that occurred during rendering (thread-safe)."""
        return self._last_error

    def _ensure_initial_colors(self):
        """Capture initial LED colors from hardware (lazy init on first frame)."""
        if self._initial_colors is None and self.fade_in_ms > 0:
            try:
                # Read current LED colors from hardware
                device_colors = self.linear.device.colors
                # Convert to dict: led_idx -> (r, g, b)
                self._initial_colors = {
                    idx: (c.red, c.green, c.blue)
                    for idx, c in enumerate(device_colors)
                }
            except (AttributeError, IndexError):
                # Fallback: if device.colors not available, assume black
                self._initial_colors = {}

    def _apply_color_map(self, color_map: dict, time_ms: int):
        """Helper to apply colors to the linear strip with automatic fade-in logic.

        When fade_in_ms > 0 and still inside the fade window, interpolates
        linearly between initial LED colors and target effect colors.
        """
        if self.fade_in_ms > 0 and time_ms < self.fade_in_ms:
            # Ensure we have initial colors (lazy init on first frame)
            self._ensure_initial_colors()

            # Calculate fade progress (0.0 = initial, 1.0 = full effect)
            progress = time_ms / self.fade_in_ms

            # Interpolate between initial colors and target colors
            faded_map = {}
            for led_idx, (target_r, target_g, target_b) in color_map.items():
                # Get initial color for this LED (default to black if not found)
                initial = self._initial_colors.get(led_idx, (0, 0, 0))
                init_r, init_g, init_b = initial

                # Linear interpolation: initial * (1 - progress) + target * progress
                faded_map[led_idx] = (
                    int(init_r + (target_r - init_r) * progress),
                    int(init_g + (target_g - init_g) * progress),
                    int(init_b + (target_b - init_b) * progress),
                )

            self.linear.apply_color_map(faded_map)
        else:
            self.linear.apply_color_map(color_map)

    def set_color(self, color: Optional[Tuple[int, int, int]]):
        """
        Set color override for this effect.
        When set, this color overrides the base_color during rendering.

        Args:
            color: RGB tuple (0-255) or None to use base_color
        """
        self.current_color = color

    def render_frame(self, time_ms: int):
        """
        Render a single frame at given time.
        Override this in subclasses.

        Args:
            time_ms: Current time in milliseconds from start
        """
        pass

    def start(self, blocking: bool = False, on_complete: Optional[callable] = None):
        """
        Start the effect animation.

        Args:
            blocking: If True, blocks until effect completes
            on_complete: Callback function to call when effect finishes
        """
        if self.running:
            return

        self.running = True

        if blocking:
            self._run_animation(on_complete)
        else:
            self.thread = threading.Thread(target=self._run_animation, args=(on_complete,), daemon=True)
            self.thread.start()

    def _run_animation(self, on_complete: Optional[callable] = None):
        """Internal animation loop with exception handling."""
        from utils.openrgb_client import OpenRGBDisconnected

        if not self.duration_ms:
            self.duration_ms = 1000  # guard against None/0
        start_time = time.time()
        frame_count = 0

        while self.running:
            try:
                elapsed_ms = (time.time() - start_time) * 1000

                if elapsed_ms >= self.duration_ms:
                    # Render the exact final frame BEFORE breaking to ensure precise timing
                    self.render_frame(self.duration_ms)

                    # Call completion callback immediately
                    if on_complete:
                        on_complete()
                    break

                self.render_frame(elapsed_ms)

                # Reset error counter on successful frame
                self._consecutive_errors = 0

                # Sleep to maintain target FPS
                frame_count += 1
                expected_time = frame_count * self.frame_time_ms / 1000
                actual_time = time.time() - start_time
                sleep_time = max(0, expected_time - actual_time)

                if sleep_time > 0:
                    time.sleep(sleep_time)

            except OpenRGBDisconnected as e:
                self._last_error = e
                self._consecutive_errors += 1

                print(f"[Effect] Disconnect in frame {frame_count} "
                      f"(errors: {self._consecutive_errors})")

                if self._consecutive_errors >= self._max_consecutive_errors:
                    print(f"[Effect] Stopping after {self._max_consecutive_errors} errors")
                    self.running = False

                    # CRITICAL: Always call on_complete even on error
                    if on_complete:
                        on_complete()
                    break

                time.sleep(0.1)  # Let reconnection happen

            except Exception as e:
                self._last_error = e
                self._consecutive_errors += 1
                print(f"[Effect] Error in frame {frame_count}: {e}")

                if self._consecutive_errors >= self._max_consecutive_errors:
                    self.running = False
                    if on_complete:
                        on_complete()
                    break

                time.sleep(0.1)

        self.running = False

    def stop(self):
        """Stop the effect animation.

        Sets running=False and returns immediately. The daemon thread will exit
        at the next loop iteration (within one frame time, ~33ms at 30fps).
        No join() needed: the render loop's batcher unregister+discard ensures
        any frames posted after stop() are dropped before delivery.
        """
        self.running = False


class WaveEffect1D(Animated1DEffect):
    """
    Sine wave animation with topology support.

    Wave propagates as a planar wavefront through 2D world space
    in the specified direction. For multi-segment LED strips, the
    wave respects the spatial layout defined in topology.

    Interpolates between color_bg (background) and color (wave peak).
    """

    def __init__(self, linear: Linear1D, duration_ms: int = 3000,
                 color: Tuple[int, int, int] = (255, 128, 0),
                 color_bg: Tuple[int, int, int] = (0, 0, 0),
                 wavelength: float = 4.0, speed: float = 1.0,
                 direction: str = "horizontal",
                 use_normalized: bool = True):
        """
        Initialize topology-aware wave effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: Wave peak RGB color
            color_bg: Background RGB color
            wavelength: Wave period (in world coordinate units if use_normalized=False,
                       in normalized [0,1] units if use_normalized=True)
            speed: Wave speed (wavelengths per second)
            direction: Wave direction - "horizontal"/"right", "left",
                      "vertical"/"down", "top", "tl", "tr", "bl", "br"
            use_normalized: If True, use normalized [0,1] coordinates (Phase 1.1)
        """
        super().__init__(linear, duration_ms)
        self.base_color = color
        self.color_bg = color_bg
        self.wavelength = wavelength
        self.speed = speed
        self.direction = direction
        self.use_normalized = use_normalized

        # Get global bounding box for world coordinate calculations
        self.bbox = self.linear.get_global_bbox()

    def _calculate_wave_position(self, world_x: float, world_y: float, zone_idx: int, local_idx: int) -> float:
        """
        Calculate wave position for a world coordinate in GLOBAL wave mode.

        For global wave behavior: the wave propagates continuously across the entire
        2D layout (bbox). get_led_world_position() already handles segment rotation
        by returning physically-correct world coordinates, so no additional rotation
        correction is needed here.

        Args:
            world_x: X coordinate in world space (already rotation-aware)
            world_y: Y coordinate in world space (already rotation-aware)
            zone_idx: Zone index (unused in global mode, kept for signature compatibility)
            local_idx: LED index within zone (unused in global mode, kept for signature compatibility)

        Returns:
            Position value along the wave direction axis
        """
        min_x = self.bbox['min_x']
        max_x = self.bbox['max_x']
        min_y = self.bbox['min_y']
        max_y = self.bbox['max_y']

        # Calculate position along direction axis - no rotation correction needed
        # because get_led_world_position() already provides physically-correct coordinates

        if self.direction in ("horizontal", "right"):
            # Wave propagates left to right (X increasing)
            return float(world_x - min_x)

        elif self.direction == "left":
            # Wave propagates right to left (X decreasing)
            return float(max_x - world_x)

        elif self.direction in ("vertical", "down"):
            # Wave propagates top to bottom (Y decreasing)
            # Higher Y values (top) get position=0, lower Y values (bottom) get position=max
            return float(max_y - world_y)

        elif self.direction == "top":
            # Wave propagates bottom to top (Y increasing)
            # Lower Y values (bottom) get position=0, higher Y values (top) get position=max
            return float(world_y - min_y)

        elif self.direction in ("tl", "diagonal_tl_br"):
            # Wave propagates from top-left to bottom-right
            # Empirical formula (validated on real hardware)
            x_pos = max_x - world_x
            y_pos = world_y - min_y
            return float(x_pos + y_pos)

        elif self.direction in ("br",):
            # Wave propagates from bottom-right to top-left
            # Empirical formula (validated on real hardware)
            x_pos = world_x - min_x
            y_pos = max_y - world_y
            return float(x_pos + y_pos)

        elif self.direction in ("tr", "diagonal_tr_bl"):
            # Wave propagates from top-right to bottom-left
            # Empirical formula (validated on real hardware)
            x_pos = world_x - min_x
            y_pos = world_y - min_y
            return float(x_pos + y_pos)

        elif self.direction in ("bl",):
            # Wave propagates from bottom-left to top-right
            # Empirical formula (validated on real hardware)
            x_pos = max_x - world_x
            y_pos = max_y - world_y
            return float(x_pos + y_pos)

        else:
            # Default to horizontal
            return float(world_x - min_x)

    def render_frame(self, time_ms: int):
        """Render wave frame using topology-aware 2D coordinates."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        time_seconds = time_ms / 1000.0
        color_map = {}

        # Iterate through all LEDs using topology
        for global_idx in range(self.linear.led_count):
            zone_idx, local_idx = self.linear.get_zone_and_local_index(global_idx)
            world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

            # Calculate wave position based on coordinate system
            if self.use_normalized:
                # Phase 1.1: Use normalized [0,1] coordinates
                norm_x, norm_y = self._normalize_coords(world_x, world_y)
                position = self._calculate_wave_position_normalized(norm_x, norm_y, zone_idx, local_idx)
            else:
                # Legacy: Use world coordinates (existing behavior)
                position = self._calculate_wave_position(world_x, world_y, zone_idx, local_idx)

            # Calculate wave phase
            phase = (position / self.wavelength - time_seconds * self.speed) * 2 * math.pi

            # Sine wave intensity (0 to 1)
            intensity = (math.sin(phase) + 1) / 2

            # Interpolate between background and peak color
            color_map[global_idx] = (
                int(self.color_bg[0] + (active_color[0] - self.color_bg[0]) * intensity),
                int(self.color_bg[1] + (active_color[1] - self.color_bg[1]) * intensity),
                int(self.color_bg[2] + (active_color[2] - self.color_bg[2]) * intensity),
            )

        self._apply_color_map(color_map, int(time_ms))

    def _normalize_coords(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Normalize world coordinates to [0,1] space using device bbox.

        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space

        Returns:
            (norm_x, norm_y) in [0,1] range
        """
        min_x = self.bbox['min_x']
        max_x = self.bbox['max_x']
        min_y = self.bbox['min_y']
        max_y = self.bbox['max_y']

        width = max_x - min_x
        height = max_y - min_y

        norm_x = (world_x - min_x) / width if width > 0 else 0.5
        norm_y = (world_y - min_y) / height if height > 0 else 0.5

        # Clamp to [0,1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)

    def _calculate_wave_position_normalized(self, norm_x: float, norm_y: float, zone_idx: int, local_idx: int) -> float:
        """
        Calculate wave position using normalized [0,1] coordinates in GLOBAL wave mode.

        For global wave behavior: the wave propagates continuously across the entire
        normalized [0,1] space. Segment rotation is already handled by coordinate
        normalization, so no additional rotation correction is needed.

        Args:
            norm_x: Normalized X coordinate [0,1] (already rotation-aware)
            norm_y: Normalized Y coordinate [0,1] (already rotation-aware)
            zone_idx: Zone index (unused in global mode, kept for signature compatibility)
            local_idx: LED index within zone (unused in global mode, kept for signature compatibility)

        Returns:
            Position in [0,1] space along wave direction
        """
        # Calculate position along direction axis - no rotation correction needed
        # because normalization already accounts for segment rotation

        if self.direction in ("horizontal", "right"):
            # Wave propagates left to right
            return norm_x

        elif self.direction == "left":
            # Wave propagates right to left
            return 1.0 - norm_x

        elif self.direction in ("vertical", "down"):
            # Wave propagates top to bottom (Y decreasing)
            # Higher norm_y (top) get position=0, lower norm_y (bottom) get position=1
            return 1.0 - norm_y

        elif self.direction == "top":
            # Wave propagates bottom to top (Y increasing)
            # Lower norm_y (bottom) get position=0, higher norm_y (top) get position=1
            return norm_y

        elif self.direction == "tl":  # Top-left to bottom-right
            # Empirical formula (validated on real hardware)
            return (1.0 - norm_x) + norm_y

        elif self.direction == "br":  # Bottom-right to top-left
            # Empirical formula (validated on real hardware)
            return norm_x + (1.0 - norm_y)

        elif self.direction == "tr":  # Top-right to bottom-left
            # Empirical formula (validated on real hardware)
            return norm_x + norm_y

        elif self.direction == "bl":  # Bottom-left to top-right
            # Empirical formula (validated on real hardware)
            return (1.0 - norm_x) + (1.0 - norm_y)

        else:
            # Default to horizontal
            return norm_x


class BumpEffect1D(Animated1DEffect):
    """
    Gaussian light-hill that bounces between edges (ping-pong).

    A single smooth dome of light travels from one edge to the other and
    reverses direction each time it reaches the opposite edge.
    Uses topology-aware world coordinates with Y/X inversions.

    color = peak color (visible at hill center)
    color_bg = background color (visible at edges)
    """

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 128, 0),
                 color_bg: Tuple[int, int, int] = (0, 0, 0),
                 direction: str = "right",
                 num_loops: int = 1,
                 use_normalized: bool = True):
        """
        Initialize Bump effect with topology awareness.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: Peak RGB color (hill center)
            color_bg: Background RGB color (edges)
            direction: Direction of travel - "horizontal"/"right", "left",
                      "vertical"/"down", "top", "tl", "tr", "bl", "br"
            num_loops: Number of complete back-and-forth cycles
            use_normalized: If True, use normalized [0,1] coordinates (Phase 1.1)
        """
        super().__init__(linear, duration_ms)
        self.base_color = color
        self.color_bg = color_bg
        self.direction = direction
        self.num_loops = max(1, num_loops)
        self.use_normalized = use_normalized

        # Get global bounding box
        self.bbox = self.linear.get_global_bbox()

        # Calculate max position along direction axis
        if self.use_normalized:
            # Normalized coordinates: max_pos is in [0,1] or [0,2] space
            if self.direction in ("horizontal", "right", "left"):
                self.max_pos = 1.0
            elif self.direction in ("vertical", "down", "top"):
                self.max_pos = 1.0
            else:  # Diagonal
                self.max_pos = 2.0  # Sum of two [0,1] ranges
        else:
            # World coordinates: max_pos is in world space
            cols_span = self.bbox['max_x'] - self.bbox['min_x']
            rows_span = self.bbox['max_y'] - self.bbox['min_y']

            if self.direction in ("horizontal", "right", "left"):
                self.max_pos = float(cols_span)
            elif self.direction in ("vertical", "down", "top"):
                self.max_pos = float(rows_span)
            else:  # Diagonal
                self.max_pos = float(cols_span + rows_span)

        # Sigma: max_pos/4 so edges are at ~2σ (intensity ≈ 0.13)
        self.sigma = max(0.25 if self.use_normalized else 1.0, self.max_pos / 4.0)

    def _normalize_coords(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """
        Normalize world coordinates to [0,1] space using device bbox.

        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space

        Returns:
            (norm_x, norm_y) in [0,1] range
        """
        min_x = self.bbox['min_x']
        max_x = self.bbox['max_x']
        min_y = self.bbox['min_y']
        max_y = self.bbox['max_y']

        width = max_x - min_x
        height = max_y - min_y

        norm_x = (world_x - min_x) / width if width > 0 else 0.5
        norm_y = (world_y - min_y) / height if height > 0 else 0.5

        # Clamp to [0,1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)

    def _calculate_position(self, world_x: float, world_y: float) -> float:
        """
        Calculate position along direction axis using world coordinates (GLOBAL wave mode).

        For global wave behavior: the wave propagates continuously across the entire
        bbox. get_led_world_position() already handles segment rotation, so no
        additional rotation correction is needed.

        Args:
            world_x: X coordinate in world space (already rotation-aware)
            world_y: Y coordinate in world space (already rotation-aware)

        Returns:
            Position value along the direction axis
        """
        min_x = self.bbox['min_x']
        max_x = self.bbox['max_x']
        min_y = self.bbox['min_y']
        max_y = self.bbox['max_y']

        # Same logic as WaveEffect1D for global wave consistency
        if self.direction in ("horizontal", "right"):
            return float(world_x - min_x)
        elif self.direction == "left":
            return float(max_x - world_x)
        elif self.direction in ("vertical", "down"):
            # Empirical formula (validated on hardware)
            return float(max_y - world_y)
        elif self.direction == "top":
            return float(world_y - min_y)
        elif self.direction in ("tl", "diagonal_tl_br"):
            # Empirical formula (validated on hardware)
            return float((max_x - world_x) + (world_y - min_y))
        elif self.direction in ("br",):
            # Empirical formula (validated on hardware)
            return float((world_x - min_x) + (max_y - world_y))
        elif self.direction in ("tr", "diagonal_tr_bl"):
            # Empirical formula (validated on hardware)
            return float((world_x - min_x) + (world_y - min_y))
        elif self.direction in ("bl",):
            # Empirical formula (validated on hardware)
            return float((max_x - world_x) + (max_y - world_y))
        else:
            return float(world_x - min_x)

    def _calculate_position_normalized(self, norm_x: float, norm_y: float) -> float:
        """
        Calculate position using normalized [0,1] coordinates (GLOBAL wave mode).

        For global wave behavior: the wave propagates continuously across the entire
        normalized [0,1] space. Segment rotation is already handled by coordinate
        normalization.

        Args:
            norm_x: Normalized X coordinate [0,1] (already rotation-aware)
            norm_y: Normalized Y coordinate [0,1] (already rotation-aware)

        Returns:
            Position in [0,1] space along direction axis
        """
        # Same logic as WaveEffect1D for consistency
        if self.direction in ("horizontal", "right"):
            return norm_x
        elif self.direction == "left":
            return 1.0 - norm_x
        elif self.direction in ("vertical", "down"):
            return 1.0 - norm_y
        elif self.direction == "top":
            return norm_y
        elif self.direction == "tl":
            # Empirical formula (validated on hardware)
            return (1.0 - norm_x) + norm_y
        elif self.direction == "br":
            # Empirical formula (validated on hardware)
            return norm_x + (1.0 - norm_y)
        elif self.direction == "tr":
            # Empirical formula (validated on hardware)
            return norm_x + norm_y
        elif self.direction == "bl":
            # Empirical formula (validated on hardware)
            return (1.0 - norm_x) + (1.0 - norm_y)
        else:
            return norm_x

    def render_frame(self, time_ms: int):
        """Render Gaussian hill at its current ping-pong position."""
        active_color = self.current_color if self.current_color else self.base_color

        # Triangular wave: 1 loop = one full back-and-forth
        traversal_ms = self.duration_ms / (2 * self.num_loops)
        t_raw = (time_ms % (2 * traversal_ms)) / traversal_ms  # [0, 2)
        t_bounce = t_raw if t_raw <= 1.0 else 2.0 - t_raw      # Triangle wave [0→1→0→...]

        # Hill center position (oscillates between 0 and max_pos)
        center = t_bounce * self.max_pos

        r0, g0, b0 = self.color_bg
        r1, g1, b1 = active_color

        color_map = {}
        for global_idx in range(self.linear.led_count):
            zone_idx, local_idx = self.linear.get_zone_and_local_index(global_idx)
            world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

            # Calculate position along direction axis based on coordinate system
            if self.use_normalized:
                # Phase 1.1: Use normalized [0,1] coordinates
                norm_x, norm_y = self._normalize_coords(world_x, world_y)
                pos = self._calculate_position_normalized(norm_x, norm_y)
            else:
                # Legacy: Use world coordinates (existing behavior)
                pos = self._calculate_position(world_x, world_y)

            # Gaussian intensity (distance from center)
            dist = pos - center
            intensity = math.exp(-(dist * dist) / (2 * self.sigma * self.sigma))

            # Interpolate between background and peak color
            color_map[global_idx] = (
                int(r0 + (r1 - r0) * intensity),
                int(g0 + (g1 - g0) * intensity),
                int(b0 + (b1 - b0) * intensity),
            )

        self._apply_color_map(color_map, int(time_ms))


class OceanWavesEffect1D(Animated1DEffect):
    """
    Ocean waves effect for LINEAR devices with 2D topology.

    Simulates ocean surface using 3 superimposed sinusoids. For multi-segment
    LED strips with 2D layout, uses world_x for wave calculation and world_y
    for depth/crest comparison.

    colors[0] = deep water (dark blue)
    colors[1] = shallow water (lighter blue)
    colors[2] = wave crest/foam (light blue/white)
    """

    # Wave parameters: (frequency, amplitude, speed_multiplier, initial_phase)
    _WAVE_PARAMS = [
        (1.2, 0.35, 1.0, 0.0),
        (2.1, 0.15, 1.3, 1.0),
        (3.7, 0.08, 0.7, 2.5),
    ]
    _TOTAL_AMP = 0.58  # Sum of amplitudes
    _TAU = 2.0 * math.pi

    _DEFAULT_COLORS = [
        (0, 15, 60),      # Deep water
        (0, 70, 150),     # Shallow water
        (150, 210, 255),  # Crest/foam base
    ]

    def __init__(self, linear: Linear1D, duration_ms: int = 4000,
                 colors=None, speed: float = 1.0, use_normalized: bool = True):
        """
        Initialize Ocean Waves effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            colors: [deep, shallow, crest] RGB colors
            speed: Wave propagation speed multiplier
            use_normalized: If True, use normalized [0,1] coordinates (Phase 1.1)
        """
        super().__init__(linear, duration_ms)

        # Color palette
        palette = colors if colors and len(colors) >= 3 else self._DEFAULT_COLORS
        self.c_deep = tuple(palette[0])
        self.c_mid = tuple(palette[1])
        self.c_crest = tuple(palette[2])

        # Foam: blend crest toward white for bright peak
        self.c_foam = _lerp_color_util(self.c_crest, (240, 250, 255), 0.5)
        self.c_sky = (0, 0, 0)

        self.speed = speed
        self.use_normalized = use_normalized

        # Get bbox for normalization
        self.bbox = self.linear.get_global_bbox()
        self.cols_span = self.bbox['max_x'] - self.bbox['min_x']
        self.rows_span = self.bbox['max_y'] - self.bbox['min_y']

        # Per-position phase noise (based on LED count for simplicity)
        random.seed(42)  # Deterministic for consistency
        self._phase_offsets = [random.uniform(0, self._TAU) for _ in range(linear.led_count)]

    def _normalize_coords(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Normalize world coordinates to [0,1] space."""
        norm_x = (world_x - self.bbox['min_x']) / self.cols_span if self.cols_span > 0 else 0.5
        norm_y = (world_y - self.bbox['min_y']) / self.rows_span if self.rows_span > 0 else 0.5
        return (max(0.0, min(1.0, norm_x)), max(0.0, min(1.0, norm_y)))

    def render_frame(self, time_ms: int):
        """Render ocean waves using superimposed sinusoids."""
        time_seconds = (time_ms / 1000.0) * self.speed

        color_map = {}
        for global_idx in range(self.linear.led_count):
            zone_idx, local_idx = self.linear.get_zone_and_local_index(global_idx)
            world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

            # Get normalized coordinates based on coordinate system
            if self.use_normalized:
                # Phase 1.1: Use normalized [0,1] coordinates
                xn, yn = self._normalize_coords(world_x, world_y)
            else:
                # Legacy: Calculate manually (existing behavior)
                xn = (world_x - self.bbox['min_x']) / self.cols_span if self.cols_span > 0 else 0.5
                yn = (world_y - self.bbox['min_y']) / self.rows_span if self.rows_span > 0 else 0.5

            # Get per-position phase offset
            phase_offset = self._phase_offsets[global_idx]

            # Sum of 3 superimposed sinusoids
            wave_h = sum(
                amp * math.sin(freq * xn * self._TAU + time_seconds * spd * math.pi + ph + phase_offset)
                for freq, amp, spd, ph in self._WAVE_PARAMS
            )

            # Normalize wave height to [0, 1]
            # 0 = crest at bottom, 1 = crest at top
            crest_yn = (wave_h / self._TOTAL_AMP + 1.0) / 2.0

            # Determine color based on Y position relative to crest (in normalized space)
            tolerance = 0.05 if self.use_normalized else 0.5  # Smaller tolerance for [0,1] space
            if yn > crest_yn + tolerance:
                # Above crest: sky
                color = self.c_sky
            elif abs(yn - crest_yn) <= tolerance:
                # At crest: foam
                color = self.c_foam
            else:
                # Below crest: water gradient
                depth_tolerance = 0.15 if self.use_normalized else 1.5
                if yn >= crest_yn - depth_tolerance:
                    # Just below crest: mix mid and crest
                    color = _lerp_color_util(self.c_mid, self.c_crest, 0.5)
                else:
                    # Deeper water: gradient based on distance from crest
                    depth = (crest_yn - yn) / crest_yn if crest_yn > 0 else 0.0
                    depth = max(0.0, min(1.0, depth))
                    color = _lerp_color_util(self.c_mid, self.c_deep, depth)

            color_map[global_idx] = color

        self._apply_color_map(color_map, int(time_ms))


class FireEffect1D(Animated1DEffect):
    """
    Fire effect via cellular automata for LINEAR devices with 2D topology.

    Creates a virtual 2D heat grid based on bbox, runs cellular automaton,
    then maps heat values to LEDs via nearest-neighbor. Works with sparse
    topologies (non-contiguous segments).

    colors[0] = ember base (dark red)
    colors[1] = flame peak (bright yellow)
    """

    _N = 8  # Palette size: heat indices 0..7

    _DEFAULT_COLORS = [
        (200, 30, 0),    # Ember base (dark red)
        (255, 220, 0),   # Flame peak (bright yellow)
    ]

    @staticmethod
    def _make_palette(ember: Tuple[int, int, int], peak: Tuple[int, int, int]) -> list:
        """
        8-step palette: black → ember → peak → warm white.
        """
        black = (0, 0, 0)
        warm_tip = (255, 255, 80)
        return [
            black,                                                    # 0 -- off
            _lerp_color_util(black, ember, 0.20),            # 1 -- ember glow
            _lerp_color_util(black, ember, 0.60),            # 2 -- dark red
            ember,                                                    # 3 -- ember
            _lerp_color_util(ember, peak, 1 / 3),            # 4 -- dark orange
            _lerp_color_util(ember, peak, 2 / 3),            # 5 -- orange
            peak,                                                     # 6 -- yellow peak
            _lerp_color_util(peak, warm_tip, 0.50),          # 7 -- warm white tip
        ]

    def __init__(self, linear: Linear1D, duration_ms: int = 4000,
                 colors=None, intensity: float = 0.85, direction: str = 'down',
                 use_normalized: bool = True):
        """
        Initialize Fire effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            colors: [ember, peak] RGB colors
            intensity: Fire intensity [0, 1] - probability of max heat in source
            direction: Fire propagation direction ('down' = bottom→top, 'top' = top→bottom)
            use_normalized: Reserved for Phase 1.1 (cellular automaton uses internal grid)
        """
        super().__init__(linear, duration_ms)

        # Color palette
        palette_colors = colors if colors and len(colors) >= 2 else self._DEFAULT_COLORS
        ember = tuple(palette_colors[0])
        peak = tuple(palette_colors[1])
        self._palette = self._make_palette(ember, peak)

        self.intensity = max(0.0, min(1.0, intensity))
        self.direction = direction  # 'down' (default) or 'top'
        self.use_normalized = use_normalized  # Reserved for future use

        # Get bbox and create virtual 2D grid
        self.bbox = self.linear.get_global_bbox()
        self.cols = int(self.bbox['max_x'] - self.bbox['min_x'] + 1)
        self.rows = int(self.bbox['max_y'] - self.bbox['min_y'] + 1)

        # Heat grid: rows+2 (2 hidden source rows for heat source)
        self._heat = [[0] * self.cols for _ in range(self.rows + 2)]

        # Build LED mapping: for each grid cell, find nearest LED (if any)
        self._grid_to_led = {}  # (grid_row, grid_col) -> global_led_index
        for global_idx in range(linear.led_count):
            zone_idx, local_idx = linear.get_zone_and_local_index(global_idx)
            world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

            # Map world coords to grid coords
            grid_col = int(world_x - self.bbox['min_x'])

            # Grid row mapping depends on direction
            if self.direction == 'top':
                # Direction 'top': top→bottom combustion
                # High world_y (top) → low grid_row (near source)
                # Low world_y (bottom) → high grid_row (far from source)
                grid_row = self.rows - 1 - int(world_y - self.bbox['min_y'])
            else:
                # Direction 'down': bottom→top combustion (default)
                # High world_y (top) → high grid_row (far from source)
                # Low world_y (bottom) → low grid_row (near source)
                grid_row = int(world_y - self.bbox['min_y'])

            # Clamp to grid bounds
            grid_col = max(0, min(self.cols - 1, grid_col))
            grid_row = max(0, min(self.rows - 1, grid_row))

            # Store mapping (last LED wins if multiple LEDs map to same cell)
            self._grid_to_led[(grid_row, grid_col)] = global_idx

    def render_frame(self, time_ms: int):
        """Render one frame of cellular automaton fire."""
        rows = self.rows
        cols = self.cols
        max_heat = self._N - 1  # 7
        palette = self._palette
        heat = self._heat

        if self.direction == 'top':
            # Direction 'top': top→bottom combustion
            # Heat source at TOP (hidden rows -1 and -2)
            # 1. Feed hidden source rows at top
            for c in range(cols):
                if random.random() < self.intensity:
                    heat[0][c] = max_heat
                else:
                    heat[0][c] = max(0, max_heat - random.randint(0, 2))

            # 2. Downward diffusion: Gauss-Seidel from top to bottom
            for r in range(0, rows + 1):
                row_src = heat[r]
                row_dst = heat[r + 1] if r + 1 < rows + 2 else heat[r]
                for c in range(cols):
                    lc = c - 1 if c > 0 else 0
                    rc = c + 1 if c < cols - 1 else cols - 1
                    avg = (row_src[c] * 2 + row_src[lc] + row_src[rc]) / 4
                    if r + 1 < rows + 2:
                        row_dst[c] = max(0, int(avg) - random.randint(0, 1))
        else:
            # Direction 'down': bottom→top combustion (default)
            # Heat source at BOTTOM (hidden rows below visible grid)
            # 1. Feed hidden source rows at bottom
            for c in range(cols):
                if random.random() < self.intensity:
                    heat[rows + 1][c] = max_heat
                else:
                    heat[rows + 1][c] = max(0, max_heat - random.randint(0, 2))

            # 2. Upward diffusion: Gauss-Seidel from bottom to top
            for r in range(rows + 1, 0, -1):
                row_src = heat[r]
                row_dst = heat[r - 1]
                for c in range(cols):
                    lc = c - 1 if c > 0 else 0
                    rc = c + 1 if c < cols - 1 else cols - 1
                    avg = (row_src[c] * 2 + row_src[lc] + row_src[rc]) / 4
                    row_dst[c] = max(0, int(avg) - random.randint(0, 1))

        # 3. Render: map heat grid to LEDs
        color_map = {}
        for (grid_row, grid_col), led_idx in self._grid_to_led.items():
            heat_val = heat[grid_row][grid_col]
            color_map[led_idx] = palette[min(max_heat, heat_val)]

        self._apply_color_map(color_map, int(time_ms))


class GlitchEffect1D(Animated1DEffect):
    """
    Glitch effect with random LED flashes and persistence.

    Features:
    - Random LED glitches with configurable density
    - Some glitches become persistent (don't return to base)
    - Variable glitch duration
    - No topology dependency (global random effect)
    """

    _DEFAULT_GLITCH_COLORS = [
        (255, 0, 0),    # Red
        (0, 255, 0),    # Green
        (0, 255, 255),  # Cyan
    ]

    def __init__(self, linear: Linear1D, duration_ms: int = 5000,
                 base_color: Tuple[int, int, int] = (0, 0, 255),
                 glitch_colors: list = None,
                 glitch_percentage: float = 0.15,
                 glitch_duration_ms: int = 150,
                 persistence_percentage: float = 0.3,
                 use_normalized: bool = True):
        """
        Initialize glitch effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total effect duration
            base_color: Background color
            glitch_colors: List of glitch colors
            glitch_percentage: % of LEDs glitching simultaneously [0, 1]
            glitch_duration_ms: Duration of single glitch flash
            persistence_percentage: % of glitched LEDs that become persistent [0, 1]
            use_normalized: Reserved for Phase 1.1 (random effect doesn't use coordinates)
        """
        super().__init__(linear, duration_ms)
        self.base_color = base_color
        self.glitch_colors = glitch_colors or self._DEFAULT_GLITCH_COLORS
        self.glitch_percentage = max(0.0, min(1.0, glitch_percentage))
        self.glitch_duration_ms = glitch_duration_ms
        self.persistence_percentage = max(0.0, min(1.0, persistence_percentage))
        self.use_normalized = use_normalized  # Reserved for future use

        # Persistent LED tracking
        self.persistent_leds = set()
        self.last_glitch_time = 0

    def render_frame(self, time_ms: int):
        """Render glitch frame with random LED selection and persistence."""
        # Check if it's time for a new glitch cycle
        if time_ms - self.last_glitch_time >= self.glitch_duration_ms:
            self.last_glitch_time = time_ms

            # Select LEDs to glitch (exclude persistent ones)
            all_leds = set(range(self.linear.led_count))
            available_leds = list(all_leds - self.persistent_leds)

            num_glitch_leds = max(1, int(len(all_leds) * self.glitch_percentage))
            num_to_glitch = min(num_glitch_leds, len(available_leds))

            if num_to_glitch > 0:
                glitching_leds = random.sample(available_leds, num_to_glitch)

                # Determine which become persistent
                num_persist = max(0, int(len(glitching_leds) * self.persistence_percentage))
                if num_persist > 0:
                    new_persistent = set(random.sample(glitching_leds, num_persist))
                    self.persistent_leds.update(new_persistent)

        # Build color map
        color_map = {}

        # Base color for non-persistent LEDs
        for led_idx in range(self.linear.led_count):
            if led_idx not in self.persistent_leds:
                color_map[led_idx] = self.base_color

        # Glitch colors for persistent LEDs (stay glitched)
        for led_idx in self.persistent_leds:
            glitch_color = random.choice(self.glitch_colors)
            color_map[led_idx] = glitch_color

        self._apply_color_map(color_map, int(time_ms))


# =============================================================================
# MatrixRainEffect1D - Falling columns with topology awareness
# =============================================================================

class MatrixRainEffect1D(Animated1DEffect):
    """
    Matrix rain: columns fall from top (max_y) to bottom (min_y).

    Uses device topology to create virtual columns based on world_x (or norm_x).
    Each column has a bright head and fading trail falling downward.

    colors[0] = off/background (default black)
    colors[1] = trail color (default dark green)
    colors[2] = head color (default bright green)
    density multiplies the number of simultaneous active columns.

    use_normalized: if True, uses normalized [0,1] coordinates instead of world coords
    """

    def __init__(
        self,
        linear: Linear1D,
        duration_ms: int = 8000,
        color_off: Tuple[int, int, int] = (0, 0, 0),
        color_trail: Tuple[int, int, int] = (0, 64, 0),
        color_head: Tuple[int, int, int] = (0, 255, 70),
        density: float = 1.0,
        use_normalized: bool = True
    ):
        super().__init__(linear, duration_ms)
        self.color_off = color_off
        self.color_trail = color_trail
        self.color_head = color_head
        self.density = max(0.1, min(3.0, density))
        self.use_normalized = use_normalized

        # Load topology and bbox
        self.bbox = linear.get_global_bbox()
        if self.bbox is None:
            # Fallback: treat as simple 1D strip (no topology)
            self.virtual_columns = None
            return

        # Build virtual columns: group LEDs by world_x (or norm_x if normalized)
        # Each column is a list of (y_coord, global_idx) sorted by y_coord DESC (top to bottom)
        self._build_virtual_columns()

    def _normalize_coords(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Normalize world coordinates to [0,1] space using device bbox."""
        min_x = self.bbox['min_x']
        max_x = self.bbox['max_x']
        min_y = self.bbox['min_y']
        max_y = self.bbox['max_y']

        width = max_x - min_x
        height = max_y - min_y

        norm_x = (world_x - min_x) / width if width > 0 else 0.5
        norm_y = (world_y - min_y) / height if height > 0 else 0.5

        # Clamp to [0,1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)

    def _build_virtual_columns(self):
        """Group LEDs by x coordinate (world_x or norm_x) to create virtual columns."""
        from collections import defaultdict

        columns_dict = defaultdict(list)

        for global_idx in range(self.linear.led_count):
            zone_idx, local_idx = self.linear.get_zone_and_local_index(global_idx)
            world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

            if self.use_normalized:
                norm_x, norm_y = self._normalize_coords(world_x, world_y)
                # Round norm_x to nearest 0.1 for grouping (10 columns in normalized space)
                x_key = round(norm_x * 10) / 10
                y_coord = norm_y
            else:
                # Round world_x to nearest integer for grouping
                x_key = round(world_x)
                y_coord = world_y

            columns_dict[x_key].append((y_coord, global_idx))

        # Sort each column by y_coord DESC (top first)
        self.virtual_columns = {}
        for x_key, leds in columns_dict.items():
            self.virtual_columns[x_key] = sorted(leds, key=lambda item: item[0], reverse=True)

        self.column_keys = list(self.virtual_columns.keys())

    def _run_animation(self, on_complete=None):
        if self.virtual_columns is None:
            # Fallback: no topology, use simple pulse
            self.running = False
            if on_complete:
                on_complete()
            return

        self.running = True
        start_time = time.time()
        frame_dt = 1 / 15  # 15 fps for matrix rain feel

        # Y span: 1.0 for normalized, world units for world coords
        if self.use_normalized:
            y_span = 1.0
            min_y = 0.0
            max_y = 1.0
        else:
            y_span = self.bbox['max_y'] - self.bbox['min_y']
            min_y = self.bbox['min_y']
            max_y = self.bbox['max_y']

        max_active = max(1, int(len(self.column_keys) * self.density))

        # Each drop: [x_key, head_y, trail_length, speed_y_per_sec]
        drops = []

        def _new_drop():
            x_key = random.choice(self.column_keys)
            trail_len = random.uniform(y_span * 0.2, y_span * 0.5)
            speed = random.uniform(y_span * 0.5, y_span * 1.5)
            start_y = max_y + trail_len  # Start above visible area
            return [x_key, start_y, trail_len, speed]

        # Initialize drops with staggered starts
        for _ in range(max_active):
            drop = _new_drop()
            drop[1] = random.uniform(max_y, max_y + y_span)
            drops.append(drop)

        last_time = time.time()

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms >= self.duration_ms:
                break

            now = time.time()
            dt = now - last_time
            last_time = now

            # Initialize all LEDs to off
            color_map = {idx: self.color_off for idx in range(self.linear.led_count)}

            # Update and render each drop
            for drop in drops:
                x_key, head_y, trail_len, speed = drop
                drop[1] -= speed * dt  # Move head downward (Y decreases)

                head_y = drop[1]
                column_leds = self.virtual_columns[x_key]

                # Render trail: find LEDs in column within [head_y - trail_len, head_y]
                for y_coord, global_idx in column_leds:
                    if head_y - trail_len <= y_coord <= head_y:
                        # Distance from head (0 = at head, trail_len = at tail)
                        dist_from_head = head_y - y_coord

                        if dist_from_head < 0.5:
                            # At head: bright green
                            color_map[global_idx] = self.color_head
                        else:
                            # In trail: fade from trail_color to off
                            fade_factor = 1.0 - (dist_from_head / trail_len)
                            color_map[global_idx] = (
                                int(self.color_trail[0] * fade_factor),
                                int(self.color_trail[1] * fade_factor),
                                int(self.color_trail[2] * fade_factor),
                            )

                # Reset drop when head completely off screen (below min_y)
                if head_y < min_y:
                    new_drop = _new_drop()
                    drop[0] = new_drop[0]
                    drop[1] = new_drop[1]
                    drop[2] = new_drop[2]
                    drop[3] = new_drop[3]

            self._apply_color_map(color_map, int(elapsed_ms))

            elapsed = time.time() - now
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# AuroraEffect1D - Vertical light bands with shimmer and additive blending
# =============================================================================

class AuroraEffect1D(Animated1DEffect):
    """
    Aurora borealis with topology awareness.

    Multiple color bands ondeggia vertically (world_y varies with world_x).
    Each band has center_y calculated from 2 superimposed sinusoids.
    LEDs near band center contribute with smoothstep fade.
    Additive RGB blending (multiple bands overlay).

    colors = list of band colors (3-8 recommended)
    height = base band position [0, 1] (0=bottom, 1=top)
    tail_length = fade distance multiplier
    wave_frequency = primary sinusoid frequency
    ripple = secondary sinusoid amplitude [0, 1]
    speed = animation speed multiplier
    use_normalized = if True, uses normalized [0,1] coordinates instead of world coords
    """

    _TAU = 2 * math.pi

    @staticmethod
    def _ease(t: float) -> float:
        """Smoothstep ease-in-out: t^2 * (3 - 2t)."""
        return t * t * (3.0 - 2.0 * t)

    def __init__(
        self,
        linear: Linear1D,
        duration_ms: int = 10000,
        colors: List[Tuple[int, int, int]] = None,
        height: float = 0.5,
        tail_length: float = 1.5,
        wave_frequency: float = 0.8,
        ripple: float = 0.3,
        speed: float = 0.5,
        wave_amplitude: float = 0.45,
        use_normalized: bool = True
    ):
        super().__init__(linear, duration_ms)

        if colors is None or len(colors) < 2:
            colors = [(0, 255, 80), (0, 180, 200), (80, 0, 255)]

        self.tail_length = tail_length
        self.ripple = ripple
        self.wave_amplitude = wave_amplitude
        self.use_normalized = use_normalized

        # Load topology and bbox
        self.bbox = linear.get_global_bbox()
        if self.bbox is None:
            # Fallback: no topology
            self.bands = None
            return

        # Build per-band parameters (matching 2D implementation)
        n = len(colors)
        self.bands = [
            {
                'color': tuple(colors[i]),
                'freq1': wave_frequency + i * 0.3,          # primary wave
                'freq2': 1.5 + i * 0.5,                     # secondary ripple
                'speed1': speed * (0.7 + i * 0.15),         # primary speed
                'speed2': speed * (1.1 - i * 0.1),          # secondary speed
                'phase_x': i * math.pi * 0.7,               # spatial phase
                'height_base': height + (i % 2) * 0.1,      # alternating height
            }
            for i in range(n)
        ]

        # Precompute LED positions (world or normalized)
        self._led_positions = []
        for global_idx in range(linear.led_count):
            zone_idx, local_idx = linear.get_zone_and_local_index(global_idx)
            world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

            if self.use_normalized:
                norm_x, norm_y = self._normalize_coords_static(world_x, world_y, self.bbox)
                self._led_positions.append((norm_x, norm_y))
            else:
                self._led_positions.append((world_x, world_y))

        if self.use_normalized:
            # Normalized space: always 1.0
            self.x_span = 1.0
            self.y_span = 1.0
            self.is_horizontal = False  # Not relevant in normalized space
            self.effective_span = 1.0
        else:
            # World coordinates
            self.x_span = self.bbox['max_x'] - self.bbox['min_x']
            self.y_span = self.bbox['max_y'] - self.bbox['min_y']
            self.is_horizontal = self.y_span < 1.0
            self.effective_span = self.x_span if self.is_horizontal else self.y_span

    @staticmethod
    def _normalize_coords_static(world_x: float, world_y: float, bbox: dict) -> Tuple[float, float]:
        """Normalize world coordinates to [0,1] space using device bbox."""
        min_x = bbox['min_x']
        max_x = bbox['max_x']
        min_y = bbox['min_y']
        max_y = bbox['max_y']

        width = max_x - min_x
        height = max_y - min_y

        norm_x = (world_x - min_x) / width if width > 0 else 0.5
        norm_y = (world_y - min_y) / height if height > 0 else 0.5

        # Clamp to [0,1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)

    def _run_animation(self, on_complete=None):
        if self.bands is None:
            # Fallback: no topology
            self.running = False
            if on_complete:
                on_complete()
            return

        self.running = True
        start_time = time.time()
        frame_dt = 1 / 30  # 30 fps

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms >= self.duration_ms:
                break

            frame_start = time.time()
            t = time.time() - start_time

            # Initialize RGB accumulator for additive blending
            acc = [[0.0, 0.0, 0.0] for _ in range(self.linear.led_count)]

            # Process each band
            for band in self.bands:
                color = band['color']
                freq1 = band['freq1']
                freq2 = band['freq2']
                speed1 = band['speed1']
                speed2 = band['speed2']
                phase_x = band['phase_x']
                h_base = band['height_base']
                c0, c1, c2 = color

                # For each LED, calculate band center at its x coordinate
                for led_idx, (coord_x, coord_y) in enumerate(self._led_positions):
                    # xn is already normalized [0,1] for both modes
                    if self.use_normalized:
                        xn = coord_x  # Already normalized
                    else:
                        xn = (coord_x - self.bbox['min_x']) / max(self.x_span, 1)

                    # Two superimposed sinusoids (matching 2D formula)
                    wave1 = math.sin(xn * freq1 * self._TAU + t * speed1 + phase_x)
                    wave2 = math.sin(xn * freq2 * self._TAU - t * speed2) * self.ripple * 0.5
                    band_center_normalized = h_base + (wave1 + wave2) * self.wave_amplitude
                    band_center_normalized = max(0.05, min(0.95, band_center_normalized))

                    if self.use_normalized:
                        # Normalized space: direct comparison
                        band_center = band_center_normalized
                        led_coord = coord_y  # Already normalized
                        fade_len = max(0.05, self.tail_length * 0.15)  # Fixed in [0,1] space
                    else:
                        # World coordinates: convert to world space
                        if self.is_horizontal:
                            band_center = self.bbox['min_x'] + band_center_normalized * self.x_span
                            led_coord = coord_x
                        else:
                            band_center = self.bbox['min_y'] + band_center_normalized * self.y_span
                            led_coord = coord_y
                        fade_len = max(1.0, self.effective_span * self.tail_length * 0.6)

                    # Distance from LED to band center
                    dist = abs(led_coord - band_center)

                    if dist <= fade_len:
                        # Within fade distance: calculate brightness
                        raw = 1.0 - (dist / fade_len)
                        brightness = self._ease(raw)

                        # Accumulate RGB contribution
                        acc[led_idx][0] += c0 * brightness
                        acc[led_idx][1] += c1 * brightness
                        acc[led_idx][2] += c2 * brightness

            # Build color_map from accumulator (clamp to 255)
            color_map = {}
            for led_idx in range(self.linear.led_count):
                rgb = acc[led_idx]
                color_map[led_idx] = (
                    min(255, int(rgb[0])),
                    min(255, int(rgb[1])),
                    min(255, int(rgb[2])),
                )

            self._apply_color_map(color_map, int(elapsed_ms))

            elapsed = time.time() - frame_start
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# ParallaxStarsEffect1D - Lateral parallax scroll with depth layers
# =============================================================================

class ParallaxStarsEffect1D(Animated1DEffect):
    """
    Parallax stars: 3 depth layers scrolling at different speeds.

    Deeper layers = slower speed, dimmer stars, more numerous.
    Stars scroll in the specified direction and wrap around.

    colors[0] = background (default black)
    colors[1] = far stars (default white)
    colors[2] = mid stars (default white)
    colors[3] = near stars (default white)
    speed = base scroll rate (near layer speed, default 9.0 units/s for world, 0.6/s for normalized)
    density = multiplier for star count per layer
    direction = scroll direction ('left', 'right')
    use_normalized = if True, uses normalized [0,1] coordinates instead of world coords
    """

    def __init__(
        self,
        linear: Linear1D,
        duration_ms: int = 15000,
        colors: list = None,
        speed: float = 9.0,
        density: float = 1.0,
        direction: str = 'left',
        use_normalized: bool = True
    ):
        super().__init__(linear, duration_ms)
        self.speed = speed
        self.density = max(0.1, min(3.0, density))
        self.direction = direction if direction in ('left', 'right') else 'left'
        self.use_normalized = use_normalized

        if colors is None or len(colors) == 0:
            colors = [(0, 0, 0)]  # background
        self.bg_color = colors[0]
        star_colors = colors[1:] if len(colors) > 1 else [(255, 255, 255)]

        # Load topology and bbox
        self.bbox = linear.get_global_bbox()
        if self.bbox is None:
            # Fallback: no topology
            self.layers = None
            return

        if self.use_normalized:
            self.x_span = 1.0
            self.y_span = 1.0
        else:
            self.x_span = self.bbox['max_x'] - self.bbox['min_x']
            self.y_span = self.bbox['max_y'] - self.bbox['min_y']

        # Layer definitions: (speed_mult, brightness_factor, base_count)
        # For normalized: base_count scaled by 10 (assume ~10 virtual columns)
        if self.use_normalized:
            layer_defs = [
                (0.17, 0.27, max(8, int(10 / 3))),    # far: slow, dim, many
                (0.44, 0.59, max(5, int(10 / 4))),    # mid: medium
                (1.00, 0.94, max(3, int(10 / 6))),    # near: fast, bright
            ]
        else:
            layer_defs = [
                (0.17, 0.27, max(8, int(self.x_span / 3))),    # far: slow, dim, many
                (0.44, 0.59, max(5, int(self.x_span / 4))),    # mid: medium
                (1.00, 0.94, max(3, int(self.x_span / 6))),    # near: fast, bright
            ]

        self.layers = []
        for i, (spd_m, bright_m, base_count) in enumerate(layer_defs):
            sc = star_colors[i % len(star_colors)]
            bright_color = tuple(int(ch * bright_m) for ch in sc)
            count = max(1, int(base_count * self.density))

            # Stars: [x_float, y_float] in normalized [0,1] or world coords
            if self.use_normalized:
                stars = [
                    [random.uniform(0.0, 1.0), random.uniform(0.0, 1.0)]
                    for _ in range(count)
                ]
            else:
                stars = [
                    [
                        random.uniform(self.bbox['min_x'], self.bbox['max_x']),
                        random.uniform(self.bbox['min_y'], self.bbox['max_y'])
                    ]
                    for _ in range(count)
                ]

            self.layers.append({
                'stars': stars,
                'speed_mult': spd_m,
                'color': bright_color,
            })

        # Precompute LED positions (normalized or world)
        self._led_positions = []
        for global_idx in range(linear.led_count):
            zone_idx, local_idx = linear.get_zone_and_local_index(global_idx)
            world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

            if self.use_normalized:
                norm_x, norm_y = self._normalize_coords_static(world_x, world_y, self.bbox)
                self._led_positions.append((norm_x, norm_y))
            else:
                self._led_positions.append((world_x, world_y))

    @staticmethod
    def _normalize_coords_static(world_x: float, world_y: float, bbox: dict) -> Tuple[float, float]:
        """Normalize world coordinates to [0,1] space using device bbox."""
        min_x = bbox['min_x']
        max_x = bbox['max_x']
        min_y = bbox['min_y']
        max_y = bbox['max_y']

        width = max_x - min_x
        height = max_y - min_y

        norm_x = (world_x - min_x) / width if width > 0 else 0.5
        norm_y = (world_y - min_y) / height if height > 0 else 0.5

        # Clamp to [0,1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)

    def _run_animation(self, on_complete=None):
        if self.layers is None:
            # Fallback: no topology
            self.running = False
            if on_complete:
                on_complete()
            return

        self.running = True
        start_time = time.time()
        frame_dt = 1 / 30  # 30 fps
        last_time = time.time()

        # Distance threshold for LED-star matching
        if self.use_normalized:
            match_threshold = 0.08  # Fixed in [0,1] space
        else:
            match_threshold = 1.5  # World units (empirical)

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms >= self.duration_ms:
                break

            now = time.time()
            dt = now - last_time
            last_time = now

            # Initialize all LEDs to background
            color_map = {idx: self.bg_color for idx in range(self.linear.led_count)}

            # Update and render each layer
            for layer in self.layers:
                layer_speed = self.speed * layer['speed_mult']
                star_color = layer['color']

                for star in layer['stars']:
                    # Scroll based on direction (left/right only)
                    if self.use_normalized:
                        # Normalized space [0,1]
                        if self.direction == 'right':
                            star[0] += layer_speed * dt
                            if star[0] > 1.0:
                                star[0] = 0.0 - random.uniform(0, 0.2)
                                star[1] = random.uniform(0.0, 1.0)
                        else:  # left
                            star[0] -= layer_speed * dt
                            if star[0] < 0.0:
                                star[0] = 1.0 + random.uniform(0, 0.2)
                                star[1] = random.uniform(0.0, 1.0)
                    else:
                        # World coordinates
                        if self.direction == 'right':
                            star[0] += layer_speed * dt
                            if star[0] > self.bbox['max_x']:
                                star[0] = self.bbox['min_x'] - random.uniform(0, self.x_span * 0.2)
                                star[1] = random.uniform(self.bbox['min_y'], self.bbox['max_y'])
                        else:  # left
                            star[0] -= layer_speed * dt
                            if star[0] < self.bbox['min_x']:
                                star[0] = self.bbox['max_x'] + random.uniform(0, self.x_span * 0.2)
                                star[1] = random.uniform(self.bbox['min_y'], self.bbox['max_y'])

                    # Find nearest LED(s) to star position
                    star_x, star_y = star[0], star[1]

                    for led_idx, (led_x, led_y) in enumerate(self._led_positions):
                        # Euclidean distance
                        dist = math.sqrt((led_x - star_x) ** 2 + (led_y - star_y) ** 2)

                        if dist <= match_threshold:
                            # LED is close enough to star: color it
                            color_map[led_idx] = star_color

            self._apply_color_map(color_map, int(elapsed_ms))

            elapsed = time.time() - now
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# LightningEffect1D - Discrete lightning events with flash and bolt
# =============================================================================

class LightningEffect1D(Animated1DEffect):
    """
    Lightning: periodic lightning events with bolt, flash, and fade.

    Each event consists of:
    1. Bolt: random jagged path from top to bottom with glow (40ms)
    2. Full-screen flash (60ms)
    3. Fade back to sky with smoothstep (6 steps × 40ms)
    Between strikes: occasional atmospheric flicker (5% chance)

    colors[0] = sky/background (default dark blue)
    colors[1] = bolt/flash color (default white)
    bolt_interval_ms = average time between strikes (randomized ±50%)
    """

    @staticmethod
    def _ease(t: float) -> float:
        """Smoothstep ease-in-out: t^2*(3-2t)."""
        return t * t * (3.0 - 2.0 * t)

    def __init__(
        self,
        linear: Linear1D,
        duration_ms: int = 10000,
        color_sky: Tuple[int, int, int] = (5, 5, 20),
        color_bolt: Tuple[int, int, int] = (255, 255, 255),
        bolt_interval_ms: int = 2000,
        use_normalized: bool = True
    ):
        super().__init__(linear, duration_ms)
        self.color_sky = color_sky
        self.color_bolt = color_bolt
        self.bolt_interval_ms = bolt_interval_ms
        self.use_normalized = use_normalized

        # Load topology and bbox
        self.bbox = linear.get_global_bbox()
        if self.bbox is None:
            # Fallback: no topology
            self.has_topology = False
            return

        self.has_topology = True

        if self.use_normalized:
            self.y_span = 1.0
        else:
            self.y_span = self.bbox['max_y'] - self.bbox['min_y']
            # Lightning requires vertical extent >= 2 for world coords
            if self.y_span < 2:
                print(f"[Lightning1D] WARNING: Device {linear.device.name} has insufficient Y-span "
                      f"({self.y_span}) for lightning effect. Requires multi-zone vertical layout. "
                      f"Using simple flash fallback.")
                self.has_topology = False
                return

        # Precompute LED positions (normalized or world)
        self._led_positions = []
        for global_idx in range(linear.led_count):
            zone_idx, local_idx = linear.get_zone_and_local_index(global_idx)
            world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

            if self.use_normalized:
                norm_x, norm_y = self._normalize_coords_static(world_x, world_y, self.bbox)
                self._led_positions.append((norm_x, norm_y))
            else:
                self._led_positions.append((world_x, world_y))

    @staticmethod
    def _normalize_coords_static(world_x: float, world_y: float, bbox: dict) -> Tuple[float, float]:
        """Normalize world coordinates to [0,1] space using device bbox."""
        min_x = bbox['min_x']
        max_x = bbox['max_x']
        min_y = bbox['min_y']
        max_y = bbox['max_y']

        width = max_x - min_x
        height = max_y - min_y

        norm_x = (world_x - min_x) / width if width > 0 else 0.5
        norm_y = (world_y - min_y) / height if height > 0 else 0.5

        # Clamp to [0,1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)

    def _generate_bolt(self):
        """Generate random jagged bolt path from top to bottom."""
        if not self.has_topology:
            return []

        bolt_points = []

        if self.use_normalized:
            # Normalized space [0,1]
            x = random.uniform(0.1, 0.9)  # Padding from edges
            y = 1.0  # Start at top
            step = 0.1  # ~10 steps in [0,1]
            jitter = 0.1

            while y >= 0.0:
                bolt_points.append((x, y))
                y -= step
                x += random.uniform(-jitter, jitter)
                x = max(0.0, min(1.0, x))  # clamp to [0,1]
        else:
            # World coordinates
            x = random.uniform(self.bbox['min_x'] + 1, self.bbox['max_x'] - 1)
            y = self.bbox['max_y']
            step = self.y_span / 10  # ~10 steps
            jitter = 2.0

            while y >= self.bbox['min_y']:
                bolt_points.append((x, y))
                y -= step
                x += random.uniform(-jitter, jitter)
                x = max(self.bbox['min_x'], min(self.bbox['max_x'], x))  # clamp

        return bolt_points

    def _run_animation(self, on_complete=None):
        if not self.has_topology:
            # Fallback: simple pulse
            self.running = False
            if on_complete:
                on_complete()
            return

        self.running = True
        start_time = time.time()
        frame_dt = 1 / 30
        next_strike = 0.0

        # Glow distance threshold
        glow_threshold = 2.0
        glow_color = (
            int((self.color_sky[0] + self.color_bolt[0]) / 2),
            int((self.color_sky[1] + self.color_bolt[1]) / 2),
            int((self.color_sky[2] + self.color_bolt[2]) / 2),
        )
        flash_color = (
            int(self.color_bolt[0] * 0.6 + 255 * 0.4),
            int(self.color_bolt[1] * 0.6 + 255 * 0.4),
            int(self.color_bolt[2] * 0.6 + 255 * 0.4),
        )

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms >= self.duration_ms:
                break

            # Strike duration: ~340ms (40ms bolt + 60ms flash + 240ms fade)
            strike_duration_ms = 340
            time_remaining = self.duration_ms - elapsed_ms

            if elapsed_ms >= next_strike and time_remaining >= strike_duration_ms:
                # === Phase 1: Bolt path with glow (40ms) ===
                bolt_path = self._generate_bolt()
                color_map = {idx: self.color_sky for idx in range(self.linear.led_count)}

                for led_idx, (led_x, led_y) in enumerate(self._led_positions):
                    # Find closest point on bolt path
                    min_dist = float('inf')
                    for bolt_x, bolt_y in bolt_path:
                        dist = math.sqrt((led_x - bolt_x) ** 2 + (led_y - bolt_y) ** 2)
                        min_dist = min(min_dist, dist)

                    if min_dist < 2.5:
                        # On bolt path: bright (threshold increased from 0.5 to 2.5 for multi-zone strips)
                        color_map[led_idx] = self.color_bolt
                    elif min_dist < glow_threshold:
                        # Near bolt: glow
                        color_map[led_idx] = glow_color

                self._apply_color_map(color_map, int(elapsed_ms))
                time.sleep(0.04)

                # === Phase 2: Full-screen flash (60ms) ===
                color_map = {idx: flash_color for idx in range(self.linear.led_count)}
                self._apply_color_map(color_map, int((time.time() - start_time) * 1000))
                time.sleep(0.06)

                # === Phase 3: Fade back to sky (6 steps × 40ms) ===
                fade_steps = 6
                for step in range(fade_steps):
                    t = self._ease(1.0 - step / (fade_steps - 1))
                    fade_color = (
                        int(self.color_sky[0] + (flash_color[0] - self.color_sky[0]) * t),
                        int(self.color_sky[1] + (flash_color[1] - self.color_sky[1]) * t),
                        int(self.color_sky[2] + (flash_color[2] - self.color_sky[2]) * t),
                    )
                    color_map = {idx: fade_color for idx in range(self.linear.led_count)}
                    self._apply_color_map(color_map, int((time.time() - start_time) * 1000))
                    time.sleep(0.04)

                # Schedule next strike (±50% randomization)
                interval_s = self.bolt_interval_ms / 1000.0
                next_strike = elapsed_ms + interval_s * 1000 * random.uniform(0.5, 1.8)

            else:
                # Between strikes: dark sky with occasional flicker (5%)
                if random.random() < 0.05:
                    flicker_intensity = random.uniform(0, 0.3)
                    flicker_color = (
                        int(self.color_sky[0] + (60 - self.color_sky[0]) * flicker_intensity),
                        int(self.color_sky[1] + (60 - self.color_sky[1]) * flicker_intensity),
                        int(self.color_sky[2] + (80 - self.color_sky[2]) * flicker_intensity),
                    )
                    color_map = {idx: flicker_color for idx in range(self.linear.led_count)}
                else:
                    color_map = {idx: self.color_sky for idx in range(self.linear.led_count)}

                self._apply_color_map(color_map, int(elapsed_ms))
                time.sleep(frame_dt)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# DirectionalFlashEffect1D - Half-flash for impact feedback
# =============================================================================

class DirectionalFlashEffect1D(Animated1DEffect):
    """
    Directional half-flash for impact feedback (e.g., UnderAttack_Right).

    The hit-side half of the device lights up instantly at the start of
    each loop, then both zones fade to black over the remainder of the loop.

    color_bg = background zone color (default dark red)
    color_hit = impact zone color (default bright red)
    direction = "right" | "left" | "top" | "down" | "tl" | "tr" | "bl" | "br"
    num_loops = how many flash repetitions (default 1)
    """

    _HOLD = 0.10  # Fraction of each loop held at full brightness

    def __init__(
        self,
        linear: Linear1D,
        duration_ms: int = 600,
        color_bg: Tuple[int, int, int] = (20, 0, 0),
        color_hit: Tuple[int, int, int] = (255, 20, 0),
        direction: str = "right",
        num_loops: int = 1,
        use_normalized: bool = True
    ):
        super().__init__(linear, duration_ms)
        self.color_bg = color_bg
        self.color_hit = color_hit
        self.direction = direction
        self.num_loops = max(1, num_loops)
        self.use_normalized = use_normalized

        # Load topology and bbox
        self.bbox = linear.get_global_bbox()
        if self.bbox is None:
            # Fallback: no topology
            self.has_topology = False
            return

        self.has_topology = True

        # Precompute LED positions (normalized or world) and hit quarter classification
        self._led_in_hit_half = []
        for global_idx in range(linear.led_count):
            zone_idx, local_idx = linear.get_zone_and_local_index(global_idx)
            world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

            if self.use_normalized:
                norm_x, norm_y = self._normalize_coords_static(world_x, world_y, self.bbox)
                is_hit = self._in_hit_half(norm_x, norm_y)
            else:
                is_hit = self._in_hit_half(world_x, world_y)

            self._led_in_hit_half.append(is_hit)

    @staticmethod
    def _normalize_coords_static(world_x: float, world_y: float, bbox: dict) -> Tuple[float, float]:
        """Normalize world coordinates to [0,1] space using device bbox."""
        min_x = bbox['min_x']
        max_x = bbox['max_x']
        min_y = bbox['min_y']
        max_y = bbox['max_y']

        width = max_x - min_x
        height = max_y - min_y

        norm_x = (world_x - min_x) / width if width > 0 else 0.5
        norm_y = (world_y - min_y) / height if height > 0 else 0.5

        # Clamp to [0,1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)

    def _in_hit_half(self, x: float, y: float) -> bool:
        """Return True if (x, y) falls in the hit half (50% from center)."""
        if not self.has_topology:
            return False

        if self.use_normalized:
            half_x, half_y = 0.5, 0.5
        else:
            half_x = (self.bbox['min_x'] + self.bbox['max_x']) / 2
            half_y = (self.bbox['min_y'] + self.bbox['max_y']) / 2

        d = self.direction

        # Cardinals: half split at center
        if   d == 'right': return x >= half_x
        elif d == 'left':  return x <  half_x
        elif d == 'down':  return y <  half_y
        elif d == 'top':   return y >= half_y

        # Diagonals: corner quadrant
        elif d == 'tl':    return y >= half_y and x <  half_x
        elif d == 'tr':    return y >= half_y and x >= half_x
        elif d == 'bl':    return y <  half_y and x <  half_x
        elif d == 'br':    return y <  half_y and x >= half_x

        return False

    def _run_animation(self, on_complete=None):
        if not self.has_topology:
            # Fallback: no topology
            self.running = False
            if on_complete:
                on_complete()
            return

        self.running = True
        start_time = time.time()
        frame_dt = 1 / 30  # 30 fps
        loop_ms = self.duration_ms / self.num_loops

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms >= self.duration_ms:
                break

            frame_start = time.time()

            # Calculate loop phase (0.0 → 1.0 within each loop)
            t_loop = (elapsed_ms % loop_ms) / loop_ms

            # Hold at full brightness for _HOLD fraction, then linear fade to black
            if t_loop < self._HOLD:
                fade = 1.0
            else:
                fade = max(0.0, 1.0 - (t_loop - self._HOLD) / (1.0 - self._HOLD))

            # Build color map based on hit quarter classification
            color_map = {}
            for led_idx in range(self.linear.led_count):
                if self._led_in_hit_half[led_idx]:
                    r, g, b = self.color_hit
                else:
                    r, g, b = self.color_bg
                color_map[led_idx] = (int(r * fade), int(g * fade), int(b * fade))

            self._apply_color_map(color_map, int(elapsed_ms))

            elapsed = time.time() - frame_start
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# PlasmaEffect1D - 2D sinusoid HSV palette cycling with topology awareness
# =============================================================================

class PlasmaEffect1D(Animated1DEffect):
    """
    Plasma: weighted sum of 4 sinusoid components (horizontal, vertical, circular, diagonal).

    Uses centered coordinates [-1, 1] for large-scale organic patterns.
    Wave frequencies WITHOUT TAU multiplier (matching 2D reference).

    colors >= 2: palette interpolation mode (user-defined gradient)
    colors 0-1: full HSV spectrum mode
    wave_weights = [horizontal, vertical, circular, diagonal] (default [1,1,1,1])
    speed = animation speed multiplier (default 1.0)
    """

    @staticmethod
    def _palette_lerp(colors: list, t: float) -> Tuple[int, int, int]:
        """Interpolate smoothly through N colors at position t in [0, 1]."""
        n = len(colors) - 1
        if n <= 0:
            return tuple(colors[0]) if colors else (0, 0, 0)
        idx = max(0.0, min(1.0, t)) * n
        i = min(int(idx), n - 1)
        # Linear interpolation between colors[i] and colors[i+1]
        c1, c2 = colors[i], colors[i + 1]
        frac = idx - i
        return (
            int(c1[0] + (c2[0] - c1[0]) * frac),
            int(c1[1] + (c2[1] - c1[1]) * frac),
            int(c1[2] + (c2[2] - c1[2]) * frac),
        )

    def __init__(
        self,
        linear: Linear1D,
        duration_ms: int = 12000,
        colors: list = None,
        speed: float = 1.0,
        wave_weights: list = None,
        use_normalized: bool = True
    ):
        super().__init__(linear, duration_ms)
        self.speed = speed
        self.use_normalized = use_normalized

        # Normalize wave weights
        raw_w = wave_weights if wave_weights else [1.0, 1.0, 1.0, 1.0]
        norm = sum(raw_w) or 1.0
        self.wH = raw_w[0] / norm if len(raw_w) > 0 else 0.25
        self.wV = raw_w[1] / norm if len(raw_w) > 1 else 0.25
        self.wC = raw_w[2] / norm if len(raw_w) > 2 else 0.25
        self.wD = raw_w[3] / norm if len(raw_w) > 3 else 0.25

        # Palette mode when ≥2 colors; HSV full spectrum otherwise
        self._colors = [tuple(c) for c in colors] if colors and len(colors) >= 2 else None

        # Load topology and bbox
        self.bbox = linear.get_global_bbox()
        if self.bbox is None:
            # Fallback: no topology
            self.has_topology = False
            return

        self.has_topology = True

        # Calculate center and half-spans (normalized or world)
        if self.use_normalized:
            cx, cy = 0.5, 0.5
            hw, hh = 0.5, 0.5
        else:
            # Try custom center from topology (world coordinates only)
            custom_center = self.linear.get_effect_center()
            if custom_center:
                cx, cy = custom_center
            else:
                # Fallback: geometric center
                cx = (self.bbox['min_x'] + self.bbox['max_x']) / 2.0
                cy = (self.bbox['min_y'] + self.bbox['max_y']) / 2.0

            hw = (self.bbox['max_x'] - self.bbox['min_x']) / 2.0 or 1.0
            hh = (self.bbox['max_y'] - self.bbox['min_y']) / 2.0 or 1.0

        # Precompute per-LED constants using CENTERED [-1, 1] coordinates
        self._plasma_coords = []
        for global_idx in range(linear.led_count):
            zone_idx, local_idx = linear.get_zone_and_local_index(global_idx)
            world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

            if self.use_normalized:
                # Convert world to [0,1] first, then to centered [-1,1]
                norm_x = (world_x - self.bbox['min_x']) / (self.bbox['max_x'] - self.bbox['min_x']) if (self.bbox['max_x'] - self.bbox['min_x']) > 0 else 0.5
                norm_y = (world_y - self.bbox['min_y']) / (self.bbox['max_y'] - self.bbox['min_y']) if (self.bbox['max_y'] - self.bbox['min_y']) > 0 else 0.5
                nx = (norm_x - cx) / hw    # [-1, 1] horizontal
                ny = (norm_y - cy) / hh    # [-1, 1] vertical
            else:
                nx = (world_x - cx) / hw    # [-1, 1] horizontal
                ny = (world_y - cy) / hh    # [-1, 1] vertical

            dist = math.sqrt(nx * nx + ny * ny)  # [0, sqrt(2)]
            diag = nx + ny              # [-2, 2]

            self._plasma_coords.append((global_idx, nx, ny, dist, diag))

    def _run_animation(self, on_complete=None):
        if not self.has_topology:
            # Fallback: no topology
            self.running = False
            if on_complete:
                on_complete()
            return

        self.running = True
        start_time = time.time()
        frame_dt = 1 / 30  # 30 fps

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms >= self.duration_ms:
                break

            frame_start = time.time()

            t = elapsed_ms / 1000.0 * self.speed
            colors = self._colors
            color_map = {}

            for led_idx, nx, ny, dist, diag in self._plasma_coords:
                # Reference formula — no TAU, frequencies 3/4/5/2.5, speeds 1.1/0.9/1.3/0.7
                v = (
                    self.wH * math.sin(nx * 3.0 + t * 1.1) +
                    self.wV * math.sin(ny * 4.0 + t * 0.9) +
                    self.wC * math.sin(dist * 5.0 - t * 1.3) +
                    self.wD * math.sin(diag * 2.5 + t * 0.7)
                )  # v in [-1.0, 1.0] because weights sum=1
                v_norm = (v + 1.0) * 0.5  # [0, 1]

                if colors is not None:
                    color_map[led_idx] = self._palette_lerp(colors, v_norm)
                else:
                    color_map[led_idx] = _hsv_to_rgb_util(v_norm * 360.0, 1.0, 1.0)

            self._apply_color_map(color_map, int(elapsed_ms))

            elapsed = time.time() - frame_start
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)

        self.running = False
        if on_complete:
            on_complete()


class ColorCycleEffect1D(Animated1DEffect):
    """Multi-color scrolling gradient along the LED strip.

    N colors are distributed as a smooth interpolated gradient along the strip.
    The gradient scrolls in the given direction over time.
    speed=1.0 means exactly one full color cycle over the effect duration.
    """

    def __init__(self, linear: Linear1D, duration_ms: int = 3000,
                 colors=None,
                 direction: str = 'forward', speed: float = 1.0,
                 use_normalized: bool = True):
        super().__init__(linear, duration_ms)
        self.colors = colors if colors else [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        self.direction = direction
        self.speed = speed
        self.use_normalized = use_normalized

    def _normalize_coords(self, world_x: float, world_y: float) -> tuple:
        """
        Normalize world coordinates to [0,1] space using global bbox.

        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space

        Returns:
            (norm_x, norm_y) in [0,1] range
        """
        bbox = self.linear.get_global_bbox()
        min_x = bbox['min_x']
        max_x = bbox['max_x']
        min_y = bbox['min_y']
        max_y = bbox['max_y']

        width = max_x - min_x
        height = max_y - min_y

        norm_x = (world_x - min_x) / width if width > 0 else 0.5
        norm_y = (world_y - min_y) / height if height > 0 else 0.5

        # Clamp to [0,1]
        norm_x = max(0.0, min(1.0, norm_x))
        norm_y = max(0.0, min(1.0, norm_y))

        return (norm_x, norm_y)

    def _calculate_position_normalized(self, norm_x: float, norm_y: float) -> float:
        """
        Calculate position along direction axis using normalized [0,1] coordinates.

        Args:
            norm_x: Normalized X coordinate [0,1]
            norm_y: Normalized Y coordinate [0,1]

        Returns:
            Position in [0,1] space along direction axis
        """
        # Same logic as WaveEffect1D for consistency
        if self.direction in ("horizontal", "right"):
            return norm_x
        elif self.direction == "left":
            return 1.0 - norm_x
        elif self.direction in ("vertical", "down"):
            return 1.0 - norm_y
        elif self.direction == "top":
            return norm_y
        elif self.direction == "tl":
            return (1.0 - norm_x) + norm_y
        elif self.direction == "br":
            return norm_x + (1.0 - norm_y)
        elif self.direction == "tr":
            return norm_x + norm_y
        elif self.direction == "bl":
            return (1.0 - norm_x) + (1.0 - norm_y)
        else:
            return norm_x

    @staticmethod
    def _cycle_color(colors, t: float):
        """Return interpolated color at normalised cycle position t (0.0-1.0)."""
        n = len(colors)
        if n == 1:
            return colors[0]
        t = t % 1.0
        pos = t * n
        idx1 = int(pos) % n
        idx2 = (idx1 + 1) % n
        frac = pos - int(pos)
        c1, c2 = colors[idx1], colors[idx2]
        return (
            max(0, min(255, int(c1[0] + (c2[0] - c1[0]) * frac))),
            max(0, min(255, int(c1[1] + (c2[1] - c1[1]) * frac))),
            max(0, min(255, int(c1[2] + (c2[2] - c1[2]) * frac))),
        )

    def render_frame(self, time_ms: int):
        """Render one frame of the scrolling color cycle with dual-coordinate support.

        Supports both world coordinates (device-specific) and normalized coordinates
        (device-independent [0,1] space) for 8-way directional color propagation.
        """
        scroll = (time_ms / self.duration_ms) * self.speed
        color_map = {}

        if self.use_normalized:
            # Phase 1.1: Normalized coordinates path
            for global_idx in range(self.linear.led_count):
                zone_idx, local_idx = self.linear.get_zone_and_local_index(global_idx)
                world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

                # Normalize to [0,1] space
                norm_x, norm_y = self._normalize_coords(world_x, world_y)

                # Calculate position along direction axis in normalized space
                pos_normalized = self._calculate_position_normalized(norm_x, norm_y)

                # Diagonal directions span [0,2] range, normalize to [0,1]
                if self.direction in ('tl', 'br', 'tr', 'bl'):
                    pos_normalized = pos_normalized / 2.0

                # Apply scroll (time-based offset)
                # All directions use inverted scroll in 1D (different from 2D due to position formulas)
                t = (pos_normalized - scroll) % 1.0

                color_map[global_idx] = self._cycle_color(self.colors, t)

        else:
            # Legacy: World coordinates path
            bbox = self.linear.get_global_bbox()
            min_x = bbox['min_x']
            max_x = bbox['max_x']
            min_y = bbox['min_y']
            max_y = bbox['max_y']

            width = max_x - min_x
            height = max_y - min_y

            # Determine max_pos based on direction (for normalization)
            if self.direction in ('horizontal', 'right', 'left'):
                max_pos = width if width > 0 else 1.0
            elif self.direction in ('vertical', 'down', 'top'):
                max_pos = height if height > 0 else 1.0
            elif self.direction in ('tl', 'br', 'tr', 'bl'):
                max_pos = width + height if (width + height) > 0 else 1.0
            else:
                max_pos = width if width > 0 else 1.0

            for global_idx in range(self.linear.led_count):
                zone_idx, local_idx = self.linear.get_zone_and_local_index(global_idx)
                world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

                # Calculate position along direction axis
                if self.direction in ("horizontal", "right"):
                    position = float(world_x - min_x)
                elif self.direction == "left":
                    position = float(max_x - world_x)
                elif self.direction in ("vertical", "down"):
                    position = float(max_y - world_y)
                elif self.direction == "top":
                    position = float(world_y - min_y)
                elif self.direction == "tl":
                    position = float((max_x - world_x) + (world_y - min_y))
                elif self.direction == "br":
                    position = float((world_x - min_x) + (max_y - world_y))
                elif self.direction == "tr":
                    position = float((world_x - min_x) + (world_y - min_y))
                elif self.direction == "bl":
                    position = float((max_x - world_x) + (max_y - world_y))
                else:
                    position = float(world_x - min_x)

                # Normalize position to [0, 1]
                pos_normalized = position / max_pos if max_pos > 0 else 0.0

                # Apply scroll (time-based offset)
                # All directions use inverted scroll in 1D (different from 2D due to position formulas)
                t = (pos_normalized - scroll) % 1.0

                color_map[global_idx] = self._cycle_color(self.colors, t)

        self._apply_color_map(color_map, int(time_ms))


class ScannerEffect1D(Animated1DEffect):
    """Cylon eye / Knight Rider scanner effect."""

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 0, 0),
                 width: float = 3.0, tail_length: int = 5,
                 bounce: bool = True):
        """
        Initialize scanner effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: RGB color
            width: Width of bright center
            tail_length: Length of fade trail
            bounce: If True, bounces back and forth
        """
        super().__init__(linear, duration_ms)
        self.base_color = color
        self.width = width
        self.tail_length = tail_length
        self.bounce = bounce

    def render_frame(self, time_ms: int):
        """Render scanner frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        progress = time_ms / self.duration_ms

        if self.bounce:
            # Bounce back and forth
            cycle_progress = (progress * 2) % 2
            if cycle_progress > 1:
                cycle_progress = 2 - cycle_progress
            position = cycle_progress * self.linear.led_count
        else:
            # One-way scan
            position = (progress * self.linear.led_count) % self.linear.led_count

        color_map = self.linear.generate_scanner(
            position,
            active_color,
            width=self.width,
            tail_length=self.tail_length
        )
        self._apply_color_map(color_map, int(time_ms))


class ChaseEffect1D(Animated1DEffect):
    """Chase effect with multiple moving dots."""

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (0, 255, 128),
                 spacing: int = 3, count: int = 3, speed: float = 1.0):
        """
        Initialize chase effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: RGB color
            spacing: Space between dots
            count: Number of dots
            speed: Chase speed multiplier
        """
        super().__init__(linear, duration_ms)
        self.base_color = color
        self.spacing = spacing
        self.count = count
        self.speed = speed

    def render_frame(self, time_ms: int):
        """Render chase frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        progress = time_ms / self.duration_ms
        position = int(progress * self.linear.led_count * self.speed) % self.linear.led_count

        color_map = self.linear.generate_chase(
            position,
            active_color,
            spacing=self.spacing,
            count=self.count
        )
        self._apply_color_map(color_map, int(time_ms))


class RainbowEffect1D(Animated1DEffect):
    """Animated rainbow gradient."""

    def __init__(self, linear: Linear1D, duration_ms: int = 5000, speed: float = 1.0):
        """
        Initialize rainbow effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            speed: Animation speed
        """
        super().__init__(linear, duration_ms)
        self.speed = speed

    def render_frame(self, time_ms: int):
        """Render rainbow frame."""
        progress = time_ms / self.duration_ms
        offset = (progress * self.speed) % 1.0

        color_map = self.linear.generate_rainbow(offset)
        self._apply_color_map(color_map, int(time_ms))


class FillEffect1D(Animated1DEffect):
    """Progress bar fill effect."""

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (0, 255, 0),
                 direction: str = 'forward', reverse_at_end: bool = False):
        """
        Initialize fill effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: RGB color
            direction: 'forward' or 'reverse'
            reverse_at_end: If True, empties after filling
        """
        super().__init__(linear, duration_ms)
        self.base_color = color
        self.direction = direction
        self.reverse_at_end = reverse_at_end

    def render_frame(self, time_ms: int):
        """Render fill frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        progress = time_ms / self.duration_ms

        if self.reverse_at_end:
            # Fill then empty
            if progress < 0.5:
                fill_amount = progress * 2
            else:
                fill_amount = (1 - progress) * 2
        else:
            fill_amount = progress

        color_map = self.linear.generate_fill(
            fill_amount,
            active_color,
            direction=self.direction
        )
        self._apply_color_map(color_map, int(time_ms))


class SparkleEffect1D(Animated1DEffect):
    """Random sparkle/twinkle effect."""

    def __init__(self, linear: Linear1D, duration_ms: int = 3000,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 density: float = 0.2):
        """
        Initialize sparkle effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: RGB color
            density: Sparkle density (0-1)
        """
        super().__init__(linear, duration_ms)
        self.base_color = color
        self.density = density

    def render_frame(self, time_ms: int):
        """Render sparkle frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        # Randomly select LEDs to sparkle
        num_sparkles = int(self.linear.led_count * self.density)
        active_leds = random.sample(range(self.linear.led_count), num_sparkles)

        color_map = self.linear.generate_sparkle(active_leds, active_color)
        self._apply_color_map(color_map, int(time_ms))


class BreathEffect1D(Animated1DEffect):
    """Two-color breath effect for linear devices.

    Oscillates smoothly between color1 and color2 exactly loop_count times
    within duration_ms. Identical semantics to BreathEffect2D.

    Example: duration=5000ms, loop_count=5 -> 5 oscillations of 1000ms each (total 5000ms).
    """

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 color1: Tuple[int, int, int] = (255, 255, 255),
                 color2: Tuple[int, int, int] = (0, 0, 0),
                 loop_count: int = 1):
        loop_count = max(1, loop_count)
        self.cycle_ms = max(1, duration_ms // loop_count)
        super().__init__(linear, duration_ms)
        self.color1 = tuple(int(v) for v in color1)
        self.color2 = tuple(int(v) for v in color2)
        self.loop_count = loop_count

    def render_frame(self, time_ms: int):
        """Render breath frame."""
        c1 = self.current_color if self.current_color else self.color1
        c2 = self.color2

        cycle_progress = (time_ms % self.cycle_ms) / self.cycle_ms
        alpha = (1.0 - math.cos(cycle_progress * math.pi * 2)) / 2.0

        color = (
            int(c1[0] + (c2[0] - c1[0]) * alpha),
            int(c1[1] + (c2[1] - c1[1]) * alpha),
            int(c1[2] + (c2[2] - c1[2]) * alpha),
        )
        color_map = self.linear.generate_solid(color)
        self._apply_color_map(color_map, int(time_ms))


class PulseEffect1D(Animated1DEffect):
    """Pulsing brightness effect."""

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 128, 0),
                 min_brightness: float = 0.1):
        """
        Initialize pulse effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: RGB color
            min_brightness: Minimum brightness (0-1)
        """
        super().__init__(linear, duration_ms)
        self.base_color = color
        self.min_brightness = min_brightness

    def render_frame(self, time_ms: int):
        """Render pulse frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        progress = time_ms / self.duration_ms

        # Sine wave for smooth pulsing
        intensity = (math.sin(progress * 2 * math.pi * 2) + 1) / 2  # 0-1
        intensity = self.min_brightness + (1 - self.min_brightness) * intensity

        dimmed_color = (
            int(active_color[0] * intensity),
            int(active_color[1] * intensity),
            int(active_color[2] * intensity)
        )

        color_map = self.linear.generate_solid(dimmed_color)
        self._apply_color_map(color_map, int(time_ms))


class FadeEffect1D(Animated1DEffect):
    """
    Per-LED fade: each LED transitions independently from its actual current
    color to the target color.

    Mirrors FadeEffect2D: start_colors are captured from linear.device.colors
    at construction time — the caller must ensure device.colors reflects the
    real hardware state before constructing.
    """

    def __init__(self, linear: Linear1D, duration_ms: int = 1000,
                 end_color: Tuple[int, int, int] = (255, 255, 255)):
        super().__init__(linear, duration_ms)
        # Capture per-LED start colors from actual device state
        try:
            self.start_colors = [
                (c.red, c.green, c.blue) for c in linear.device.colors
            ]
        except Exception:
            self.start_colors = [(0, 0, 0)]
        self.base_color = end_color

    def render_frame(self, time_ms: int):
        """Render fade frame with per-LED color interpolation."""
        target = self.current_color if self.current_color else self.base_color
        progress = min(time_ms / self.duration_ms, 1.0)
        n = min(len(self.start_colors), self.linear.led_count)

        color_map = {
            i: (
                int(sc[0] + (target[0] - sc[0]) * progress),
                int(sc[1] + (target[1] - sc[1]) * progress),
                int(sc[2] + (target[2] - sc[2]) * progress),
            )
            for i, sc in enumerate(self.start_colors[:n])
        }
        self._apply_color_map(color_map, int(time_ms))


class CenterOutEffect1D(Animated1DEffect):
    """Effect expanding from center to edges."""

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (0, 128, 255)):
        """
        Initialize center-out effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: RGB color
        """
        super().__init__(linear, duration_ms)
        self.base_color = color

    def render_frame(self, time_ms: int):
        """Render center-out frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        progress = time_ms / self.duration_ms

        color_map = self.linear.generate_center_out(progress, active_color)
        self._apply_color_map(color_map, int(time_ms))


class BloomEffect1D(Animated1DEffect):
    """Bloom effect for LINEAR devices with 2D topology: expanding ring with spatial color cycling.

    Each LED cycles through the color palette based on when the expanding ring
    touches it. Once touched, the LED continues cycling until reaching t=100%
    (final color). The ring can expand beyond device borders using expansion_factor.
    """

    _DEFAULT_COLORS = [
        (255, 255, 255),  # White
        (255, 255,   0),  # Yellow
        (255, 128,   0),  # Orange
        (255,   0,   0),  # Red
        (  0,   0,   0),  # Black
    ]

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 colors=None, expansion_factor: float = 2.0, use_normalized: bool = True,
                 center_x: float = None, center_y: float = None):
        """
        Initialize bloom effect with topology awareness.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            colors: Color palette for spatial cycling
            expansion_factor: Multiplier for max_radius (1.0-5.0) - allows ring expansion beyond borders
            use_normalized: if True, uses normalized [0,1] coordinates
            center_x: Override center X (normalized [0,1] or world depending on use_normalized)
            center_y: Override center Y (normalized [0,1] or world depending on use_normalized)
        """
        super().__init__(linear, duration_ms)
        self._palette = [tuple(int(v) for v in c) for c in colors] if colors else self._DEFAULT_COLORS
        self.expansion_factor = max(1.0, min(5.0, expansion_factor))
        self.use_normalized = use_normalized

        # Calculate center of bounding box (normalized or world)
        bbox = self.linear.get_global_bbox()

        if self.use_normalized:
            # Use provided center or default to geometric center (0.5, 0.5)
            self.center_x = center_x if center_x is not None else 0.5
            self.center_y = center_y if center_y is not None else 0.5
            # Base max radius in normalized space: corner to center
            base_max_radius = (0.5**2 + 0.5**2)**0.5  # ≈ 0.707
        else:
            # Try custom center from topology (world coordinates only)
            custom_center = self.linear.get_effect_center()
            if custom_center:
                self.center_x, self.center_y = custom_center
            else:
                # Fallback: geometric center
                self.center_x = (bbox['min_x'] + bbox['max_x']) / 2.0
                self.center_y = (bbox['min_y'] + bbox['max_y']) / 2.0

            # Calculate base max radius (distance from center to furthest corner)
            corners = [
                (bbox['min_x'], bbox['min_y']),
                (bbox['max_x'], bbox['min_y']),
                (bbox['min_x'], bbox['max_y']),
                (bbox['max_x'], bbox['max_y']),
            ]
            base_max_radius = max(
                ((cx - self.center_x)**2 + (cy - self.center_y)**2)**0.5
                for cx, cy in corners
            )

        # Apply expansion factor to allow ring expansion beyond device
        self.max_radius = base_max_radius * self.expansion_factor

    def _palette_lerp(self, t: float) -> Tuple[int, int, int]:
        """Interpolate color from palette at position t ∈ [0, 1]."""
        palette = self._palette
        n = len(palette)
        if n == 1:
            return palette[0]

        # Map t to palette index
        pos = t * (n - 1)
        idx = min(int(pos), n - 2)
        local_t = pos - idx
        c1, c2 = palette[idx], palette[idx + 1]

        return (
            int(c1[0] + (c2[0] - c1[0]) * local_t),
            int(c1[1] + (c2[1] - c1[1]) * local_t),
            int(c1[2] + (c2[2] - c1[2]) * local_t),
        )

    def render_frame(self, time_ms: int):
        """Render bloom frame using spatial color cycling."""
        progress = time_ms / self.duration_ms
        current_radius = progress * self.max_radius

        # Build color map using 2D distances from topology
        color_map = {}
        bbox = self.linear.get_global_bbox()

        # Final frame guard: ensure all LEDs show final color (t=1.0)
        # Only last 0.5% of duration to allow full animation visibility
        if progress >= 0.995:
            final_color = self._palette_lerp(1.0)
            for global_led_idx in range(self.linear.led_count):
                color_map[global_led_idx] = final_color
        else:
            for global_led_idx in range(self.linear.led_count):
                # Get world position of this LED
                zone_idx, local_idx = self.linear.get_zone_and_local_index(global_led_idx)
                world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

                if self.use_normalized:
                    # Convert to normalized [0,1]
                    norm_x = (world_x - bbox['min_x']) / (bbox['max_x'] - bbox['min_x']) if (bbox['max_x'] - bbox['min_x']) > 0 else 0.5
                    norm_y = (world_y - bbox['min_y']) / (bbox['max_y'] - bbox['min_y']) if (bbox['max_y'] - bbox['min_y']) > 0 else 0.5
                    dx = norm_x - self.center_x
                    dy = norm_y - self.center_y
                else:
                    dx = world_x - self.center_x
                    dy = world_y - self.center_y

                # Calculate 2D Euclidean distance from center
                distance = (dx*dx + dy*dy)**0.5

                # LED already "touched" by expanding ring: cycle through colors
                if distance <= current_radius:
                    # Time since ring touched this LED (in radius units)
                    time_since_touch = current_radius - distance
                    # Normalize to [0,1] based on TOTAL max_radius (with expansion factor)
                    # This ensures color cycling speed is proportional to expansion distance
                    t_touch = min(1.0, time_since_touch / self.max_radius) if self.max_radius > 0 else 0.0
                    color = self._palette_lerp(t_touch)
                    color_map[global_led_idx] = color
                else:
                    # LEDs not yet touched: explicitly set to black
                    color_map[global_led_idx] = (0, 0, 0)

        self._apply_color_map(color_map, int(time_ms))


class ExplosionEffect1D(Animated1DEffect):
    """Explosion effect for LINEAR devices with 2D topology.

    True explosion: an expanding ring with a decaying trail behind it.
    Uses world coordinates to create circular expansion across multi-segment strips.
    """

    _DEFAULT_COLORS = [
        (255, 255, 255),  # ring peak  — pure white flash (QUICK WIN)
        (255,  40,   0),  # burn trail — intense red-orange (QUICK WIN)
    ]

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 colors=None, ring_width: float = 0.1, decay_rate: float = 0.4,
                 expansion_factor: float = 2.0,
                 use_normalized: bool = True,
                 center_x: float = None, center_y: float = None):
        """
        Initialize explosion effect with topology awareness.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            colors: [ring_color, trail_color]; defaults to white + intense red
            ring_width: Thickness of ring as fraction of max_radius (0.02–0.5, default 0.1)
            decay_rate: Trail fade speed; fraction of duration per e-fold
            expansion_factor: Ring expansion multiplier (1.0-5.0, default 2.0) - QUICK WIN
            use_normalized: If True, use normalized [0,1] coordinates (Phase 1.1)
            center_x: Normalized center X [0,1]; defaults to 0.5
            center_y: Normalized center Y [0,1]; defaults to 0.5
        """
        super().__init__(linear, duration_ms)
        self.ring_width = max(0.02, ring_width)
        self.decay_rate = max(0.05, decay_rate)
        self.expansion_factor = max(1.0, min(5.0, expansion_factor))
        self.use_normalized = use_normalized

        palette = [tuple(int(v) for v in c) for c in colors] if colors else self._DEFAULT_COLORS
        self._ring_color = palette[0] if len(palette) > 0 else self._DEFAULT_COLORS[0]
        self._trail_color = palette[1] if len(palette) > 1 else self._DEFAULT_COLORS[1]

        # Store bbox for coordinate conversion
        self.bbox = self.linear.get_global_bbox()

        if use_normalized:
            # Phase 1.1: Normalized [0,1] space — use calibrated center if provided
            self.center_x = center_x if center_x is not None else 0.5
            self.center_y = center_y if center_y is not None else 0.5
            # Base max radius = distance to furthest corner in unit square
            base_max_radius = (0.5**2 + 0.5**2)**0.5  # ≈ 0.707
            # Apply expansion factor
            self.max_radius = base_max_radius * self.expansion_factor
        else:
            # Legacy: Use world coordinates
            # Try custom center from topology (world coordinates only)
            custom_center = self.linear.get_effect_center()
            if custom_center:
                self.center_x, self.center_y = custom_center
            else:
                # Fallback: geometric center of global bounding box
                self.center_x = (self.bbox['min_x'] + self.bbox['max_x']) / 2.0
                self.center_y = (self.bbox['min_y'] + self.bbox['max_y']) / 2.0

            # Calculate base max radius (distance from center to furthest corner)
            corners = [
                (self.bbox['min_x'], self.bbox['min_y']),
                (self.bbox['max_x'], self.bbox['min_y']),
                (self.bbox['min_x'], self.bbox['max_y']),
                (self.bbox['max_x'], self.bbox['max_y']),
            ]
            base_max_radius = max(
                ((cx - self.center_x)**2 + (cy - self.center_y)**2)**0.5
                for cx, cy in corners
            )
            # Apply expansion factor to allow ring expansion beyond device
            self.max_radius = base_max_radius * self.expansion_factor

    def render_frame(self, time_ms: int):
        """Render explosion frame with impact flash and fade-out."""
        import math

        progress = time_ms / self.duration_ms
        ring_radius = progress * self.max_radius        # Leading edge position
        ring_px = self.ring_width * self.max_radius     # Ring thickness
        decay_tc = self.decay_rate * self.duration_ms   # Time constant for trail [ms]

        rc, tc = self._ring_color, self._trail_color
        color_map = {}

        # QUICK WIN: Impact flash in first 5% of animation
        if progress < 0.05:
            # White flash at center during initial impact
            initial_flash_radius = self.max_radius * 0.15
            for global_led_idx in range(self.linear.led_count):
                zone_idx, local_idx = self.linear.get_zone_and_local_index(global_led_idx)
                world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

                if self.use_normalized:
                    min_x, max_x = self.bbox['min_x'], self.bbox['max_x']
                    min_y, max_y = self.bbox['min_y'], self.bbox['max_y']
                    cols_span = max_x - min_x
                    rows_span = max_y - min_y
                    led_x = (world_x - min_x) / cols_span if cols_span > 0 else 0.5
                    led_y = (world_y - min_y) / rows_span if rows_span > 0 else 0.5
                else:
                    led_x = world_x
                    led_y = world_y

                dx = led_x - self.center_x
                dy = led_y - self.center_y
                dist = (dx*dx + dy*dy)**0.5

                if dist <= initial_flash_radius:
                    # White flash with radial falloff
                    flash_intensity = 1.0 - (dist / initial_flash_radius)
                    color_map[global_led_idx] = (
                        int(255 * flash_intensity),
                        int(255 * flash_intensity),
                        int(255 * flash_intensity),
                    )
                else:
                    color_map[global_led_idx] = (0, 0, 0)

            self._apply_color_map(color_map, int(time_ms))
            return

        # QUICK WIN: Double-decay fade-out in last 25% of animation
        fadeout_multiplier = 1.0
        accelerated_decay_factor = 1.0
        if progress >= 0.75:
            fadeout_progress = (progress - 0.75) / 0.25  # 0.0 at 75%, 1.0 at 100%
            fadeout_multiplier = 1.0 - fadeout_progress   # Global fade to black
            accelerated_decay_factor = 1.0 - 0.8 * fadeout_progress  # Speed up trail decay 5x
            effective_decay_tc = decay_tc * accelerated_decay_factor
        else:
            effective_decay_tc = decay_tc

        for global_led_idx in range(self.linear.led_count):
            # Get world position of this LED
            zone_idx, local_idx = self.linear.get_zone_and_local_index(global_led_idx)
            world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

            # Phase 1.1: Convert to appropriate coordinate system
            if self.use_normalized:
                # Normalize to [0,1] space
                min_x, max_x = self.bbox['min_x'], self.bbox['max_x']
                min_y, max_y = self.bbox['min_y'], self.bbox['max_y']
                cols_span = max_x - min_x
                rows_span = max_y - min_y

                led_x = (world_x - min_x) / cols_span if cols_span > 0 else 0.5
                led_y = (world_y - min_y) / rows_span if rows_span > 0 else 0.5
            else:
                # Legacy: Use world coordinates
                led_x = world_x
                led_y = world_y

            # Calculate 2D Euclidean distance from center
            dx = led_x - self.center_x
            dy = led_y - self.center_y
            dist = (dx*dx + dy*dy)**0.5

            dist_behind_front = ring_radius - dist  # Positive = ring has passed this LED

            if dist_behind_front < 0:
                # Ahead of ring → off
                color_map[global_led_idx] = (0, 0, 0)

            elif dist_behind_front <= ring_px:
                # Inside the ring wavefront: peak brightness at leading edge
                t = dist_behind_front / ring_px   # 0 = at leading edge, 1 = inner edge
                intensity = (1.0 - t) ** 1.2
                # Apply global fadeout in last 25%
                intensity *= fadeout_multiplier
                color_map[global_led_idx] = (
                    int(rc[0] * intensity),
                    int(rc[1] * intensity),
                    int(rc[2] * intensity),
                )

            else:
                # Behind the ring: decaying trail
                time_of_pass_ms = (dist / self.max_radius) * self.duration_ms
                time_since_pass = time_ms - time_of_pass_ms
                # Use accelerated decay in last 25%
                intensity = math.exp(-time_since_pass / max(effective_decay_tc, 1.0))
                intensity = max(0.0, intensity)
                # Apply global fadeout in last 25%
                intensity *= fadeout_multiplier
                color_map[global_led_idx] = (
                    int(tc[0] * intensity),
                    int(tc[1] * intensity),
                    int(tc[2] * intensity),
                )

        self._apply_color_map(color_map, int(time_ms))


class PulseFromCenterEffect1D(Animated1DEffect):
    """Pulse wave expanding from center."""

    def __init__(self, linear: Linear1D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 0, 128),
                 width: float = 5.0):
        """
        Initialize pulse from center effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color: RGB color
            width: Pulse width
        """
        super().__init__(linear, duration_ms)
        self.base_color = color
        self.width = width

    def render_frame(self, time_ms: int):
        """Render pulse from center frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        progress = time_ms / self.duration_ms

        color_map = self.linear.generate_pulse_from_center(
            progress,
            active_color,
            width=self.width
        )
        self._apply_color_map(color_map, int(time_ms))


class GradientShiftEffect1D(Animated1DEffect):
    """Two-color spatial gradient for linear devices.

    Renders a static gradient from color1 to color2 across the strip.
    Direction controls which end shows color1 vs color2.
    """

    # DEBUG FLAG - Set to True to enable detailed logging
    DEBUG_GRADIENT = True

    def __init__(self, linear: Linear1D, duration_ms: int = 3000,
                 color1: Tuple[int, int, int] = (255, 0, 0),
                 color2: Tuple[int, int, int] = (0, 0, 255),
                 direction: str = 'right',
                 use_normalized: bool = True):
        """
        Initialize gradient effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total duration
            color1: Start RGB color
            color2: End RGB color
            direction: 'right'/'forward' = color1 left→right; 'left'/'backward' = reversed
            use_normalized: If True, use normalized [0,1] coordinates (Phase 1.1)
        """
        super().__init__(linear, duration_ms)
        self.base_color1 = color1
        self.base_color2 = color2
        self.direction = direction
        self.use_normalized = use_normalized
        self._first_frame_logged = False  # Log only first frame per effect
        # Capture per-LED start colors from actual device state (same pattern as FadeEffect1D)
        try:
            self.start_colors = [(c.red, c.green, c.blue) for c in linear.device.colors]
        except Exception:
            self.start_colors = None

    def _calculate_gradient_factor(self, global_led_index: int) -> float:
        """Calculate gradient interpolation factor.

        Uses device topology to get LED world position, then applies
        gradient logic on the global bounding box (like GradientEffect2D).

        Args:
            global_led_index: LED index in device (0 to led_count-1)

        Returns:
            Interpolation factor (0.0 = color1, 1.0 = color2)
        """
        # Get world position of this LED from topology
        zone_idx, local_idx = self.linear.get_zone_and_local_index(global_led_index)
        world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

        # Phase 1.1: Branch based on coordinate system
        if self.use_normalized:
            # Use normalized [0,1] coordinates
            bbox = self.linear.get_global_bbox()
            min_x, max_x = bbox['min_x'], bbox['max_x']
            min_y, max_y = bbox['min_y'], bbox['max_y']

            # Normalize to [0,1]
            cols_span = max_x - min_x
            rows_span = max_y - min_y
            norm_x = (world_x - min_x) / cols_span if cols_span > 0 else 0.5
            norm_y = (world_y - min_y) / rows_span if rows_span > 0 else 0.5

            return self._calculate_gradient_factor_normalized(norm_x, norm_y, zone_idx)
        else:
            # Legacy: Use world coordinates (existing behavior)
            return self._calculate_gradient_factor_world(world_x, world_y, zone_idx)

    def _calculate_gradient_factor_world(self, world_x: float, world_y: float, zone_idx: int) -> float:
        """Calculate gradient factor using world coordinates with rotation correction.

        Args:
            world_x: X coordinate in world space
            world_y: Y coordinate in world space
            zone_idx: Zone index (to check rotation)

        Returns:
            Interpolation factor (0.0 = color1, 1.0 = color2)
        """
        # Get rotation of this segment
        rotation = self.linear.get_zone_rotation(zone_idx)

        # Get global bounding box
        bbox = self.linear.get_global_bbox()
        min_x, max_x = bbox['min_x'], bbox['max_x']
        min_y, max_y = bbox['min_y'], bbox['max_y']

        # Normalize world position to [0, 1] within bbox
        rows_span = max_y - min_y
        cols_span = max_x - min_x

        # EXACT same logic as gradient_2d.py _calculate_gradient_color()
        # but with rotation correction added
        if self.direction in ("horizontal", "right"):
            # color1 on left → color2 on right
            factor = (world_x - min_x) / cols_span if cols_span > 0 else 0.0
            # Rotation correction: rotation=180 reverses the gradient
            if rotation == 180:
                factor = 1.0 - factor

        elif self.direction == "left":
            # color1 on right → color2 on left
            factor = 1.0 - ((world_x - min_x) / cols_span) if cols_span > 0 else 0.0
            # Rotation correction: rotation=180 reverses back to normal
            if rotation == 180:
                factor = 1.0 - factor

        elif self.direction in ("vertical", "down"):
            # color1 on top → color2 on bottom
            # World Y grows upward, so high Y = top = color1 (factor 0.0)
            factor = 1.0 - ((world_y - min_y) / rows_span) if rows_span > 0 else 0.0
            # Rotation correction: rotation=90 reverses the gradient
            if rotation == 90:
                factor = 1.0 - factor

        elif self.direction == "top":
            # color1 on bottom → color2 on top
            # World Y grows upward, so high Y = top = color2 (factor 1.0)
            factor = (world_y - min_y) / rows_span if rows_span > 0 else 0.0
            # Rotation correction: rotation=270 reverses the gradient
            if rotation == 270:
                factor = 1.0 - factor

        elif self.direction in ("tl", "diagonal_tl_br"):
            # color1 top-left → color2 bottom-right
            # Apply rotation correction to components
            norm_row_base = 1.0 - ((world_y - min_y) / rows_span) if rows_span > 0 else 0.0
            norm_col_base = (world_x - min_x) / cols_span if cols_span > 0 else 0.0

            norm_row = (1.0 - norm_row_base) if rotation == 90 else norm_row_base
            norm_col = (1.0 - norm_col_base) if rotation == 180 else norm_col_base
            factor = (norm_row + norm_col) / 2.0

        elif self.direction in ("br",):
            # color1 bottom-right → color2 top-left
            norm_row_base = (world_y - min_y) / rows_span if rows_span > 0 else 0.0
            norm_col_base = 1.0 - ((world_x - min_x) / cols_span) if cols_span > 0 else 0.0

            norm_row = (1.0 - norm_row_base) if rotation == 270 else norm_row_base
            norm_col = (1.0 - norm_col_base) if rotation == 180 else norm_col_base
            factor = (norm_row + norm_col) / 2.0

        elif self.direction in ("tr", "diagonal_tr_bl"):
            # color1 top-right → color2 bottom-left
            norm_row_base = 1.0 - ((world_y - min_y) / rows_span) if rows_span > 0 else 0.0
            norm_col_base = 1.0 - ((world_x - min_x) / cols_span) if cols_span > 0 else 1.0

            norm_row = (1.0 - norm_row_base) if rotation == 90 else norm_row_base
            norm_col = (1.0 - norm_col_base) if rotation == 180 else norm_col_base
            factor = (norm_row + norm_col) / 2.0

        elif self.direction in ("bl",):
            # color1 bottom-left → color2 top-right
            norm_row_base = (world_y - min_y) / rows_span if rows_span > 0 else 0.0
            norm_col_base = (world_x - min_x) / cols_span if cols_span > 0 else 0.0

            norm_row = (1.0 - norm_row_base) if rotation == 270 else norm_row_base
            norm_col = (1.0 - norm_col_base) if rotation == 180 else norm_col_base
            factor = (norm_row + norm_col) / 2.0

        else:
            # Default to left→right with rotation correction
            factor = (world_x - min_x) / cols_span if cols_span > 0 else 0.0
            if rotation == 180:
                factor = 1.0 - factor

        return factor

    def _calculate_gradient_factor_normalized(self, norm_x: float, norm_y: float, zone_idx: int) -> float:
        """Calculate gradient factor using normalized [0,1] coordinates with rotation correction.

        Args:
            norm_x: Normalized X coordinate [0,1]
            norm_y: Normalized Y coordinate [0,1]
            zone_idx: Zone index (to check rotation)

        Returns:
            Interpolation factor (0.0 = color1, 1.0 = color2)
        """
        # Get rotation of this segment
        rotation = self.linear.get_zone_rotation(zone_idx)

        # Coordinates already normalized to [0,1] with rotation correction
        if self.direction in ("horizontal", "right"):
            # color1 on left (0.0) → color2 on right (1.0)
            factor = norm_x
            # Rotation correction: rotation=180 reverses the gradient
            if rotation == 180:
                factor = 1.0 - factor
            return factor

        elif self.direction == "left":
            # color1 on right (1.0) → color2 on left (0.0)
            factor = 1.0 - norm_x
            # Rotation correction: rotation=180 reverses back to normal
            if rotation == 180:
                factor = 1.0 - factor
            return factor

        elif self.direction in ("vertical", "down"):
            # color1 on top (high Y) → color2 on bottom (low Y)
            # In normalized space, assume Y=1.0 is top
            factor = 1.0 - norm_y
            # Rotation correction: rotation=90 reverses the gradient
            if rotation == 90:
                factor = 1.0 - factor
            return factor

        elif self.direction == "top":
            # color1 on bottom (low Y) → color2 on top (high Y)
            factor = norm_y
            # Rotation correction: rotation=270 reverses the gradient
            if rotation == 270:
                factor = 1.0 - factor
            return factor

        elif self.direction in ("tl", "diagonal_tl_br"):
            # color1 top-left → color2 bottom-right
            # Apply rotation correction to components
            norm_y_comp = (1.0 - norm_y) if rotation != 90 else norm_y
            norm_x_comp = norm_x if rotation != 180 else (1.0 - norm_x)
            return (norm_y_comp + norm_x_comp) / 2.0

        elif self.direction in ("br",):
            # color1 bottom-right → color2 top-left
            # Apply rotation correction to components
            norm_y_comp = norm_y if rotation != 270 else (1.0 - norm_y)
            norm_x_comp = (1.0 - norm_x) if rotation != 180 else norm_x
            return (norm_y_comp + norm_x_comp) / 2.0

        elif self.direction in ("tr", "diagonal_tr_bl"):
            # color1 top-right → color2 bottom-left
            # Apply rotation correction to components
            norm_y_comp = (1.0 - norm_y) if rotation != 90 else norm_y
            norm_x_comp = (1.0 - norm_x) if rotation != 180 else norm_x
            return (norm_y_comp + norm_x_comp) / 2.0

        elif self.direction in ("bl",):
            # color1 bottom-left → color2 top-right
            # Apply rotation correction to components
            norm_y_comp = norm_y if rotation != 270 else (1.0 - norm_y)
            norm_x_comp = norm_x if rotation != 180 else (1.0 - norm_x)
            return (norm_y_comp + norm_x_comp) / 2.0

        else:
            # Default to left→right with rotation correction
            factor = norm_x
            if rotation == 180:
                factor = 1.0 - factor
            return factor

    def render_frame(self, time_ms: int):
        """Render gradient frame, fading in from current LED state.

        Uses EXACT same gradient logic as GradientEffect2D, treating
        the 1D strip as a matrix 1×N (1 row, N columns).
        """
        progress = min(time_ms / self.duration_ms, 1.0)

        # Build target gradient using 2D matrix logic
        target_map = {}
        for i in range(self.linear.led_count):
            factor = self._calculate_gradient_factor(i)

            # Linear interpolation between color1 and color2
            target_map[i] = (
                int(self.base_color1[0] + (self.base_color2[0] - self.base_color1[0]) * factor),
                int(self.base_color1[1] + (self.base_color2[1] - self.base_color1[1]) * factor),
                int(self.base_color1[2] + (self.base_color2[2] - self.base_color1[2]) * factor),
            )

        if self.start_colors:
            # Interpolate from start state → target gradient
            color_map = {}
            for i in range(self.linear.led_count):
                target = target_map.get(i, (0, 0, 0))
                start = self.start_colors[i] if i < len(self.start_colors) else (0, 0, 0)
                final = (
                    int(start[0] + (target[0] - start[0]) * progress),
                    int(start[1] + (target[1] - start[1]) * progress),
                    int(start[2] + (target[2] - start[2]) * progress),
                )
                color_map[i] = final

            self._apply_color_map(color_map, int(time_ms))
        else:
            # No fade-in, apply target directly
            self.linear.apply_color_map(target_map)


class CornerGradientEffect1D(Animated1DEffect):
    """
    4-corner gradient effect for LINEAR devices with 2D topology.

    Uses world coordinates from device topology to apply bi-linear interpolation
    between 4 corner colors across multi-segment LED strips.
    """

    def __init__(self, linear: Linear1D, duration_ms: int = 1000,
                 color_tl: Tuple[int, int, int] = (255, 0, 0),
                 color_tr: Tuple[int, int, int] = (0, 255, 0),
                 color_br: Tuple[int, int, int] = (0, 0, 255),
                 color_bl: Tuple[int, int, int] = (255, 255, 0)):
        """
        Initialize 4-corner gradient effect for LINEAR device.

        Args:
            linear: Linear1D instance
            duration_ms: Effect duration
            color_tl: Top-left corner color
            color_tr: Top-right corner color
            color_br: Bottom-right corner color
            color_bl: Bottom-left corner color
        """
        super().__init__(linear, duration_ms)
        self.color_tl = color_tl
        self.color_tr = color_tr
        self.color_br = color_br
        self.color_bl = color_bl

    def _bilinear_interpolate(
        self,
        c00: Tuple[int, int, int],  # Top-left
        c10: Tuple[int, int, int],  # Top-right
        c01: Tuple[int, int, int],  # Bottom-left
        c11: Tuple[int, int, int],  # Bottom-right
        x: float,  # Normalized horizontal position [0, 1]
        y: float   # Normalized vertical position [0, 1]
    ) -> Tuple[int, int, int]:
        """
        Perform bi-linear interpolation between 4 corner colors.

        Formula: f(x,y) = (1-x)(1-y)c00 + x(1-y)c10 + (1-x)y c01 + xy c11

        Args:
            c00, c10, c01, c11: Corner colors (RGB tuples)
            x: Normalized horizontal position (0 = left, 1 = right)
            y: Normalized vertical position (0 = top, 1 = bottom)

        Returns:
            Interpolated RGB color
        """
        r = (
            (1 - x) * (1 - y) * c00[0] +
            x * (1 - y) * c10[0] +
            (1 - x) * y * c01[0] +
            x * y * c11[0]
        )

        g = (
            (1 - x) * (1 - y) * c00[1] +
            x * (1 - y) * c10[1] +
            (1 - x) * y * c01[1] +
            x * y * c11[1]
        )

        b = (
            (1 - x) * (1 - y) * c00[2] +
            x * (1 - y) * c10[2] +
            (1 - x) * y * c01[2] +
            x * y * c11[2]
        )

        return (int(r), int(g), int(b))

    def render_frame(self, time_ms: int):
        """Render 4-corner gradient using world coordinates from topology."""
        # Get global bounding box from topology
        bbox = self.linear.get_global_bbox()
        min_x, max_x = bbox['min_x'], bbox['max_x']
        min_y, max_y = bbox['min_y'], bbox['max_y']

        rows_span = max_y - min_y
        cols_span = max_x - min_x

        # Build color map for all LEDs using world coordinates
        color_map = {}

        for global_led_idx in range(self.linear.led_count):
            # Get world position of this LED
            zone_idx, local_idx = self.linear.get_zone_and_local_index(global_led_idx)
            world_x, world_y = self.linear.get_led_world_position(zone_idx, local_idx)

            # Normalize to [0, 1] within global bounding box
            norm_x = (world_x - min_x) / cols_span if cols_span > 0 else 0.0
            norm_y = (world_y - min_y) / rows_span if rows_span > 0 else 0.0

            # IMPORTANT: Y grows upward in world coords, but bilinear expects
            # y=0 at top, y=1 at bottom. Invert Y for correct interpolation.
            norm_y = 1.0 - norm_y

            # Apply bi-linear interpolation
            color = self._bilinear_interpolate(
                self.color_tl,  # Top-left (c00)
                self.color_tr,  # Top-right (c10)
                self.color_bl,  # Bottom-left (c01)
                self.color_br,  # Bottom-right (c11)
                norm_x, norm_y
            )

            color_map[global_led_idx] = color

        # Apply color map (supports fade-in if set)
        self._apply_color_map(color_map, int(time_ms))


class GlitchEffect1D(Animated1DEffect):
    """
    Glitch effect with random LED flashes, persistence, and color variation.

    Features:
    - Initial smooth transition to base color
    - Random LED glitches with configurable density
    - Some glitches become persistent (don't return to base)
    - Variable glitch duration and color variation
    """

    def __init__(self, linear: Linear1D, duration_ms: int = 5000,
                 base_color: Tuple[int, int, int] = (0, 0, 255),
                 glitch_colors: list = None,
                 glitch_percentage: float = 0.15,
                 glitch_duration_ms: int = 150,
                 duration_variability: float = 0.5,
                 persistence_percentage: float = 0.3,
                 color_variation: float = 0.2):
        """
        Initialize glitch effect.

        Args:
            linear: Linear1D instance
            duration_ms: Total effect duration
            base_color: Background color (default blue)
            glitch_colors: List of 3 glitch colors (default: red, green, cyan)
            glitch_percentage: % of LEDs glitching simultaneously (0-1)
            glitch_duration_ms: Duration of single glitch flash
            duration_variability: Random variation in glitch duration (0-1)
            persistence_percentage: % of glitched LEDs that become persistent (0-1)
            color_variation: Random color variation amount (0-1)
        """
        super().__init__(linear, duration_ms, fps=60)
        self.base_color = base_color
        self.glitch_colors = glitch_colors or [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 255, 255)   # Cyan
        ]
        self.glitch_percentage = glitch_percentage
        self.glitch_duration_ms = glitch_duration_ms
        self.duration_variability = duration_variability
        self.persistence_percentage = persistence_percentage
        self.color_variation = color_variation

    def _ease_in_out(self, t: float) -> float:
        """Smooth easing function."""
        return t * t * (3 - 2 * t)

    def _vary_color(self, base_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Apply random color variation."""
        num_channels = random.randint(1, 3)
        channels_to_vary = random.sample([0, 1, 2], num_channels)

        varied = list(base_color)
        for channel in channels_to_vary:
            variation = random.uniform(-self.color_variation, self.color_variation)
            varied[channel] = int(varied[channel] * (1 + variation))
            varied[channel] = max(0, min(255, varied[channel]))

        return tuple(varied)

    def _run_animation(self, on_complete: Optional[callable] = None):
        """Custom animation loop with glitch logic."""
        start_time = time.time()

        # Phase 1: Smooth transition to base color (500ms)
        transition_duration = 0.5
        transition_start = time.time()

        # Capture current LED colors
        initial_colors = []
        for i in range(self.linear.led_count):
            color = self.linear.get_led_color(i)
            initial_colors.append(color if color else (0, 0, 0))

        # Transition to base color
        while (time.time() - transition_start) < transition_duration:
            elapsed = time.time() - transition_start
            t = min(1.0, elapsed / transition_duration)
            t_eased = self._ease_in_out(t)

            color_map = {}
            for i in range(self.linear.led_count):
                color = _lerp_color_util(initial_colors[i], self.base_color, t_eased)
                color_map[i] = color

            self._apply_color_map(color_map, int((time.time() - start_time) * 1000))
            time.sleep(self.frame_time_ms / 1000)

        # Set final base color
        color_map = {i: self.base_color for i in range(self.linear.led_count)}
        self._apply_color_map(color_map, int((time.time() - start_time) * 1000))

        # Phase 2: Glitch loop
        persistent_leds = set()
        effect_start = time.time()
        effect_duration_s = self.duration_ms / 1000.0

        num_glitch_leds = max(1, int(self.linear.led_count * self.glitch_percentage))

        while self.running and (time.time() - effect_start) < effect_duration_s:
            # Select LEDs to glitch (exclude persistent ones)
            available_leds = [i for i in range(self.linear.led_count) if i not in persistent_leds]
            num_to_glitch = min(num_glitch_leds, len(available_leds))

            if num_to_glitch > 0:
                glitching_leds = random.sample(available_leds, num_to_glitch)
            else:
                glitching_leds = []

            # Calculate varied glitch duration
            variation = random.uniform(-self.duration_variability, self.duration_variability)
            actual_duration_ms = self.glitch_duration_ms * (1 + variation)

            # Apply glitch colors
            color_map = {}
            for led_idx in glitching_leds:
                base_glitch = random.choice(self.glitch_colors)
                varied_color = self._vary_color(base_glitch)
                color_map[led_idx] = varied_color

            self._apply_color_map(color_map, int((time.time() - start_time) * 1000))
            time.sleep(actual_duration_ms / 1000)

            # Determine which LEDs become persistent
            new_persistent = set()
            if glitching_leds:
                num_persist = max(0, int(len(glitching_leds) * self.persistence_percentage))
                if num_persist > 0:
                    new_persistent = set(random.sample(glitching_leds, num_persist))

            persistent_leds.update(new_persistent)

            # Non-persistent LEDs return to base color
            color_map = {}
            for led_idx in glitching_leds:
                if led_idx not in new_persistent:
                    color_map[led_idx] = self.base_color

            if color_map:
                self._apply_color_map(color_map, int((time.time() - start_time) * 1000))

        self.running = False
        if on_complete:
            on_complete()
