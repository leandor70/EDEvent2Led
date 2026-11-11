"""
4-Corner Gradient effect for 2D matrices.

Implements bi-linear interpolation between 4 corner colors.
Used for 4 Corner Nuance base effect (2D only).
"""

from typing import Tuple, List
from .spatial_effects_2d import Animated2DEffect
from .keyboard_matrix_2d import KeyboardMatrix2D


class CornerGradientEffect2D(Animated2DEffect):
    """
    4-corner gradient effect - bi-linear interpolation between 4 corner colors.

    Corner positions:
    - top_left (0, 0)
    - top_right (0, cols-1)
    - bottom_right (rows-1, cols-1)
    - bottom_left (rows-1, 0)

    Each LED color is interpolated based on its relative position within the matrix.
    """

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 1000,
                 color_tl: Tuple[int, int, int] = (255, 0, 0),
                 color_tr: Tuple[int, int, int] = (0, 255, 0),
                 color_br: Tuple[int, int, int] = (0, 0, 255),
                 color_bl: Tuple[int, int, int] = (255, 255, 0)):
        """
        Initialize 4-corner gradient effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Duration to transition from current state to gradient
            color_tl: Top-left corner color
            color_tr: Top-right corner color
            color_br: Bottom-right corner color
            color_bl: Bottom-left corner color
        """
        super().__init__(matrix, duration_ms)
        self.base_color = color_tl  # Base color for potential override
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

        Formula:
        c(x,y) = (1-x)(1-y)c00 + x(1-y)c10 + xy c11 + (1-x)y c01

        Args:
            c00, c10, c11, c01: Corner colors (RGB tuples)
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

    def _calculate_corner_gradient_color(self, row: int, col: int) -> Tuple[int, int, int]:
        """
        Calculate gradient color for a specific LED position using bi-linear interpolation.

        Args:
            row: Row index
            col: Column index

        Returns:
            RGB color tuple
        """
        rows = self.matrix.rows
        cols = self.matrix.cols

        # Normalize position to [0, 1]
        x = col / (cols - 1) if cols > 1 else 0.0  # Horizontal
        y = row / (rows - 1) if rows > 1 else 0.0  # Vertical

        # Use current_color if overridden (from keyframes) for top-left
        # This allows keyframe color injection while maintaining corner gradient pattern
        tl_color = self.current_color if self.current_color else self.color_tl

        # Bi-linear interpolation between 4 corners
        gradient_color = self._bilinear_interpolate(
            tl_color,        # Top-left (c00)
            self.color_tr,   # Top-right (c10)
            self.color_bl,   # Bottom-left (c01)
            self.color_br,   # Bottom-right (c11)
            x, y
        )

        return gradient_color

    def render_frame(self, time_ms: int):
        """Render 4-corner gradient frame (static, no built-in fade)."""
        # Build color map for all LEDs
        color_map = {}

        for row, col, led_idx in self.matrix.get_all_led_coords():
            # Calculate gradient color for this position
            color_map[led_idx] = self._calculate_corner_gradient_color(row, col)

        # Apply color map using standard mechanism (supports external fade_in_ms if set)
        self._apply_color_map(color_map, int(time_ms))
