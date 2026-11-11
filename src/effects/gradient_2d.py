"""
Gradient effects for 2D matrices.

Implements spatial gradients between two colors with various directions.
Used for 2 Color Nuance base effect.
"""

from typing import Tuple
from .spatial_effects_2d import Animated2DEffect
from .keyboard_matrix_2d import KeyboardMatrix2D


class GradientEffect2D(Animated2DEffect):
    """
    2D gradient effect - spatial interpolation between two colors.

    Creates a smooth gradient from color1 to color2 across the keyboard matrix.
    Direction can be horizontal, vertical, or diagonal.
    """

    def __init__(self, matrix: KeyboardMatrix2D, duration_ms: int = 1000,
                 color1: Tuple[int, int, int] = (255, 0, 0),
                 color2: Tuple[int, int, int] = (0, 0, 255),
                 direction: str = "horizontal"):
        """
        Initialize gradient effect.

        Args:
            matrix: KeyboardMatrix2D instance
            duration_ms: Effect duration (static gradient, no fade)
            color1: Start color (can be overridden by set_color())
            color2: End color
            direction: Gradient direction - "horizontal", "vertical", "diagonal_tl_br", "diagonal_tr_bl"
        """
        super().__init__(matrix, duration_ms)
        self.base_color = color1  # Base color for potential override
        self.color1 = color1
        self.color2 = color2
        self.direction = direction

    def _calculate_gradient_color(self, row: int, col: int) -> Tuple[int, int, int]:
        """
        Calculate gradient color for a specific LED position.

        Args:
            row: Row index
            col: Column index

        Returns:
            RGB color tuple
        """
        rows = self.matrix.rows
        cols = self.matrix.cols

        # Normalize position to [0, 1]
        if self.direction in ("horizontal", "right"):
            # color1 on left → color2 on right
            factor = col / (cols - 1) if cols > 1 else 0.0

        elif self.direction == "left":
            # color1 on right → color2 on left
            factor = 1.0 - (col / (cols - 1)) if cols > 1 else 0.0

        elif self.direction in ("vertical", "down"):
            # color1 on top → color2 on bottom
            factor = row / (rows - 1) if rows > 1 else 0.0

        elif self.direction == "top":
            # color1 on bottom → color2 on top
            factor = 1.0 - (row / (rows - 1)) if rows > 1 else 0.0

        elif self.direction in ("tl", "diagonal_tl_br"):
            # color1 top-left → color2 bottom-right
            norm_row = row / (rows - 1) if rows > 1 else 0.0
            norm_col = col / (cols - 1) if cols > 1 else 0.0
            factor = (norm_row + norm_col) / 2.0

        elif self.direction in ("br",):
            # color1 bottom-right → color2 top-left
            norm_row = 1.0 - (row / (rows - 1)) if rows > 1 else 0.0
            norm_col = 1.0 - (col / (cols - 1)) if cols > 1 else 0.0
            factor = (norm_row + norm_col) / 2.0

        elif self.direction in ("tr", "diagonal_tr_bl"):
            # color1 top-right → color2 bottom-left
            norm_row = row / (rows - 1) if rows > 1 else 0.0
            norm_col = 1.0 - (col / (cols - 1)) if cols > 1 else 1.0
            factor = (norm_row + norm_col) / 2.0

        elif self.direction in ("bl",):
            # color1 bottom-left → color2 top-right
            norm_row = 1.0 - (row / (rows - 1)) if rows > 1 else 0.0
            norm_col = col / (cols - 1) if cols > 1 else 0.0
            factor = (norm_row + norm_col) / 2.0

        else:
            # Default to left→right
            factor = col / (cols - 1) if cols > 1 else 0.0

        # Linear interpolation between color1 and color2
        # Use current_color if overridden (from keyframes)
        start_color = self.current_color if self.current_color else self.color1

        gradient_color = (
            int(start_color[0] + (self.color2[0] - start_color[0]) * factor),
            int(start_color[1] + (self.color2[1] - start_color[1]) * factor),
            int(start_color[2] + (self.color2[2] - start_color[2]) * factor)
        )

        return gradient_color

    def render_frame(self, time_ms: int):
        """Render gradient frame (static, no built-in fade)."""
        # Build color map for all LEDs
        color_map = {}

        for row, col, led_idx in self.matrix.get_all_led_coords():
            # Calculate gradient color for this position
            color_map[led_idx] = self._calculate_gradient_color(row, col)

        # Apply color map using standard mechanism (supports external fade_in_ms if set)
        self._apply_color_map(color_map, int(time_ms))
