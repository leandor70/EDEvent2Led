"""
Pulse, Fade and Breath effects for 2D matrices.

Simple uniform color effects with brightness variation or color interpolation over time.
Used for Static Transition and Breath base effects.
"""

import math
from typing import Tuple, Optional
from .spatial_effects_2d import Animated2DEffect
from .keyboard_matrix_2d import KeyboardMatrix2D


class PulseEffect2D(Animated2DEffect):
    """
    Uniform pulse effect - all LEDs same color with varying brightness.

    Can be used for:
    - Static Transition: Fade from current to target color
    - Breath: Oscillate brightness between min and max
    """

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 2000,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 min_brightness: float = 0.2):
        """
        Initialize pulse effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total duration
            color: Base RGB color (can be overridden by set_color())
            min_brightness: Minimum brightness (0.0 = off, 1.0 = full)
        """
        super().__init__(matrix, duration_ms)
        self.base_color = color
        self.min_brightness = min_brightness

    def render_frame(self, time_ms: int):
        """Render pulse frame."""
        # Use current_color if set (from keyframe), otherwise use base_color
        active_color = self.current_color if self.current_color else self.base_color

        # Calculate brightness using sine wave
        progress = time_ms / self.duration_ms
        brightness_range = 1.0 - self.min_brightness
        brightness = self.min_brightness + brightness_range * (0.5 + 0.5 * math.sin(progress * math.pi * 2))

        # Apply brightness to color
        pulsed_color = (
            int(active_color[0] * brightness),
            int(active_color[1] * brightness),
            int(active_color[2] * brightness)
        )

        # Build color_map with all LEDs set to the same color
        color_map = {}
        for row, col, led_idx in self.matrix.get_all_led_coords():
            color_map[led_idx] = pulsed_color

        # Use _apply_color_map to enable fade-in support
        self._apply_color_map(color_map, int(time_ms))


class BreathEffect2D(Animated2DEffect):
    """
    Two-color breath effect for keyboards.

    Oscillates smoothly between color1 and color2 exactly loop_count times
    within duration_ms. Cosine envelope ensures smooth transitions.

    Example: duration=5000ms, loop_count=5 -> 5 oscillations of 1000ms each (total 5000ms).
    """

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 2000,
                 color1: Tuple[int, int, int] = (255, 255, 255),
                 color2: Tuple[int, int, int] = (0, 0, 0),
                 loop_count: int = 1):
        """
        Initialize breath effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: TOTAL duration of the effect (all oscillations combined)
            color1: Starting/ending color
            color2: Peak color (midpoint of each cycle)
            loop_count: Number of complete oscillations; each cycle = duration_ms / loop_count
        """
        loop_count = max(1, loop_count)
        self.cycle_ms = max(1, duration_ms // loop_count)
        super().__init__(matrix, duration_ms)
        self.color1 = tuple(int(v) for v in color1)
        self.color2 = tuple(int(v) for v in color2)
        self.loop_count = loop_count

    def render_frame(self, time_ms: int):
        """Render breath frame."""
        # Use current_color as color1 override (legacy FusedEffect keyframe system)
        c1 = self.current_color if self.current_color else self.color1
        c2 = self.color2

        # Phase within the current cycle (0..1), independent of loop_count
        cycle_progress = (time_ms % self.cycle_ms) / self.cycle_ms
        # Cosine envelope: 0 at start/end of each cycle, 1 at midpoint
        alpha = (1.0 - math.cos(cycle_progress * math.pi * 2)) / 2.0

        color = (
            int(c1[0] + (c2[0] - c1[0]) * alpha),
            int(c1[1] + (c2[1] - c1[1]) * alpha),
            int(c1[2] + (c2[2] - c1[2]) * alpha),
        )

        # Build color_map with all LEDs set to the same color
        color_map = {}
        for row, col, led_idx in self.matrix.get_all_led_coords():
            color_map[led_idx] = color

        # Use _apply_color_map to enable fade-in support
        self._apply_color_map(color_map, int(time_ms))


class FadeEffect2D(Animated2DEffect):
    """
    Per-LED fade: each LED transitions independently from its actual current
    color to the target color.

    Used for Static Transition base effect.  start_colors are captured from
    matrix.device.colors at construction time — the caller must ensure
    device.colors reflects the real hardware state before constructing.
    """

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 1000,
                 end_color: Tuple[int, int, int] = (255, 255, 255)):
        """
        Initialize fade effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Total duration
            end_color: Target RGB color (can be overridden by set_color())
        """
        super().__init__(matrix, duration_ms)
        # Capture per-LED start colors from actual device state
        try:
            self.start_colors = [
                (c.red, c.green, c.blue) for c in matrix.device.colors
            ]
        except Exception:
            self.start_colors = [(0, 0, 0)]
        self.base_color = end_color

        # DEBUG: log the space key (LED 34) color at effect start
        SPACE_LED = 34
        if len(self.start_colors) > SPACE_LED:
            sc = self.start_colors[SPACE_LED]
            print(f"[FadeEffect2D] Start colors read: {len(self.start_colors)} LEDs "
                  f"| Space (LED {SPACE_LED}): RGB{sc} "
                  f"| LED 0: RGB{self.start_colors[0]} "
                  f"| LED 104: RGB{self.start_colors[min(104, len(self.start_colors)-1)]} "
                  f"| target: RGB{end_color}")

    def render_frame(self, time_ms: int):
        """Render fade frame with per-LED color interpolation."""
        target = self.current_color if self.current_color else self.base_color
        progress = min(time_ms / self.duration_ms, 1.0)

        color_map = {
            i: (
                int(sc[0] + (target[0] - sc[0]) * progress),
                int(sc[1] + (target[1] - sc[1]) * progress),
                int(sc[2] + (target[2] - sc[2]) * progress),
            )
            for i, sc in enumerate(self.start_colors)
        }
        self.matrix.apply_color_map(color_map)
