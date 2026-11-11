"""
Color utility functions for HSV/RGB conversion and color interpolation.

Centralizes color manipulation functions used across the effects modules.
"""

from typing import Tuple, List


def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    Convert HSV to RGB color.

    Args:
        h: Hue in degrees (0-360)
        s: Saturation (0-1)
        v: Value/Brightness (0-1)

    Returns:
        RGB tuple (0-255, 0-255, 0-255)
    """
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def hsv_to_rgb_normalized(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    Convert HSV to RGB with hue in 0-1 range (alternative input format).

    Args:
        h: Hue normalized (0-1)
        s: Saturation (0-1)
        v: Value/Brightness (0-1)

    Returns:
        RGB tuple (0-255, 0-255, 0-255)
    """
    if s == 0.0:
        val = int(v * 255)
        return (val, val, val)

    h = h * 6.0
    i = int(h)
    f = h - i

    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    i = i % 6

    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q

    return (int(r * 255), int(g * 255), int(b * 255))


def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    Convert RGB to HSV color.

    Args:
        r: Red (0-255)
        g: Green (0-255)
        b: Blue (0-255)

    Returns:
        HSV tuple (h: 0-360, s: 0-1, v: 0-1)
    """
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    delta = max_val - min_val

    if delta == 0:
        h = 0.0
    elif max_val == r:
        h = 60.0 * (((g - b) / delta) % 6)
    elif max_val == g:
        h = 60.0 * (((b - r) / delta) + 2)
    else:
        h = 60.0 * (((r - g) / delta) + 4)

    s = 0.0 if max_val == 0 else delta / max_val
    v = max_val

    return (h, s, v)


def lerp_color(
    color1: Tuple[int, int, int], color2: Tuple[int, int, int], t: float
) -> Tuple[int, int, int]:
    """
    Linear interpolation between two colors.

    Args:
        color1: Start RGB color
        color2: End RGB color
        t: Interpolation factor (0.0 = color1, 1.0 = color2)

    Returns:
        Interpolated RGB color
    """
    t = max(0.0, min(1.0, t))
    return (
        int(color1[0] + (color2[0] - color1[0]) * t),
        int(color1[1] + (color2[1] - color1[1]) * t),
        int(color1[2] + (color2[2] - color1[2]) * t),
    )


def lerp_color_list(
    colors: List[Tuple[int, int, int]], t: float
) -> Tuple[int, int, int]:
    """
    Interpolate between multiple colors evenly spaced.

    Args:
        colors: List of RGB colors
        t: Position (0.0 = first color, 1.0 = last color)

    Returns:
        Interpolated RGB color
    """
    if not colors:
        return (0, 0, 0)
    if len(colors) == 1:
        return colors[0]

    t = max(0.0, min(1.0, t))
    segment_count = len(colors) - 1
    segment = int(t * segment_count)
    segment = min(segment, segment_count - 1)

    local_t = (t * segment_count) - segment
    return lerp_color(colors[segment], colors[segment + 1], local_t)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex color string."""
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
