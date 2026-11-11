"""
2D Matrix Effects for Keyboards with individually addressable LEDs.
Provides tools to create spatial effects on keyboard LED matrices.
"""
import math
from typing import List, Tuple, Optional, Callable
from utils.openrgb_client import RGBColor
from utils.openrgb_safe import safe_get_colors, safe_set_colors, DeviceSafetyError


class KeyboardMatrix2D:
    """
    Represents a keyboard LED matrix with 2D coordinate system.
    Enables spatial effects like waves, circles, lines, etc.
    """

    def __init__(self, matrix_map: List[List[Optional[int]]], device):
        """
        Initialize keyboard matrix.

        Args:
            matrix_map: 2D list where matrix_map[row][col] = LED index (or None if no LED)
            device: OpenRGB device object for the keyboard
        """
        self.matrix_map = matrix_map
        self.device = device
        self.rows = len(matrix_map)
        self.cols = len(matrix_map[0]) if matrix_map else 0
        # IO intercept: when set, apply_color_map calls this instead of device.set_colors.
        # Used by VisualEffectRenderer to batch and serialize hardware I/O.
        self._frame_intercept = None  # Optional[Callable[[List[RGBColor]], None]]

        # Build reverse mapping: LED index -> (row, col)
        self.led_to_coord = {}
        for row in range(self.rows):
            for col in range(self.cols):
                led_idx = matrix_map[row][col]
                if led_idx is not None:
                    self.led_to_coord[led_idx] = (row, col)

    def get_led_index(self, row: int, col: int) -> Optional[int]:
        """
        Get LED index at specific matrix position.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            LED index or None if no LED at that position
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.matrix_map[row][col]
        return None

    def get_led_coords(self, led_index: int) -> Optional[Tuple[int, int]]:
        """
        Get matrix coordinates for a specific LED.

        Args:
            led_index: LED index

        Returns:
            (row, col) tuple or None if LED not in matrix
        """
        return self.led_to_coord.get(led_index)

    def get_all_led_coords(self) -> List[Tuple[int, int, int]]:
        """
        Get all LED positions as (row, col, led_index) tuples.

        Returns:
            List of (row, col, led_index) for all LEDs
        """
        coords = []
        for row in range(self.rows):
            for col in range(self.cols):
                led_idx = self.matrix_map[row][col]
                if led_idx is not None:
                    coords.append((row, col, led_idx))
        return coords

    def get_led_world_position(self, led_index: int) -> Tuple[float, float]:
        """
        Get world coordinates for a specific LED.

        For keyboard matrices, world coordinates are derived from matrix position:
        - col → world_x (horizontal axis)
        - row → world_y (vertical axis)

        Args:
            led_index: LED index

        Returns:
            (world_x, world_y) - matrix position as floats, or (0.0, 0.0) if not found
        """
        coords = self.get_led_coords(led_index)
        if coords is None:
            return (0.0, 0.0)

        row, col = coords
        return (float(col), float(row))  # col→X, row→Y

    def get_effect_center(self) -> Optional[Tuple[float, float]]:
        """
        Get custom effect center from device topology, if configured.

        Returns:
            (world_x, world_y) tuple in matrix coordinates, or None if not configured

        Note: Implementation planned for future. Currently keyboards use geometric center.
        """
        # TODO: Implement when keyboard supports custom center in topology editor
        return None

    def distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """
        Calculate Euclidean distance between two positions.

        Args:
            pos1: (row, col) tuple
            pos2: (row, col) tuple

        Returns:
            Distance as float
        """
        r1, c1 = pos1
        r2, c2 = pos2
        return math.sqrt((r2 - r1) ** 2 + (c2 - c1) ** 2)

    def set_led_by_coords(self, row: int, col: int, color: Tuple[int, int, int]):
        """
        Set LED color by matrix coordinates.

        Args:
            row: Row index
            col: Column index
            color: RGB tuple (0-255)
        """
        led_idx = self.get_led_index(row, col)
        if led_idx is not None:
            colors = self.device.colors
            colors[led_idx] = RGBColor(*color)
            self.device.set_colors(colors)

    def set_all_leds(self, color: Tuple[int, int, int]):
        """
        Set all keyboard LEDs to the same color.

        Args:
            color: RGB tuple (0-255)
        """
        if self._frame_intercept is not None:
            # Route through the batcher so I/O is serialised with apply_color_map calls
            rgb = RGBColor(*color)
            colors = [rgb] * len(self.device.colors)
            self._frame_intercept(colors)
        else:
            self.device.set_color(RGBColor(*color))

    def apply_color_map(self, color_map: dict):
        """
        Apply a dictionary of LED colors.

        Args:
            color_map: Dict mapping LED index -> RGB color tuple
        """
        # Safely get current colors with fallback
        colors = safe_get_colors(self.device, operation="keyboard_matrix:apply_color_map")

        for led_idx, color in color_map.items():
            if 0 <= led_idx < len(colors):
                colors[led_idx] = RGBColor(*color)

        if self._frame_intercept is not None:
            # Renderer will handle validation via IOBatcher
            self._frame_intercept(colors)
        else:
            # Direct mode: validate before sending
            try:
                safe_set_colors(self.device, colors, fast=True, operation="keyboard_matrix:apply_color_map")
            except DeviceSafetyError as e:
                print(f"[ERROR] Keyboard matrix color validation failed: {e}")

    # ===== 2D EFFECT GENERATORS =====

    def generate_horizontal_line(self, row: int, color: Tuple[int, int, int]) -> dict:
        """
        Generate color map for a horizontal line.

        Args:
            row: Row to illuminate
            color: RGB color

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for col in range(self.cols):
            led_idx = self.get_led_index(row, col)
            if led_idx is not None:
                color_map[led_idx] = color
        return color_map

    def generate_vertical_line(self, col: int, color: Tuple[int, int, int]) -> dict:
        """
        Generate color map for a vertical line.

        Args:
            col: Column to illuminate
            color: RGB color

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for row in range(self.rows):
            led_idx = self.get_led_index(row, col)
            if led_idx is not None:
                color_map[led_idx] = color
        return color_map

    def generate_circle(self, center: Tuple[int, int], radius: float,
                       color: Tuple[int, int, int], thickness: float = 0.5) -> dict:
        """
        Generate color map for a circle.

        Args:
            center: (row, col) center position
            radius: Circle radius
            color: RGB color
            thickness: Line thickness (how far from exact radius to still light up)

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for row, col, led_idx in self.get_all_led_coords():
            dist = self.distance(center, (row, col))
            if abs(dist - radius) <= thickness:
                color_map[led_idx] = color
            else:
                # Set LEDs outside circle to black to avoid leaving previous colors
                color_map[led_idx] = (0, 0, 0)
        return color_map

    def generate_filled_circle(self, center: Tuple[int, int], radius: float,
                               color: Tuple[int, int, int]) -> dict:
        """
        Generate color map for a filled circle.

        Args:
            center: (row, col) center position
            radius: Circle radius
            color: RGB color

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for row, col, led_idx in self.get_all_led_coords():
            dist = self.distance(center, (row, col))
            if dist <= radius:
                color_map[led_idx] = color
            else:
                # Set LEDs outside circle to black to avoid leaving previous colors
                color_map[led_idx] = (0, 0, 0)
        return color_map

    def generate_ripple(self, center: Tuple[int, int], radius: float,
                       color: Tuple[int, int, int], falloff: float = 2.0) -> dict:
        """
        Generate color map for a ripple effect with gradient falloff.

        Args:
            center: (row, col) center position
            radius: Maximum radius
            color: RGB color at center
            falloff: How quickly brightness decreases with distance

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}

        # Guard against zero radius to prevent division by zero
        if radius <= 0:
            # If radius is zero or negative, just set center LED to full color
            for row, col, led_idx in self.get_all_led_coords():
                if (row, col) == center:
                    color_map[led_idx] = color
                else:
                    color_map[led_idx] = (0, 0, 0)
            return color_map

        for row, col, led_idx in self.get_all_led_coords():
            dist = self.distance(center, (row, col))
            if dist <= radius:
                # Calculate intensity based on distance (1.0 at center, 0.0 at radius)
                intensity = max(0.0, 1.0 - (dist / radius) ** falloff)
                dimmed_color = (
                    int(color[0] * intensity),
                    int(color[1] * intensity),
                    int(color[2] * intensity)
                )
                color_map[led_idx] = dimmed_color
            else:
                # Set LEDs outside radius to black to avoid leaving previous colors
                color_map[led_idx] = (0, 0, 0)
        return color_map

    def generate_wave(self, time: float, direction: str = 'horizontal',
                     color: Tuple[int, int, int] = (255, 128, 0),
                     wavelength: float = 4.0, speed: float = 1.0,
                     color_bg: Tuple[int, int, int] = (0, 0, 0)) -> dict:
        """
        Generate color map for a sine wave effect.

        Args:
            time: Current time in seconds
            direction: Wave direction - 'horizontal'/'right'/'left',
                       'vertical'/'down'/'top', or diagonal 'tl'/'br'/'tr'/'bl'
            color: Base RGB color
            wavelength: Wave period (distance between peaks)
            speed: Wave propagation speed

        Returns:
            Dict mapping LED index -> color
        """
        # Map 8-direction arrow values to (axis, reversed)
        # axis: 'col' = horizontal, 'row' = vertical,
        #       'diag_sum' = TL-BR diagonal, 'diag_diff' = TR-BL diagonal
        _DIR = {
            'horizontal': ('col',       False),
            'right':      ('col',       False),  # wave front moves right
            'left':       ('col',       True),   # wave front moves left
            'vertical':   ('row',       False),
            'down':       ('row',       False),  # wave front moves down
            'top':        ('row',       True),   # wave front moves up
            'tl':         ('diag_sum',  True),   # towards TL (BR -> TL)
            'br':         ('diag_sum',  False),  # towards BR (TL -> BR)
            'tr':         ('diag_diff', True),   # towards TR (BL -> TR)
            'bl':         ('diag_diff', False),  # towards BL (TR -> BL)
        }
        axis, reverse = _DIR.get(direction, ('col', False))
        max_diag = max(1, (self.rows - 1) + (self.cols - 1))

        color_map = {}
        for row, col, led_idx in self.get_all_led_coords():
            # Compute position along the chosen axis
            if axis == 'col':
                pos = (self.cols - 1 - col) if reverse else col
            elif axis == 'row':
                pos = (self.rows - 1 - row) if reverse else row
            elif axis == 'diag_sum':
                raw = row + col
                pos = (max_diag - raw) if reverse else raw
            else:  # diag_diff: TR -> BL
                raw = row + (self.cols - 1 - col)
                pos = (max_diag - raw) if reverse else raw

            # Calculate sine wave
            phase = (pos / wavelength - time * speed) * 2 * math.pi
            intensity = (math.sin(phase) + 1) / 2  # Range 0-1

            color_map[led_idx] = (
                int(color_bg[0] + (color[0] - color_bg[0]) * intensity),
                int(color_bg[1] + (color[1] - color_bg[1]) * intensity),
                int(color_bg[2] + (color[2] - color_bg[2]) * intensity),
            )

        return color_map

    def generate_diagonal_line(self, offset: float, color: Tuple[int, int, int],
                               thickness: float = 0.5, direction: int = 1) -> dict:
        """
        Generate color map for a diagonal line.

        Args:
            offset: Line position (-max to +max)
            color: RGB color
            thickness: Line thickness
            direction: 1 for top-left to bottom-right, -1 for top-right to bottom-left

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for row, col, led_idx in self.get_all_led_coords():
            # Calculate distance from diagonal line
            if direction == 1:
                dist = abs(col - row - offset)
            else:
                dist = abs(col + row - offset)

            if dist <= thickness:
                color_map[led_idx] = color
            else:
                # Set LEDs outside diagonal line to black to avoid leaving previous colors
                color_map[led_idx] = (0, 0, 0)

        return color_map

    def generate_gradient(self, direction: str = 'horizontal',
                         color1: Tuple[int, int, int] = (255, 0, 0),
                         color2: Tuple[int, int, int] = (0, 0, 255)) -> dict:
        """
        Generate color map for a gradient.

        Args:
            direction: 'horizontal', 'vertical', or 'radial'
            color1: Start RGB color
            color2: End RGB color

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}

        if direction == 'radial':
            center = (self.rows / 2, self.cols / 2)
            max_dist = self.distance((0, 0), (self.rows, self.cols))

            for row, col, led_idx in self.get_all_led_coords():
                dist = self.distance(center, (row, col))
                factor = min(1.0, dist / max_dist)

                color = (
                    int(color1[0] + (color2[0] - color1[0]) * factor),
                    int(color1[1] + (color2[1] - color1[1]) * factor),
                    int(color1[2] + (color2[2] - color1[2]) * factor)
                )
                color_map[led_idx] = color

        else:
            for row, col, led_idx in self.get_all_led_coords():
                if direction == 'horizontal':
                    factor = col / (self.cols - 1)
                else:  # vertical
                    factor = row / (self.rows - 1)

                color = (
                    int(color1[0] + (color2[0] - color1[0]) * factor),
                    int(color1[1] + (color2[1] - color1[1]) * factor),
                    int(color1[2] + (color2[2] - color1[2]) * factor)
                )
                color_map[led_idx] = color

        return color_map

    def generate_custom(self, generator_func: Callable[[int, int], Tuple[int, int, int]]) -> dict:
        """
        Generate color map using a custom function.

        Args:
            generator_func: Function that takes (row, col) and returns RGB color

        Returns:
            Dict mapping LED index -> color
        """
        color_map = {}
        for row, col, led_idx in self.get_all_led_coords():
            color = generator_func(row, col)
            color_map[led_idx] = color
        return color_map
