"""
Debug script to show gradient calculation for 17-LED strip.

Test case: color1=white (255,255,255), color2=blue (0,0,255), direction=left
Expected: blue on left → white on right
"""

def calculate_gradient_factor(col: int, direction: str, led_count: int) -> float:
    """Same logic as GradientShiftEffect1D._calculate_gradient_factor()"""
    row = 0
    rows = 1
    cols = led_count

    if direction in ("horizontal", "right"):
        # color1 on left → color2 on right
        factor = col / (cols - 1) if cols > 1 else 0.0

    elif direction == "left":
        # color1 on right → color2 on left
        factor = 1.0 - (col / (cols - 1)) if cols > 1 else 0.0

    elif direction in ("vertical", "down"):
        # color1 on top → color2 on bottom
        factor = row / (rows - 1) if rows > 1 else 0.0

    elif direction == "top":
        # color1 on bottom → color2 on top
        factor = 1.0 - (row / (rows - 1)) if rows > 1 else 0.0

    elif direction in ("tl", "diagonal_tl_br"):
        # color1 top-left → color2 bottom-right
        norm_row = row / (rows - 1) if rows > 1 else 0.0
        norm_col = col / (cols - 1) if cols > 1 else 0.0
        factor = (norm_row + norm_col) / 2.0

    elif direction in ("br",):
        # color1 bottom-right → color2 top-left
        norm_row = 1.0 - (row / (rows - 1)) if rows > 1 else 0.0
        norm_col = 1.0 - (col / (cols - 1)) if cols > 1 else 0.0
        factor = (norm_row + norm_col) / 2.0

    elif direction in ("tr", "diagonal_tr_bl"):
        # color1 top-right → color2 bottom-left
        norm_row = row / (rows - 1) if rows > 1 else 0.0
        norm_col = 1.0 - (col / (cols - 1)) if cols > 1 else 1.0
        factor = (norm_row + norm_col) / 2.0

    elif direction in ("bl",):
        # color1 bottom-left → color2 top-right
        norm_row = 1.0 - (row / (rows - 1)) if rows > 1 else 0.0
        norm_col = col / (cols - 1) if cols > 1 else 0.0
        factor = (norm_row + norm_col) / 2.0

    else:
        # Default to left→right
        factor = col / (cols - 1) if cols > 1 else 0.0

    return factor


def interpolate_color(color1, color2, factor):
    """Interpolate between color1 and color2 using factor (0.0 to 1.0)"""
    return (
        int(color1[0] + (color2[0] - color1[0]) * factor),
        int(color1[1] + (color2[1] - color1[1]) * factor),
        int(color1[2] + (color2[2] - color1[2]) * factor),
    )


def main():
    # Test case parameters
    color1 = (255, 255, 255)  # WHITE
    color2 = (0, 0, 255)      # BLUE
    direction = "left"
    led_count = 17

    print("=" * 80)
    print("GRADIENT 1D DEBUG - 17-LED Strip")
    print("=" * 80)
    print(f"Color1 (bianco): RGB{color1}")
    print(f"Color2 (blu):    RGB{color2}")
    print(f"Direction: {direction}")
    print(f"LED Count: {led_count}")
    print("-" * 80)
    print(f"{'LED':<6} {'Factor':<10} {'RGB Color':<20} {'Visual':<30}")
    print("-" * 80)

    for i in range(led_count):
        factor = calculate_gradient_factor(i, direction, led_count)
        color = interpolate_color(color1, color2, factor)

        # Visual representation (intensity bar)
        blue_intensity = int((factor) * 20)
        white_intensity = int((1.0 - factor) * 20)
        visual = "B" * blue_intensity + "W" * white_intensity

        # Color description
        if factor >= 0.95:
            desc = "PURE BLUE"
        elif factor <= 0.05:
            desc = "PURE WHITE"
        else:
            desc = "mixed"

        print(f"LED {i:2d}  {factor:.4f}     RGB{color}       {visual:<25} {desc}")

    print("-" * 80)
    print()
    print("Legend:")
    print("  Factor 1.0 = 100% color2 (BLUE)")
    print("  Factor 0.0 = 100% color1 (WHITE)")
    print("  Expected: LED 0 (left) = BLUE, LED 16 (right) = WHITE")
    print("=" * 80)


if __name__ == "__main__":
    main()
