"""
Spatial 2D effects for keyboard matrices with color override support.

These effects define HOW light moves across 2D matrices (keyboards).
They support dynamic color override from keyframe interpolation in fused effects.
"""
import time
import math
import random
import threading
from typing import Tuple, Optional, List, Callable, Dict, Any, Union
from .keyboard_matrix_2d import KeyboardMatrix2D
from utils.color_utils import lerp_color as _lerp_color, hsv_to_rgb as _hsv_to_rgb


# Precomputed constant: avoids recalculating 2*pi per LED per frame in wave/plasma/aurora/ocean
_TAU = 2.0 * math.pi


class Animated2DEffect:
    """Base class for animated 2D spatial effects."""

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int, fps: int = 30):
        """
        Initialize animated effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total duration in milliseconds
            fps: Frames per second
        """
        self.matrix = matrix
        self.duration_ms = duration_ms
        self.fps = fps
        self.frame_time_ms = 1000 / fps
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.current_color: Optional[Tuple[int, int, int]] = None  # Color override from fused effect keyframes
        self.fade_in_ms = 0  # To be set externally by the renderer
        self._initial_colors: Optional[Dict[int, Tuple[int, int, int]]] = None  # Lazy-loaded initial LED colors for fade-in
        self.base_color: Tuple[int, int, int] = (0, 0, 0)  # Base color fallback

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
                device_colors = self.matrix.device.colors
                # Convert to dict: led_idx -> (r, g, b)
                self._initial_colors = {
                    idx: (c.red, c.green, c.blue)
                    for idx, c in enumerate(device_colors)
                }
            except (AttributeError, IndexError):
                # Fallback: if device.colors not available, assume black
                self._initial_colors = {}

    def _apply_color_map(self, color_map: dict, time_ms: int):
        """Helper to apply colors to the matrix with automatic fade-in logic.

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
                initial = self._initial_colors.get(led_idx, (0, 0, 0)) if self._initial_colors is not None else (0, 0, 0)
                init_r, init_g, init_b = initial

                # Linear interpolation: initial * (1 - progress) + target * progress
                faded_map[led_idx] = (
                    int(init_r + (target_r - init_r) * progress),
                    int(init_g + (target_g - init_g) * progress),
                    int(init_b + (target_b - init_b) * progress),
                )

            self.matrix.apply_color_map(faded_map)
        else:
            self.matrix.apply_color_map(color_map)

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

    def start(self, blocking: bool = False, on_complete: Optional[Callable[[], None]] = None):
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
            if self.thread:
                self.thread.start()

    def _run_animation(self, on_complete: Optional[Callable[[], None]] = None):
        """Internal animation loop with exception handling."""
        from utils.openrgb_client import OpenRGBDisconnected

        start_time = time.time()
        frame_count = 0

        while self.running:
            try:
                elapsed_ms = (time.time() - start_time) * 1000

                if elapsed_ms >= self.duration_ms:
                    # Render the exact final frame
                    self.render_frame(self.duration_ms)

                    # Call completion callback immediately
                    if on_complete is not None:
                        on_complete()
                    break

                self.render_frame(int(elapsed_ms))

                # Reset error counter on successful frame
                self._consecutive_errors = 0

                # Sleep to maintain target FPS
                frame_count += 1
                expected_time = frame_count * self.frame_time_ms / 1000
                actual_time = time.time() - start_time
                sleep_time = max(0.0, expected_time - actual_time)

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
                    if on_complete is not None:
                        on_complete()
                    break

                time.sleep(0.1)  # Let reconnection happen

            except Exception as e:
                self._last_error = e
                self._consecutive_errors += 1
                print(f"[Effect] Error in frame {frame_count}: {e}")

                if self._consecutive_errors >= self._max_consecutive_errors:
                    self.running = False
                    if on_complete is not None:
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


class HorizontalSweepEffect(Animated2DEffect):
    """Horizontal line sweeping across the keyboard."""

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 128, 0),
                 direction: str = 'down', trail_length: int = 2):
        """
        Initialize horizontal sweep effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total duration
            color: Base RGB color (can be overridden by set_color())
            direction: 'down' or 'up'
            trail_length: Number of trailing rows
        """
        super().__init__(matrix, duration_ms)
        self.base_color = color
        self.direction = direction
        self.trail_length = trail_length
        # Cache LED indices once — avoids rebuilding the list every frame
        self._all_led_indices = [led_idx for _, _, led_idx in matrix.get_all_led_coords()]

    def render_frame(self, time_ms: int):
        """Render sweep frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color is not None else self.base_color

        progress = time_ms / self.duration_ms
        total_rows = self.matrix.rows

        if self.direction == 'down':
            current_row = int(progress * total_rows)
        else:
            current_row = int((1 - progress) * total_rows)

        # Initialize all LEDs to black to clear previous frame
        color_map = dict.fromkeys(self._all_led_indices, (0, 0, 0))

        # Draw current row and trail
        for i in range(self.trail_length):
            row = current_row - i
            if 0 <= row < total_rows:
                intensity = 1.0 - (i / self.trail_length)
                trail_color = (
                    int(active_color[0] * intensity),
                    int(active_color[1] * intensity),
                    int(active_color[2] * intensity)
                )
                line_map = self.matrix.generate_horizontal_line(row, trail_color)
                color_map.update(line_map)

        self._apply_color_map(color_map, int(time_ms))


class VerticalSweepEffect(Animated2DEffect):
    """Vertical line sweeping across the keyboard."""

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 128, 0),
                 direction: str = 'right', trail_length: int = 2):
        """
        Initialize vertical sweep effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total duration
            color: Base RGB color (can be overridden by set_color())
            direction: 'right' or 'left'
            trail_length: Number of trailing columns
        """
        super().__init__(matrix, duration_ms)
        self.base_color = color
        self.direction = direction
        self.trail_length = trail_length
        self._all_led_indices = [led_idx for _, _, led_idx in matrix.get_all_led_coords()]

    def render_frame(self, time_ms: int):
        """Render sweep frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color is not None else self.base_color

        progress = time_ms / self.duration_ms
        total_cols = self.matrix.cols

        if self.direction == 'right':
            current_col = int(progress * total_cols)
        else:
            current_col = int((1 - progress) * total_cols)

        # Initialize all LEDs to black to clear previous frame
        color_map = dict.fromkeys(self._all_led_indices, (0, 0, 0))

        # Draw current column and trail
        for i in range(self.trail_length):
            col = current_col - i
            if 0 <= col < total_cols:
                intensity = 1.0 - (i / self.trail_length)
                trail_color = (
                    int(active_color[0] * intensity),
                    int(active_color[1] * intensity),
                    int(active_color[2] * intensity)
                )
                line_map = self.matrix.generate_vertical_line(col, trail_color)
                color_map.update(line_map)

        self._apply_color_map(color_map, int(time_ms))


class RippleEffect(Animated2DEffect):
    """Expanding ripple from center point."""

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 3000,
                 color: Tuple[int, int, int] = (0, 128, 255),
                 center: Optional[Tuple[int, int]] = None):
        """
        Initialize ripple effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total duration
            color: Base RGB color (can be overridden by set_color())
            center: (row, col) center point, defaults to keyboard center
        """
        super().__init__(matrix, duration_ms)
        self.base_color = color
        cr, cc = center if center else (matrix.rows // 2, matrix.cols // 2)
        self.center = (cr, cc)

        # Precompute distances from center to each LED once — center is fixed.
        # Eliminates math.sqrt() + method-dispatch overhead per LED per frame.
        self._led_distances: List[Tuple[int, float]] = []
        max_d = 0.0
        for row, col, led_idx in matrix.get_all_led_coords():
            dr = int(row) - int(cr)
            dc = int(col) - int(cc)
            d = math.sqrt(dr * dr + dc * dc)
            self._led_distances.append((led_idx, d))
            if d > max_d:
                max_d = d
        self.max_radius = max_d

    def render_frame(self, time_ms: int):
        """Render ripple frame with precomputed distances (no per-frame sqrt)."""
        active_color = self.current_color if self.current_color is not None else self.base_color

        current_radius = (time_ms / self.duration_ms) * self.max_radius
        if current_radius <= 0:
            current_radius = 0.001  # avoid division by zero

        r, g, b = active_color
        color_map = {}
        for led_idx, dist in self._led_distances:
            if dist <= current_radius:
                t = dist / current_radius          # 0 at center, 1 at wavefront
                intensity = 1.0 - t * t            # quadratic falloff, no ** needed
                color_map[led_idx] = (int(r * intensity), int(g * intensity), int(b * intensity))
            else:
                color_map[led_idx] = (0, 0, 0)

        self._apply_color_map(color_map, int(time_ms))


class WaveEffect(Animated2DEffect):
    """Sine wave animation across keyboard, scrolling in a constant direction."""

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 4000,
                 color: Tuple[int, int, int] = (255, 128, 0),
                 color_bg: Tuple[int, int, int] = (0, 0, 0),
                 direction: str = 'horizontal', wavelength: float = 4.0,
                 num_loops: int = 1):
        super().__init__(matrix, duration_ms)
        self.base_color = color
        self.color_bg = color_bg
        self.direction = direction
        self.wavelength = wavelength
        self.num_loops = max(1, num_loops)

    def render_frame(self, time_ms: int):
        """Render wave frame.  num_loops full phase-cycles complete in duration_ms."""
        active_color = self.current_color if self.current_color is not None else self.base_color
        # Scale time so that num_loops wavelengths scroll past in duration_ms
        time_effective = (time_ms / self.duration_ms) * self.num_loops
        color_map = self.matrix.generate_wave(
            time_effective,
            direction=self.direction,
            color=active_color,
            wavelength=self.wavelength,
            speed=1.0,
            color_bg=self.color_bg,
        )
        self._apply_color_map(color_map, int(time_ms))


class BumpEffect2D(Animated2DEffect):
    """Gaussian light-hill that bounces between the keyboard edges (ping-pong).

    A single smooth dome of light travels from one edge to the other and
    reverses direction each time it reaches the opposite edge.

    color    = peak color (Color 2 in UI — visible at the center of the hill)
    color_bg = background color (Color 1 in UI — visible at both edges)
    sigma computed dynamically as max_pos / 4 so one clean hill fills the keyboard.
    num_loops = complete back-and-forth cycles within duration_ms.
    """

    _DIR = {
        'right':      ('col',       False),
        'horizontal': ('col',       False),
        'left':       ('col',       True),
        'down':       ('row',       False),
        'vertical':   ('row',       False),
        'top':        ('row',       True),
        'tl':         ('diag_sum',  True),   # towards TL (BR -> TL)
        'br':         ('diag_sum',  False),  # towards BR (TL -> BR)
        'tr':         ('diag_diff', True),   # towards TR (BL -> TR)
        'bl':         ('diag_diff', False),  # towards BL (TR -> BL)
    }

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 128, 0),
                 color_bg: Tuple[int, int, int] = (0, 0, 0),
                 direction: str = 'right',
                 num_loops: int = 1):
        super().__init__(matrix, duration_ms)
        self.base_color = color
        self.color_bg = color_bg
        self.direction = direction
        self.num_loops = max(1, num_loops)

    def render_frame(self, time_ms: int):
        """Render Gaussian hill at its current ping-pong position."""
        active_color = self.current_color if self.current_color is not None else self.base_color

        axis, reverse = self._DIR.get(self.direction, ('col', False))
        max_diag = max(1, (self.matrix.rows - 1) + (self.matrix.cols - 1))
        max_pos = (self.matrix.cols - 1 if axis == 'col' else
                   self.matrix.rows - 1 if axis == 'row' else max_diag)

        # sigma = max_pos/4 → edges are at ~2σ → intensity ≈ 0.13 (≈ full color_bg)
        sigma = max(1.0, max_pos / 4.0)

        # 1 loop = one full back-and-forth; traversal_ms = one half-trip
        traversal_ms = self.duration_ms / (2 * self.num_loops)
        t_raw = (time_ms % (2 * traversal_ms)) / traversal_ms  # [0, 2)
        t_bounce = t_raw if t_raw <= 1.0 else 2.0 - t_raw      # triangle [0→1→0→...]

        # Hill center travels from edge 0 to edge max_pos
        center = t_bounce * max_pos

        r0, g0, b0 = self.color_bg
        r1, g1, b1 = active_color

        color_map = {}
        for row, col, led_idx in self.matrix.get_all_led_coords():
            r_int, c_int = int(row), int(col)
            if axis == 'col':
                pos = (max_pos - c_int) if reverse else c_int
            elif axis == 'row':
                pos = (max_pos - r_int) if reverse else r_int
            elif axis == 'diag_sum':
                raw = r_int + c_int
                pos = (max_diag - raw) if reverse else raw
            else:  # diag_diff
                raw = r_int + (self.matrix.cols - 1 - c_int)
                pos = (max_diag - raw) if reverse else raw

            dist = float(pos) - float(center)
            intensity = math.exp(-(dist * dist) / (2 * sigma * sigma))

            color_map[led_idx] = (
                int(r0 + (r1 - r0) * intensity),
                int(g0 + (g1 - g0) * intensity),
                int(b0 + (b1 - b0) * intensity),
            )

        self._apply_color_map(color_map, int(time_ms))


class ColorCycleEffect2D(Animated2DEffect):
    """Multi-color scrolling gradient across the keyboard.

    N colors are distributed as a smooth interpolated gradient along the
    chosen axis.  The gradient scrolls continuously in the given direction.
    speed=1.0 means exactly one full color cycle over the effect duration.
    """

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 4000,
                 colors: Optional[List[Tuple[int, int, int]]] = None,
                 direction: str = 'left', speed: float = 1.0):
        super().__init__(matrix, duration_ms)
        self.colors = colors if colors else [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        self.direction = direction
        self.speed = speed

    @staticmethod
    def _cycle_color(colors: List[Tuple[int, int, int]], t: float) -> Tuple[int, int, int]:
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
        """Render one frame of the scrolling color cycle."""
        # scroll goes 0 -> speed over the full duration
        scroll = (time_ms / self.duration_ms) * self.speed
        mc = max(self.matrix.cols - 1, 1)
        mr = max(self.matrix.rows - 1, 1)
        color_map = {}
        for row, col, led_idx in self.matrix.get_all_led_coords():
            nc = col / mc   # normalised column  0..1
            nr = row / mr   # normalised row     0..1
            d = self.direction
            if d in ('left', 'horizontal'):
                # colors flow leftward: color[0] exits from the left edge
                t = (nc + scroll) % 1.0
            elif d == 'right':
                t = (nc - scroll) % 1.0
            elif d in ('up', 'top', 'vertical'):
                # colors flow upward: RED moves bottom→top (nr decreases over time)
                t = (nr + scroll) % 1.0
            elif d == 'down':
                # colors flow downward: RED moves top→bottom (nr increases over time)
                t = (nr - scroll) % 1.0
            elif d == 'tl':
                # top-left: diagonal from bottom-right toward top-left
                t = ((nc + nr) / 2 + scroll) % 1.0
            elif d == 'br':
                t = ((nc + nr) / 2 - scroll) % 1.0
            elif d == 'tr':
                # top-right: diagonal from bottom-left toward top-right
                t = ((1 - nc + nr) / 2 + scroll) % 1.0
            elif d == 'bl':
                t = ((1 - nc + nr) / 2 - scroll) % 1.0
            else:
                t = (nc + scroll) % 1.0
            color_map[led_idx] = self._cycle_color(self.colors, t)
        self._apply_color_map(color_map, int(time_ms))


class BloomEffect(Animated2DEffect):
    """Bloom effect: expanding ring with spatial color cycling.

    Each LED cycles through the color palette based on when the expanding ring
    touches it. Once touched, the LED continues cycling until reaching t=100%
    (final color). The ring can expand beyond matrix borders using expansion_factor.

    Default palette: white → yellow → orange → red → black
    """

    _DEFAULT_COLORS = [
        (255, 255, 255),
        (255, 255,   0),
        (255, 128,   0),
        (255,   0,   0),
        (  0,   0,   0),
    ]

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 2000,
                 colors=None, expansion_factor: float = 2.0,
                 center: Optional[Tuple[int, int]] = None):
        """
        Args:
            matrix:           KeyboardMatrix2D instance
            duration_ms:      Total duration
            colors:           Color palette for spatial cycling
            expansion_factor: Multiplier for max_radius (1.0-5.0) - allows ring expansion beyond borders
            center:           (row, col) origin; defaults to matrix center
        """
        super().__init__(matrix, duration_ms)

        # Try custom center from topology (world coordinates)
        custom_center = matrix.get_effect_center()
        if custom_center:
            # Convert world (X, Y) to matrix (row, col): Y→row, X→col
            self.center = (int(custom_center[1]), int(custom_center[0]))
        elif center:
            self.center = center
        else:
            # Fallback: geometric center
            self.center = (matrix.rows // 2, matrix.cols // 2)

        self.expansion_factor = max(1.0, min(5.0, expansion_factor))

        # Base max_radius: distance to furthest corner
        base_max_radius = max(
            matrix.distance(self.center, (0, 0)),
            matrix.distance(self.center, (0, matrix.cols - 1)),
            matrix.distance(self.center, (matrix.rows - 1, 0)),
            matrix.distance(self.center, (matrix.rows - 1, matrix.cols - 1))
        )
        # Apply expansion factor to allow ring expansion beyond matrix
        self.max_radius = base_max_radius * self.expansion_factor

        self._palette = [(int(c[0]), int(c[1]), int(c[2])) for c in colors] if colors is not None else self._DEFAULT_COLORS

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
        progress = time_ms / self.duration_ms
        current_radius = progress * self.max_radius

        color_map = {}

        # DEBUG: Sample 5 LEDs at key progress points
        debug_sample = progress in [0.5, 0.9, 0.995]

        # Final frame guard: ensure all LEDs show final color (t=1.0)
        # Only last 0.5% of duration to allow full animation visibility
        if progress >= 0.995:
            final_color = self._palette_lerp(1.0)
            for row, col, led_idx in self.matrix.get_all_led_coords():
                color_map[led_idx] = final_color
        else:
            # Iterate through all LEDs
            for row, col, led_idx in self.matrix.get_all_led_coords():
                dist = self.matrix.distance(self.center, (row, col))

                # LED already "touched" by expanding ring: cycle through colors
                if dist <= current_radius:
                    # Time since ring touched this LED (in radius units)
                    time_since_touch = current_radius - dist
                    # Normalize to [0,1] based on TOTAL max_radius (with expansion factor)
                    # This ensures color cycling speed is proportional to expansion distance
                    t_touch = min(1.0, time_since_touch / self.max_radius) if self.max_radius > 0 else 0.0
                    color = self._palette_lerp(t_touch)
                    color_map[led_idx] = color
                else:
                    # LEDs not yet touched: explicitly set to black
                    color_map[led_idx] = (0, 0, 0)

        self._apply_color_map(color_map, int(time_ms))


class ExplosionEffect(Animated2DEffect):
    """True explosion: an expanding ring with a decaying trail behind it.

    The wavefront (ring) moves outward from the center.  LEDs inside the ring
    glow with a decaying "burn" color whose intensity drops exponentially with
    the time elapsed since the ring passed them.  LEDs ahead of the ring
    remain off until it reaches them.

    Two colors:
        colors[0] — ring peak color   (default: white-yellow)
        colors[1] — trail/burn color  (default: deep orange-red)
    """

    _DEFAULT_COLORS = [
        (255, 255, 255),  # ring peak  — pure white flash (Quick Win: more dramatic!)
        (255,  40,   0),  # burn trail — intense red-orange (was 255,60,0)
    ]

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 2000,
                 colors=None, ring_width: float = 0.1, decay_rate: float = 0.4,
                 expansion_factor: float = 2.0,
                 center: Optional[Tuple[int, int]] = None):
        """
        Args:
            matrix:           KeyboardMatrix2D instance
            duration_ms:      Total duration
            colors:           [ring_color, trail_color]; defaults to white + intense red
            ring_width:       Thickness of ring as fraction of max_radius (0.05–0.5, default 0.1)
            decay_rate:       Trail fade speed; fraction of duration per e-fold (default 0.4)
            expansion_factor: Ring expansion multiplier (1.0-5.0, default 2.0)
            center:           (row, col) origin; defaults to matrix center
        """
        super().__init__(matrix, duration_ms)

        # Try custom center from topology (world coordinates)
        custom_center = matrix.get_effect_center()
        if custom_center:
            # Convert world (X, Y) to matrix (row, col): Y→row, X→col
            self.center = (int(custom_center[1]), int(custom_center[0]))
        elif center:
            self.center = center
        else:
            # Fallback: geometric center
            self.center = (matrix.rows // 2, matrix.cols // 2)

        self.ring_width = max(0.02, ring_width)
        self.decay_rate = max(0.05, decay_rate)
        self.expansion_factor = max(1.0, min(5.0, expansion_factor))

        # Base max_radius: distance to furthest corner
        base_max_radius = max(
            matrix.distance(self.center, (0, 0)),
            matrix.distance(self.center, (0, matrix.cols - 1)),
            matrix.distance(self.center, (matrix.rows - 1, 0)),
            matrix.distance(self.center, (matrix.rows - 1, matrix.cols - 1))
        )
        # Apply expansion factor to allow ring expansion beyond matrix
        self.max_radius = base_max_radius * self.expansion_factor


        palette = [(int(c[0]), int(c[1]), int(c[2])) for c in colors] if colors is not None else self._DEFAULT_COLORS
        self._ring_color  = palette[0] if len(palette) > 0 else self._DEFAULT_COLORS[0]
        self._trail_color = palette[1] if len(palette) > 1 else self._DEFAULT_COLORS[1]

    def render_frame(self, time_ms: int):
        progress     = time_ms / self.duration_ms
        ring_radius  = progress * self.max_radius        # leading edge position
        ring_px      = self.ring_width * self.max_radius  # ring thickness in matrix units
        decay_tc     = self.decay_rate * self.duration_ms  # time constant for trail [ms]

        rc, tc = self._ring_color, self._trail_color
        color_map = {}

        # ── QUICK WIN 1: Impact Flash ──────────────────────────────────────────
        # First 5% of animation: white flash at center (simulates initial explosion impact)
        if progress < 0.05:
            initial_flash_radius = self.max_radius * 0.15  # 15% of max_radius
            for row, col, led_idx in self.matrix.get_all_led_coords():
                dist = self.matrix.distance(self.center, (row, col))
                if dist <= initial_flash_radius:
                    # Inside flash zone: full white with smooth falloff
                    falloff = 1.0 - (dist / initial_flash_radius)
                    intensity = falloff ** 0.5  # Soft edge
                    color_map[led_idx] = (
                        int(255 * intensity),
                        int(255 * intensity),
                        int(255 * intensity),
                    )
                else:
                    color_map[led_idx] = (0, 0, 0)

        # ── Normal Explosion Rendering ────────────────────────────────────────
        else:
            # Calculate fade-out multiplier for final portion (smooth scroll to black)
            # Last 25% of duration: gradually fade all colors to black + accelerate trail decay
            fadeout_multiplier = 1.0
            accelerated_decay_factor = 1.0  # Speeds up trail decay in final phase

            if progress >= 0.75:
                # Map progress [0.75, 1.0] → fadeout [1.0, 0.0]
                fadeout_progress = (progress - 0.75) / 0.25  # 0.0 at 0.75, 1.0 at 1.0
                fadeout_multiplier = 1.0 - fadeout_progress
                # Accelerate trail decay: make decay_tc smaller = faster decay
                # At progress=0.75 → factor=1.0 (normal), at progress=1.0 → factor=0.2 (5x faster)
                accelerated_decay_factor = 1.0 - 0.8 * fadeout_progress

            for row, col, led_idx in self.matrix.get_all_led_coords():
                dist = self.matrix.distance(self.center, (row, col))
                dist_behind_front = ring_radius - dist  # positive = ring has passed this LED

                if dist_behind_front < 0:
                    # Ahead of ring → off
                    color_map[led_idx] = (0, 0, 0)

                elif dist_behind_front <= ring_px:
                    # Inside the ring wavefront: peak brightness at leading edge, fade inward
                    t = dist_behind_front / ring_px   # 0 = at leading edge, 1 = inner edge
                    # Smooth bell: full bright at t=0, fades toward t=1
                    intensity = (1.0 - t) ** 1.2
                    intensity *= fadeout_multiplier  # Apply global fade-out
                    color_map[led_idx] = (
                        int(rc[0] * intensity),
                        int(rc[1] * intensity),
                        int(rc[2] * intensity),
                    )

                else:
                    # Behind the ring: decaying trail
                    # When did the ring pass this LED?
                    time_of_pass_ms = (dist / self.max_radius) * self.duration_ms
                    time_since_pass  = time_ms - time_of_pass_ms
                    # Apply accelerated decay in final phase (smaller decay_tc = faster decay)
                    effective_decay_tc = max(decay_tc * accelerated_decay_factor, 1.0)
                    intensity = math.exp(-time_since_pass / effective_decay_tc)
                    intensity = max(0.0, intensity)
                    intensity *= fadeout_multiplier  # Apply global fade-out
                    color_map[led_idx] = (
                        int(tc[0] * intensity),
                        int(tc[1] * intensity),
                        int(tc[2] * intensity),
                    )

        self._apply_color_map(color_map, int(time_ms))


class ImplodingCirclesEffect(Animated2DEffect):
    """Multiple circles imploding to center."""

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 3000,
                 color: Tuple[int, int, int] = (0, 255, 128),
                 center: Optional[Tuple[int, int]] = None, num_circles: int = 5):
        """
        Initialize imploding circles effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total duration
            color: Base RGB color (can be overridden by set_color())
            center: (row, col) center point
            num_circles: Number of concentric circles
        """
        super().__init__(matrix, duration_ms)
        self.base_color = color
        self.center = center or (matrix.rows // 2, matrix.cols // 2)
        self.num_circles = num_circles
        # Precompute distances from center to every LED — identical pattern to RippleEffect
        cr, cc = self.center
        self._led_distances: List[Tuple[int, float]] = []
        max_d = 0.0
        for row, col, led_idx in matrix.get_all_led_coords():
            dr, dc = int(row) - int(cr), int(col) - int(cc)
            d = math.sqrt(dr * dr + dc * dc)
            self._led_distances.append((led_idx, d))
            if d > max_d:
                max_d = d
        self.max_radius = max_d
        self._thickness = 0.8

    def render_frame(self, time_ms: int):
        """Render imploding circles with a single LED pass (precomputed distances)."""
        active_color = self.current_color if self.current_color is not None else self.base_color
        progress = time_ms / self.duration_ms

        # Precompute circle ring parameters for this frame (O(num_circles))
        rings = []
        for i in range(self.num_circles):
            circle_start = i / self.num_circles * 0.3
            circle_progress = max(0.0, (progress - circle_start) / (1 - circle_start))
            if circle_progress > 0.0:
                radius = self.max_radius * (1.0 - circle_progress)
                intensity = 1.0 - circle_progress * 0.5
                rings.append((radius, intensity))

        r0, g0, b0 = active_color
        thick = self._thickness
        color_map = {}
        for led_idx, dist in self._led_distances:
            best = None
            for radius, intensity in rings:
                if abs(dist - radius) <= thick:
                    best = (int(r0 * intensity), int(g0 * intensity), int(b0 * intensity))
                    break  # nearest ring wins
            color_map[led_idx] = best if best else (0, 0, 0)

        self._apply_color_map(color_map, int(time_ms))


class DiagonalSweepEffect(Animated2DEffect):
    """Diagonal line sweeping across keyboard."""

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 0, 255),
                 direction: int = 1):
        """
        Initialize diagonal sweep effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total duration
            color: Base RGB color (can be overridden by set_color())
            direction: 1 for TL->BR, -1 for TR->BL
        """
        super().__init__(matrix, duration_ms)
        self.base_color = color
        self.direction = direction
        self.max_offset = matrix.rows + matrix.cols

    def render_frame(self, time_ms: int):
        """Render diagonal sweep frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color is not None else self.base_color

        progress = time_ms / self.duration_ms
        offset = -self.max_offset / 2 + progress * self.max_offset

        color_map = self.matrix.generate_diagonal_line(
            offset,
            active_color,
            thickness=1.0,
            direction=self.direction
        )

        self._apply_color_map(color_map, int(time_ms))


class GlitchEffect2D(Animated2DEffect):
    """
    Glitch effect with random LED flashes, persistence, and color variation.

    Features:
    - Initial smooth transition to base color
    - Random LED glitches with configurable density
    - Some glitches become persistent (don't return to base)
    - Variable glitch duration and color variation
    """

    def __init__(self, matrix, duration_ms: int = 5000,
                 base_color: Tuple[int, int, int] = (0, 0, 255),
                 glitch_colors: Optional[List[Tuple[int, int, int]]] = None,
                 glitch_percentage: float = 0.15,
                 glitch_duration_ms: int = 150,
                 duration_variability: float = 0.5,
                 persistence_percentage: float = 0.3,
                 color_variation: float = 0.2):
        """
        Initialize glitch effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total effect duration
            base_color: Background color (default blue)
            glitch_colors: List of 3 glitch colors (default: red, green, cyan)
            glitch_percentage: % of LEDs glitching simultaneously (0-1)
            glitch_duration_ms: Duration of single glitch flash
            duration_variability: Random variation in glitch duration (0-1)
            persistence_percentage: % of glitched LEDs that become persistent (0-1)
            color_variation: Random color variation amount (0-1)
        """
        super().__init__(matrix, duration_ms, fps=60)
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

    def _run_animation(self, on_complete: Optional[Callable[[], None]] = None):
        """Custom animation loop with glitch logic."""
        start_time = time.time()

        # Get all LED indices from matrix (led_to_coord is the correct attribute)
        all_led_indices = list(self.matrix.led_to_coord.keys())
        total_leds = len(all_led_indices)

        # Initialize with base color (fade-in handled by standard mechanism via fade_in_ms)
        base_color_map = {led_idx: self.base_color for led_idx in all_led_indices}

        # Glitch loop
        persistent_leds = set()
        effect_start = time.time()
        effect_duration_s = self.duration_ms / 1000.0

        num_glitch_leds = max(1, int(total_leds * self.glitch_percentage))

        while self.running and (time.time() - effect_start) < effect_duration_s:
            # Apply base color to non-glitching LEDs (fade-in happens automatically via _apply_color_map)
            elapsed_ms = int((time.time() - start_time) * 1000)
            non_glitching_map = {led_idx: self.base_color for led_idx in all_led_indices if led_idx not in persistent_leds}
            if non_glitching_map:
                self._apply_color_map(non_glitching_map, elapsed_ms)

            # Select LEDs to glitch (exclude persistent ones)
            available_leds = [i for i in all_led_indices if i not in persistent_leds]
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


# =============================================================================
# FireEffect2D - Cellular automata fire simulation
# =============================================================================

class FireEffect2D(Animated2DEffect):
    """
    Fire via cellular automata — same algorithm as reference 07_pixel_matrix_effects.py.

    Integer heat values 0-7 map directly to a discrete 8-step palette.
    Two hidden source rows (rows, rows+1) feed the visible grid from below.
    Single-pass 2:1:1 weighted diffusion + integer dissipation (randint 0-1)
    reproduce the authentic cellular-automata fire look from the reference.

    colors[0] = ember base    (default dark-red     (200,  30, 0))
    colors[1] = flame peak    (default bright-yellow (255, 220, 0))
    """

    _N = 8  # palette size: heat indices 0..7

    @staticmethod
    def _make_palette(ember: tuple, peak: tuple) -> list:
        """
        8-step palette that reproduces the reference colors when defaults are used:
          0: black          1: ~(40,6,0)       2: ~(120,18,0)   3: ember
          4: ember->peak 1/3  5: ember->peak 2/3  6: peak        7: warm near-white
        """
        black    = (0, 0, 0)
        warm_tip = (255, 255, 80)   # warm near-white at flame tip (matches reference)
        return [
            black,                              # 0 -- spento
            _lerp_color(black, ember, 0.20),    # 1 -- brace
            _lerp_color(black, ember, 0.60),    # 2 -- rosso scuro
            ember,                              # 3 -- rosso/ember
            _lerp_color(ember, peak, 1 / 3),    # 4 -- arancione scuro
            _lerp_color(ember, peak, 2 / 3),    # 5 -- arancione
            peak,                               # 6 -- giallo/peak
            _lerp_color(peak, warm_tip, 0.50),  # 7 -- giallo chiaro
        ]

    def __init__(self, matrix, params):
        super().__init__(matrix, params.duration_ms)
        self.intensity     = params.intensity if params.intensity is not None else 0.85
        self.loop_infinite = params.loop_infinite
        ember = tuple(params.colors[0]) if len(params.colors) > 0 else (200,  30, 0)
        peak  = tuple(params.colors[1]) if len(params.colors) > 1 else (255, 220, 0)
        self._palette = self._make_palette(ember, peak)
        rows, cols = matrix.rows, matrix.cols
        # Integer heat grid: rows+2 -- two hidden source rows below the visible area
        self._heat: List[List[int]] = [[0] * cols for _ in range(rows + 2)]
        self._led_grid: List[List[Optional[int]]] = [
            [matrix.get_led_index(r, c) for c in range(cols)]
            for r in range(rows)
        ]

    def _run_animation(self, on_complete=None):
        self.running   = True
        rows, cols     = self.matrix.rows, self.matrix.cols
        max_heat       = self._N - 1       # 7
        palette        = self._palette
        heat           = self._heat
        intensity      = self.intensity
        start_time     = time.time()
        frame_dt       = 1 / 30            # 30 fps target

        while self.running:
            if not self.loop_infinite and (time.time() - start_time) * 1000 >= self.duration_ms:
                break

            frame_start = time.time()

            # 1. Feed hidden source rows (heat[rows] and heat[rows+1])
            for c in range(cols):
                if random.random() < intensity:
                    heat[rows + 1][c] = max_heat
                else:
                    heat[rows + 1][c] = max(0, max_heat - random.randint(0, 2))

            # 2. Single-pass upward diffusion: 2:1:1 weighted + integer dissipation.
            #    Each row reads from the row below (already updated this frame) --
            #    Gauss-Seidel style makes heat rise faster, authentic CA behavior.
            for r in range(rows + 1, 0, -1):
                row_src = heat[r]
                row_dst = heat[r - 1]
                for c in range(cols):
                    lc  = c - 1 if c > 0         else 0
                    rc  = c + 1 if c < cols - 1  else cols - 1
                    avg = (row_src[c] * 2 + row_src[lc] + row_src[rc]) / 4
                    row_dst[c] = max(0, int(avg) - random.randint(0, 1))

            # 3. Render visible rows 0..rows-1
            color_map = {}
            for r in range(rows):
                row_leds = self._led_grid[r]
                row_heat = heat[r]
                for c in range(cols):
                    led_idx = row_leds[c]
                    if led_idx is not None:
                        color_map[led_idx] = palette[min(max_heat, row_heat[c])]
            self._apply_color_map(color_map, int((time.time() - start_time) * 1000))

            elapsed = time.time() - frame_start
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# MatrixRainEffect2D - Falling columns of green characters
# =============================================================================

class MatrixRainEffect2D(Animated2DEffect):
    """
    Matrix rain: columns fall from top to bottom.
    Each column has a bright head and a fading trail.
    Colors cycle through the provided palette (default: black/dark-green/bright-green).
    density multiplies the number of simultaneous active columns.
    """

    def __init__(self, matrix, params):
        super().__init__(matrix, params.duration_ms)
        self.loop_infinite = params.loop_infinite
        self.density = params.density if params.density is not None else 1.0
        colors = params.colors if len(params.colors) >= 3 else [
            (0, 0, 0), (0, 64, 0), (0, 255, 70)
        ]
        self.color_off = colors[0]
        self.color_trail = colors[1]
        self.color_head = colors[2]
        # Cache for O(1) background reset and fast LED lookup
        self._all_led_indices = [led_idx for (_, _, led_idx) in matrix.get_all_led_coords()]
        self._led_grid = [
            [matrix.get_led_index(r, c) for c in range(matrix.cols)]
            for r in range(matrix.rows)
        ]

    def _run_animation(self, on_complete=None):
        self.running = True
        rows, cols = self.matrix.rows, self.matrix.cols
        start_time = time.time()
        frame_dt = 1 / 15  # 15 fps for matrix rain feel

        max_active = max(1, int(cols * self.density))
        # Each drop: (col, head_row, trail_length, speed_rows_per_sec)
        drops = []

        def _new_drop():
            col = random.randint(0, cols - 1)
            trail = random.randint(3, max(4, rows // 2))
            speed = random.uniform(rows / 3, rows)
            return [col, -trail, trail, speed]

        for _ in range(max_active):
            d = _new_drop()
            d[1] = random.randint(-rows, 0)  # stagger starts
            drops.append(d)

        last_time = time.time()

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if not self.loop_infinite and elapsed_ms >= self.duration_ms:
                break

            now = time.time()
            dt = now - last_time
            last_time = now

            color_map = dict.fromkeys(self._all_led_indices, self.color_off)

            for drop in drops:
                col, head_r, trail_len, speed = drop
                drop[1] += speed * dt  # advance head

                head_r_int = int(drop[1])
                for i in range(trail_len + 1):
                    r = head_r_int - i
                    if 0 <= r < rows:
                        led_idx = self._led_grid[r][col]
                        if led_idx is not None:
                            if i == 0:
                                color_map[led_idx] = self.color_head
                            else:
                                t = 1.0 - i / trail_len
                                color_map[led_idx] = _lerp_color(self.color_off, self.color_trail, t)

                # Reset when fully off screen
                if head_r_int - trail_len >= self.matrix.rows:
                    new_drop = _new_drop()
                    drop[0] = new_drop[0]
                    drop[1] = -new_drop[2]
                    drop[2] = new_drop[2]
                    drop[3] = new_drop[3]

            self._apply_color_map(color_map, int((time.time() - start_time) * 1000))
            time.sleep(frame_dt)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# OceanWavesEffect2D - Superimposed sinusoids with 3-zone coloring
# =============================================================================

class OceanWavesEffect2D(Animated2DEffect):
    """
    Ocean waves — column-based rendering matching reference 07_pixel_matrix_effects.py.

    For each column a crest row is computed from 3 superimposed sinusoids with
    per-column random phase noise. The column is then filled vertically:
      row < crest_row  →  deep/shallow water gradient (deepest at row 0)
      row == crest_row →  foam (brightened crest)
      row > crest_row  →  sky (black)

    colors[0] = deep water (dark blue)
    colors[1] = shallow water near surface (lighter blue)
    colors[2] = wave crest / foam base (light blue/white)
    speed controls wave propagation rate.
    """

    # Wave parameters from reference (freq, amplitude, speed_multiplier, initial_phase)
    _WAVE_PARAMS = [
        (1.2, 0.35, 1.0, 0.0),
        (2.1, 0.15, 1.3, 1.0),
        (3.7, 0.08, 0.7, 2.5),
    ]
    _TOTAL_AMP = 0.35 + 0.15 + 0.08   # = 0.58

    def __init__(self, matrix, params):
        super().__init__(matrix, params.duration_ms)
        self.loop_infinite = params.loop_infinite
        self.speed = params.speed if params.speed is not None else 1.0
        colors = params.colors if len(params.colors) >= 3 else [
            (0, 15, 60), (0, 70, 150), (150, 210, 255)
        ]
        self.c_deep  = tuple(colors[0])
        self.c_mid   = tuple(colors[1])
        self.c_crest = tuple(colors[2])
        # Foam: blend crest toward white (distinct bright pixel exactly at the crest)
        self.c_foam  = _lerp_color(self.c_crest, (240, 250, 255), 0.5)
        # Per-column random phase offset: breaks horizontal symmetry
        cols = matrix.cols
        self._col_phase = [random.uniform(0, _TAU) for _ in range(cols)]
        # Precompute LED index grid for fast column-based access
        self._led_grid = [
            [matrix.get_led_index(r, c) for c in range(cols)]
            for r in range(matrix.rows)
        ]

    def _run_animation(self, on_complete=None):
        self.running   = True
        rows, cols     = self.matrix.rows, self.matrix.cols
        speed          = self.speed
        col_phase      = self._col_phase
        c_deep         = self.c_deep
        c_mid          = self.c_mid
        c_crest        = self.c_crest
        c_foam         = self.c_foam
        c_sky          = (0, 0, 0)
        led_grid       = self._led_grid
        wave_params    = self._WAVE_PARAMS
        total_amp      = self._TOTAL_AMP
        start_time     = time.time()
        frame_dt       = 1 / 30

        while self.running:
            if not self.loop_infinite and (time.time() - start_time) * 1000 >= self.duration_ms:
                break

            frame_start = time.time()
            t = (time.time() - start_time) * speed

            color_map = {}

            for c in range(cols):
                xn = c / max(cols - 1, 1)
                cp = col_phase[c]

                # Sum of 3 superimposed sinusoids (reference formula)
                wave_h = sum(
                    amp * math.sin(freq * xn * _TAU + t * spd * math.pi + ph + cp)
                    for freq, amp, spd, ph in wave_params
                )
                # Normalize to [0, 1]: 0 = crest near row 0 (top), 1 = crest near bottom
                normalized = (wave_h / total_amp + 1.0) / 2.0
                crest_row  = int(normalized * (rows - 1))

                for r in range(rows):
                    led_idx = led_grid[r][c]
                    if led_idx is None:
                        continue

                    if r > crest_row:
                        color = c_sky                              # sky below the wave
                    elif r == crest_row:
                        color = c_foam                             # foam at the crest
                    else:
                        # Water: deepest at row 0, shallowest just below crest
                        depth_t = 1.0 - (r / crest_row) if crest_row > 0 else 0.0
                        if r >= crest_row - 1:
                            color = _lerp_color(c_mid, c_crest, 0.5)   # just below foam
                        else:
                            color = _lerp_color(c_mid, c_deep, depth_t)

                    color_map[led_idx] = color

            self._apply_color_map(color_map, int((time.time() - start_time) * 1000))

            elapsed = time.time() - frame_start
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# PlasmaEffect2D - Weighted sum of 2D sinusoids with HSV palette mapping
# =============================================================================

class PlasmaEffect2D(Animated2DEffect):
    """
    Plasma: weighted sum of 4 sinusoid components (horizontal, vertical, circular, diagonal).
    Matches the algorithm from reference 07_pixel_matrix_effects.py:
    - Coordinates centered on [-1, 1] (not [0, 1] from corner) for large-scale patterns
    - Wave frequencies WITHOUT TAU multiplier → reference-quality organic waves
    - colors >= 2: palette interpolation mode (user-defined gradient)
    - colors 0..1: full HSV spectrum mode
    wave_weights = [h, v, circ, diag], normalized internally.
    """

    @staticmethod
    def _palette_lerp(colors: list, t: float) -> tuple:
        """Interpolate smoothly through a list of N colors at position t in [0, 1]."""
        n = len(colors) - 1
        if n <= 0:
            return tuple(colors[0]) if colors else (0, 0, 0)
        idx  = max(0.0, min(1.0, t)) * n
        i    = min(int(idx), n - 1)
        return _lerp_color(colors[i], colors[i + 1], idx - i)

    def __init__(self, matrix, params):
        super().__init__(matrix, params.duration_ms)
        self.loop_infinite = params.loop_infinite
        self.speed = params.speed if params.speed is not None else 1.0
        raw_w = params.wave_weights if params.wave_weights else [1.0, 1.0, 1.0, 1.0]
        norm = sum(raw_w) or 1.0
        self.wH = raw_w[0] / norm if len(raw_w) > 0 else 0.25
        self.wV = raw_w[1] / norm if len(raw_w) > 1 else 0.25
        self.wC = raw_w[2] / norm if len(raw_w) > 2 else 0.25
        self.wD = raw_w[3] / norm if len(raw_w) > 3 else 0.25
        # Palette mode when ≥ 2 colors; HSV full spectrum otherwise
        self._colors = [tuple(c) for c in params.colors] if len(params.colors) >= 2 else None
        # Precompute per-LED constants using CENTERED [-1, 1] coordinates (reference system).
        # NO TAU multiplier — large-scale organic plasma patterns like reference.

        # Try custom center from topology (world coordinates)
        custom_center = matrix.get_effect_center()
        if custom_center:
            # Convert world (X, Y) to matrix (col, row): X→col, Y→row
            cx = custom_center[0]
            cy = custom_center[1]
        else:
            # Fallback: geometric center
            cx = matrix.cols / 2.0
            cy = matrix.rows / 2.0

        hw = cx if cx > 0 else 1.0   # half-width
        hh = cy if cy > 0 else 1.0   # half-height
        self._plasma_coords = []
        for r, c, led_idx in matrix.get_all_led_coords():
            nx   = (c - cx) / hw                         # [-1, 1] horizontal
            ny   = (r - cy) / hh                         # [-1, 1] vertical
            dist = math.sqrt(nx * nx + ny * ny)          # [0, sqrt(2)]; reference uses raw dist
            diag = nx + ny                               # [-2, 2]; reference uses nx+ny
            self._plasma_coords.append((led_idx, nx, ny, dist, diag))

    def render_frame(self, time_ms: int):
        t      = time_ms / 1000.0 * self.speed
        colors = self._colors
        color_map = {}
        for led_idx, nx, ny, dist, diag in self._plasma_coords:
            # Reference formula — no TAU, frequencies 3/4/5/2.5, speeds 1.1/0.9/1.3/0.7
            v = (
                self.wH * math.sin(nx   * 3.0 + t * 1.1) +
                self.wV * math.sin(ny   * 4.0 + t * 0.9) +
                self.wC * math.sin(dist * 5.0 - t * 1.3) +
                self.wD * math.sin(diag * 2.5 + t * 0.7)
            )  # v in [-1.0, 1.0] because weights are normalized to sum=1
            v_norm = (v + 1.0) * 0.5   # [0, 1]
            if colors is not None:
                color_map[led_idx] = self._palette_lerp(colors, v_norm)
            else:
                color_map[led_idx] = _hsv_to_rgb(v_norm * 360.0, 1.0, 1.0)
        return color_map

    def _run_animation(self, on_complete=None):
        self.running = True
        start_time = time.time()
        frame_dt = 1 / 30

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if not self.loop_infinite and elapsed_ms >= self.duration_ms:
                break
            color_map = self.render_frame(int(elapsed_ms))
            self._apply_color_map(color_map, int((time.time() - start_time) * 1000))
            time.sleep(frame_dt)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# AuroraEffect2D - Vertical light bands with shimmer and additive blending
# =============================================================================

class AuroraEffect2D(Animated2DEffect):
    """
    Aurora borealis — curtain rendering matching reference 07_pixel_matrix_effects.py.

    Each color band has a top edge that undulates horizontally via two superimposed
    sinusoids. Light falls DOWNWARD from the top edge with a smooth (smoothstep)
    fade over fade_len rows — like real aurora curtains. Multiple bands use additive
    blending so overlapping colors mix naturally.

    Parameters: height (0-1), tail_length (0-1.5), wave_frequency, ripple (0-1), speed.
    Colors: each entry defines one aurora band (3 default).
    """

    @staticmethod
    def _ease(t: float) -> float:
        """Smoothstep ease-in-out: t^2 * (3 - 2t). Same as reference ease_in_out."""
        return t * t * (3.0 - 2.0 * t)

    def __init__(self, matrix, params):
        super().__init__(matrix, params.duration_ms)
        self.loop_infinite  = params.loop_infinite
        speed               = params.speed          if params.speed          is not None else 0.5
        height              = params.height         if params.height         is not None else 0.5
        tail_length         = params.tail_length    if params.tail_length    is not None else 1.5
        wave_frequency      = params.wave_frequency if params.wave_frequency is not None else 0.8
        self._ripple        = params.ripple         if params.ripple         is not None else 0.3
        self._tail_length   = tail_length
        self._wave_amplitude = 0.45  # Oscillation amplitude for full height coverage
        colors = params.colors if len(params.colors) >= 2 else [
            (0, 255, 80), (0, 180, 200), (80, 0, 255)
        ]
        n = len(colors)
        # Build per-band parameter dict matching reference formula exactly
        self._bands = [
            {
                'color':       tuple(colors[i]),
                'freq1':       wave_frequency + i * 0.3,          # primary wave frequency
                'freq2':       1.5 + i * 0.5,                     # secondary ripple frequency
                'speed1':      speed * (0.7 + i * 0.15),          # primary wave speed
                'speed2':      speed * (1.1 - i * 0.1),           # secondary ripple speed
                'phase_x':     i * math.pi * 0.7,                 # spatial phase offset
                'height_base': height + (i % 2) * 0.1,            # alternating height
            }
            for i in range(n)
        ]
        rows, cols = matrix.rows, matrix.cols
        self._rows = rows
        self._cols = cols
        # Precompute LED index grid for fast (row, col) access
        self._led_grid = [
            [matrix.get_led_index(r, c) for c in range(cols)]
            for r in range(rows)
        ]
        # Flat list of all valid LED indices (for accumulator initialisation)
        self._all_leds = []
        for r in range(rows):
            for c in range(cols):
                led_idx = matrix.get_led_index(r, c)
                if led_idx is not None:
                    self._all_leds.append(led_idx)

    def _run_animation(self, on_complete=None):
        self.running   = True
        rows, cols     = self._rows, self._cols
        bands          = self._bands
        ripple         = self._ripple
        tail_length    = self._tail_length
        wave_amplitude = self._wave_amplitude
        led_grid       = self._led_grid
        all_leds       = self._all_leds
        ease           = self._ease
        start_time     = time.time()
        frame_dt       = 1 / 30

        while self.running:
            if not self.loop_infinite and (time.time() - start_time) * 1000 >= self.duration_ms:
                break

            frame_start = time.time()
            t = time.time() - start_time

            # Accumulate additive RGB contributions from every band
            acc = {led_idx: [0.0, 0.0, 0.0] for led_idx in all_leds}

            for band in bands:
                color   = band['color']
                freq1   = band['freq1']
                freq2   = band['freq2']
                speed1  = band['speed1']
                speed2  = band['speed2']
                phase_x = band['phase_x']
                h_base  = band['height_base']
                c0, c1, c2 = color

                for c in range(cols):
                    xn = c / max(cols - 1, 1)

                    # Two superimposed sinusoids (reference formula)
                    wave1 = math.sin(xn * freq1 * _TAU + t * speed1 + phase_x)
                    wave2 = math.sin(xn * freq2 * _TAU - t * speed2) * ripple * 0.5
                    band_top = h_base + (wave1 + wave2) * wave_amplitude
                    band_top = max(0.05, min(0.95, band_top))

                    # Convert band_top (0=bottom,1=top) to pixel row (0=top of keyboard)
                    top_px   = int((1.0 - band_top) * (rows - 1))
                    # Fade length scales dynamically with band position (reference formula)
                    fade_len = max(1, int(band_top * rows * tail_length))

                    # Fill downward from top_px (curtain falls toward bottom)
                    for r in range(top_px, min(top_px + fade_len, rows)):
                        led_idx = led_grid[r][c]
                        if led_idx is None:
                            continue
                        dist_from_top = r - top_px
                        raw        = 1.0 - dist_from_top / fade_len
                        brightness = ease(raw)   # smoothstep
                        rgb = acc[led_idx]
                        rgb[0] += c0 * brightness
                        rgb[1] += c1 * brightness
                        rgb[2] += c2 * brightness

            # Project accumulator to color_map (clamp to 255)
            color_map = {}
            for led_idx in all_leds:
                rgb = acc[led_idx]
                color_map[led_idx] = (
                    min(255, int(rgb[0])),
                    min(255, int(rgb[1])),
                    min(255, int(rgb[2])),
                )
            self._apply_color_map(color_map, int((time.time() - start_time) * 1000))

            elapsed = time.time() - frame_start
            if elapsed < frame_dt:
                time.sleep(frame_dt - elapsed)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# ParallaxStarsEffect2D - Lateral parallax scroll with depth layers
# =============================================================================

class ParallaxStarsEffect2D(Animated2DEffect):
    """
    Parallax stars: 3 depth layers scrolling at different speeds.
    Deeper layers = slower speed, dimmer stars, more numerous.
    density multiplies star count per layer.
    Colors: [background, far_stars, mid_stars, near_stars] (use 1-4 colors).
    speed controls base scroll rate — near layer speed (px/s), default 9.0.
    direction controls scroll direction ('left', 'right').
    Near stars are drawn 2 pixels wide for visibility on low-res matrices.
    """

    def __init__(self, matrix, params):
        super().__init__(matrix, params.duration_ms)
        self.loop_infinite = params.loop_infinite
        # self.speed = near layer absolute speed (px/s); far/mid are fractions of it
        self.speed = params.speed if params.speed is not None else 9.0
        self.density = params.density if params.density is not None else 1.0
        self.direction = params.direction if params.direction in ('left', 'right') else 'left'
        colors = params.colors if params.colors else [(0, 0, 0)]
        self.bg_color = colors[0]
        star_colors = colors[1:] if len(colors) > 1 else [(255, 255, 255)]
        cols = matrix.cols
        # Layer definitions: (speed_mult, brightness_factor, base_count, pixel_size)
        # Speed multipliers yield near~9, mid~4, far~1.5 px/s at default speed=9.
        # Brightness and star counts match reference 07_pixel_matrix_effects.py.
        layer_defs = [
            (0.17, 0.27, max(8, cols // 3), 1),   # far:  slow, dim, many
            (0.44, 0.59, max(5, cols // 4), 1),   # mid:  medium
            (1.00, 0.94, max(3, cols // 6), 2),   # near: fast, bright, 2-px wide
        ]
        self.layers = []
        for i, (spd_m, bright_m, base_count, size) in enumerate(layer_defs):
            sc = star_colors[i % len(star_colors)]
            bright_color = tuple(int(ch * bright_m) for ch in sc)
            count = max(1, int(base_count * self.density))
            # Stars: [col_float, row_float] — mutable list for in-place update
            stars = [
                [random.uniform(0, cols), random.uniform(0, matrix.rows - 1)]
                for _ in range(count)
            ]
            self.layers.append({
                'stars': stars,
                'speed': spd_m,
                'color': bright_color,
                'size':  size,
            })
        # Cache LED indices for O(1) background reset and fast per-cell lookup
        self._all_led_indices = [led_idx for (_, _, led_idx) in matrix.get_all_led_coords()]
        self._led_grid = [
            [matrix.get_led_index(r, c) for c in range(matrix.cols)]
            for r in range(matrix.rows)
        ]

    def _run_animation(self, on_complete=None):
        self.running = True
        rows, cols = self.matrix.rows, self.matrix.cols
        start_time = time.time()
        frame_dt = 1 / 30
        last_time = time.time()

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if not self.loop_infinite and elapsed_ms >= self.duration_ms:
                break

            now = time.time()
            dt = now - last_time
            last_time = now

            # Background — O(n) uniform fill using precomputed indices
            color_map = dict.fromkeys(self._all_led_indices, self.bg_color)

            for layer in self.layers:
                layer_speed = self.speed * layer['speed']
                star_size   = layer['size']
                for star in layer['stars']:
                    # Scroll based on direction (left/right only)
                    if self.direction == 'right':
                        star[0] += layer_speed * dt
                        if star[0] > cols:
                            star[0] = -random.uniform(0, cols * 0.2)
                            star[1] = random.uniform(0, rows - 1)
                    else:  # default: left
                        star[0] -= layer_speed * dt
                        if star[0] < 0:
                            star[0] = cols + random.uniform(0, cols * 0.2)
                            star[1] = random.uniform(0, rows - 1)

                    c_int = int(star[0]) % cols
                    r_int = int(star[1]) % rows
                    led_idx = self._led_grid[r_int][c_int]
                    if led_idx is not None:
                        color_map[led_idx] = layer['color']
                    # Near stars: 2 pixels wide for visibility on low-res matrices
                    if star_size >= 2:
                        c2  = (c_int + 1) % cols
                        adj = self._led_grid[r_int][c2]
                        if adj is not None:
                            color_map[adj] = layer['color']

            self._apply_color_map(color_map, int((time.time() - start_time) * 1000))
            time.sleep(frame_dt)

        self.running = False
        if on_complete:
            on_complete()


# =============================================================================
# LightningEffect2D - Discrete lightning events with flash and bolt
# =============================================================================

class LightningEffect2D(Animated2DEffect):
    """
    Lightning: periodic lightning events matching reference 07_pixel_matrix_effects.py.
    Each event consists of:
    1. Bolt: random jagged path from top to bottom with lateral glow (40ms)
    2. Full-screen flash (60ms)
    3. Full-screen fade back to sky using smoothstep (6 steps x 40ms)
    Between strikes: occasional atmospheric flicker (5% chance per frame).
    bolt_interval_ms controls average time between strikes (default 2000ms,
    randomized ±50% as in reference).
    Colors: [sky_color, bolt_color, flash_color, flicker_color] (4 colors).
    """

    def __init__(self, matrix, params):
        super().__init__(matrix, params.duration_ms)
        self.loop_infinite = params.loop_infinite
        self.bolt_interval_ms = params.bolt_interval_ms if params.bolt_interval_ms is not None else 2000
        colors = params.colors if len(params.colors) >= 2 else [
            (5, 5, 20), (255, 255, 255)
        ]
        self.bg_color    = colors[0]
        self.bolt_color  = colors[1]
        self.flash_base  = colors[2] if len(colors) > 2 else (255, 255, 255)
        self.flicker_base = colors[3] if len(colors) > 3 else (20, 20, 60)
        # Precomputed caches — avoid get_all_led_coords()/get_led_index() every frame
        self._all_led_indices = [led_idx for (_, _, led_idx) in matrix.get_all_led_coords()]
        self._led_grid = [
            [matrix.get_led_index(r, c) for c in range(matrix.cols)]
            for r in range(matrix.rows)
        ]

    def _generate_bolt(self, rows, cols):
        """Generate random jagged bolt from row 0 to row rows-1."""
        bolt = []
        c = random.randint(cols // 4, 3 * cols // 4)
        for r in range(rows):
            bolt.append((r, c))
            c = max(0, min(cols - 1, c + random.randint(-1, 1)))
        return bolt

    @staticmethod
    def _ease(t: float) -> float:
        """Smoothstep ease-in-out: t^2*(3-2t). Used for fade-out."""
        return t * t * (3.0 - 2.0 * t)

    def _run_animation(self, on_complete=None):
        self.running = True
        rows, cols = self.matrix.rows, self.matrix.cols
        start_time = time.time()
        frame_dt = 1 / 30
        all_idx   = self._all_led_indices
        grid      = self._led_grid
        bg        = self.bg_color
        bolt_c    = self.bolt_color
        glow_c    = _lerp_color(bg, bolt_c, 0.3)
        flash_c   = _lerp_color(bolt_c, self.flash_base, 0.4)
        ease      = self._ease

        next_strike = 0.0

        while self.running:
            elapsed_ms = (time.time() - start_time) * 1000
            if not self.loop_infinite and elapsed_ms >= self.duration_ms:
                break

            if elapsed_ms >= next_strike:
                # --- Phase 1: Bolt path with lateral glow (reference order: bolt first) ---
                bolt = self._generate_bolt(rows, cols)
                bolt_map = dict.fromkeys(all_idx, bg)
                for r, c in bolt:
                    led_idx = grid[r][c]
                    if led_idx is not None:
                        bolt_map[led_idx] = bolt_c
                    for dc in (-1, 1):
                        nc = c + dc
                        if 0 <= nc < cols:
                            adj = grid[r][nc]
                            if adj is not None:
                                bolt_map[adj] = glow_c
                self._apply_color_map(bolt_map, int((time.time() - start_time) * 1000))
                time.sleep(0.04)

                # --- Phase 2: Full-screen flash (sky illuminated by strike) ---
                self._apply_color_map(dict.fromkeys(all_idx, flash_c), int((time.time() - start_time) * 1000))
                time.sleep(0.06)

                # --- Phase 3: Full-screen fade back to sky using smoothstep ---
                fade_steps = 6
                for step in range(fade_steps):
                    t = ease(1.0 - step / (fade_steps - 1))
                    fade_map = dict.fromkeys(all_idx, _lerp_color(bg, flash_c, t))
                    self._apply_color_map(fade_map, int((time.time() - start_time) * 1000))
                    time.sleep(0.04)

                # Schedule next strike — reference uses uniform(0.5, 1.8) of interval
                interval_s = self.bolt_interval_ms / 1000.0
                next_strike = elapsed_ms + interval_s * 1000 * random.uniform(0.5, 1.8)
            else:
                # Between strikes: dark sky with occasional atmospheric flicker (5%)
                if random.random() < 0.05:
                    flicker_c = _lerp_color(bg, self.flicker_base, random.uniform(0, 0.3))
                    self._apply_color_map(dict.fromkeys(all_idx, flicker_c), int((time.time() - start_time) * 1000))
                else:
                    self._apply_color_map(dict.fromkeys(all_idx, bg), int((time.time() - start_time) * 1000))
                time.sleep(frame_dt)

        self.running = False
        if on_complete:
            on_complete()


# ============================================================
# DIRECTIONAL FLASH EFFECT
# ============================================================

class DirectionalFlashEffect(Animated2DEffect):
    """
    Directional half-flash for impact feedback (e.g. UnderAttack_Right).

    The hit-side half of the keyboard lights up instantly at the start of
    each loop, then both zones fade to black over the remainder of the loop.

    Parameters
    ----------
    color_bg   : RGB tuple — color applied to the background half
    color_hit  : RGB tuple — color applied to the hit half
    direction  : "right" | "left" | "top" | "down" — which quarter is the hit side
    num_loops  : how many flash repetitions (default 1)
    duration_ms: total duration; each flash = duration_ms / num_loops
    """

    # Fraction of each loop held at full brightness before the fade begins
    _HOLD = 0.10

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 600,
                 color_bg:  Tuple[int, int, int] = (20, 0, 0),
                 color_hit: Tuple[int, int, int] = (255, 20, 0),
                 direction: str = 'right',
                 num_loops: int = 1):
        super().__init__(matrix, duration_ms)
        self.color_bg  = color_bg
        self.color_hit = color_hit
        self.direction = direction
        self.num_loops = max(1, num_loops)

    def _in_hit_half(self, row: int, col: int) -> bool:
        """Return True if (row, col) falls in the hit half (50% from center).

        Cardinal directions: half of keyboard split at midpoint along the hit axis.
        Diagonal directions: corner quadrant (half-row × half-col).
        """
        rows, cols = self.matrix.rows, self.matrix.cols
        d = self.direction
        half_r, half_c = rows * 0.5, cols * 0.5
        # Cardinals: half split at center
        if   d == 'right': return col >= half_c
        elif d == 'left':  return col <  half_c
        elif d == 'down':  return row >= half_r
        elif d == 'top':   return row <  half_r
        # Diagonals: corner quadrant
        elif d == 'tl':    return row <  half_r and col <  half_c
        elif d == 'tr':    return row <  half_r and col >= half_c
        elif d == 'bl':    return row >= half_r and col <  half_c
        elif d == 'br':    return row >= half_r and col >= half_c
        return False

    def render_frame(self, time_ms: float):
        loop_ms  = self.duration_ms / self.num_loops
        t_loop   = (time_ms % loop_ms) / loop_ms   # 0.0 → 1.0 within each loop

        # Hold at full brightness for _HOLD fraction, then linear fade to black
        if t_loop < self._HOLD:
            fade = 1.0
        else:
            fade = max(0.0, 1.0 - (t_loop - self._HOLD) / (1.0 - self._HOLD))

        r_bg,  g_bg,  b_bg  = self.color_bg
        r_hit, g_hit, b_hit = self.color_hit

        color_map = {}

        for row, col, led_idx in self.matrix.get_all_led_coords():
            if self._in_hit_half(row, col):
                r, g, b = r_hit, g_hit, b_hit
            else:
                r, g, b = r_bg, g_bg, b_bg
            color_map[led_idx] = (int(r * fade), int(g * fade), int(b * fade))

        self._apply_color_map(color_map, int(time_ms))


# ============================================================
# KEYBOARD PRESET EFFECT
# ============================================================

class KeyboardPresetEffect(Animated2DEffect):
    """
    Soft per-LED transition towards a saved keyboard preset.

    Each LED interpolates from its current hardware color to the target
    preset color over duration_ms milliseconds at 30 fps.
    LEDs not present in the preset fade to black (0, 0, 0).

    Args:
        matrix:        KeyboardMatrix2D controller for the target keyboard
        duration_ms:   Transition duration in ms (default 800)
        target_colors: {led_index_int: (r, g, b)} preset mapping
    """

    def __init__(self, matrix, duration_ms: int, target_colors: dict):
        super().__init__(matrix, max(duration_ms, 50))
        self.target_colors = target_colors
        self._start_colors: Optional[List[Tuple[int, int, int]]] = None  # Snapshot taken on first render

    def render_frame(self, time_ms: int):
        # KeyboardMatrix2D has no led_count attribute — derive from device.leds
        led_count = len(self.matrix.device.leds)

        # Snapshot current hardware colors on first frame
        if self._start_colors is None:
            try:
                hw = self.matrix.device.colors
                self._start_colors = [
                    (int(c.red), int(c.green), int(c.blue)) for c in hw
                ] if hw else [(0, 0, 0)] * led_count
            except Exception:
                self._start_colors = [(0, 0, 0)] * led_count

        t = min(time_ms / self.duration_ms, 1.0)

        color_map = {}
        sc = self._start_colors
        for i in range(led_count):
            src = sc[i] if sc is not None and i < len(sc) else (0, 0, 0)
            tgt = self.target_colors.get(i, (0, 0, 0))
            color_map[i] = (
                int(src[0] + (tgt[0] - src[0]) * t),
                int(src[1] + (tgt[1] - src[1]) * t),
                int(src[2] + (tgt[2] - src[2]) * t),
            )

        self._apply_color_map(color_map, int(time_ms))
