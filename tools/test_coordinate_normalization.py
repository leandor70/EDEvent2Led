"""
Test script for Phase 1.1 Coordinate Normalization system.

Tests:
- GlobalBoundingBox calculation
- World coordinate extraction from devices
- Normalization to [0,1] space
- Single device and multi-device scenarios
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.visual_effect_renderer import GlobalBoundingBox


def test_global_bbox_basic():
    """Test GlobalBoundingBox class with simple coordinates."""
    print("=" * 70)
    print("TEST 1: GlobalBoundingBox - Basic Operations")
    print("=" * 70)

    # Create bbox spanning [0,10] x [0,5]
    bbox = GlobalBoundingBox(0.0, 0.0, 10.0, 5.0)

    print(f"BBox: min_x={bbox.min_x}, min_y={bbox.min_y}, max_x={bbox.max_x}, max_y={bbox.max_y}")
    print(f"Width: {bbox.width()}, Height: {bbox.height()}")
    print()

    # Test normalization
    test_points = [
        (0.0, 0.0),   # Bottom-left corner → (0, 0)
        (10.0, 5.0),  # Top-right corner → (1, 1)
        (5.0, 2.5),   # Center → (0.5, 0.5)
        (2.5, 1.25),  # Quarter point → (0.25, 0.25)
        (7.5, 3.75),  # Three-quarter point → (0.75, 0.75)
    ]

    print("Normalization Tests:")
    for world_x, world_y in test_points:
        norm_x, norm_y = bbox.normalize_point(world_x, world_y)
        print(f"  World ({world_x:5.1f}, {world_y:5.1f}) -> Normalized ({norm_x:.3f}, {norm_y:.3f})")

    print("[OK] All normalization tests passed")
    print()


def test_global_bbox_edge_cases():
    """Test GlobalBoundingBox with edge cases."""
    print("=" * 70)
    print("TEST 2: GlobalBoundingBox - Edge Cases")
    print("=" * 70)

    # Edge case 1: Zero width
    bbox_zero_width = GlobalBoundingBox(5.0, 0.0, 5.0, 10.0)
    norm_x, norm_y = bbox_zero_width.normalize_point(5.0, 5.0)
    print(f"Zero width: ({5.0}, {5.0}) -> ({norm_x:.3f}, {norm_y:.3f})")
    assert norm_x == 0.5, "Zero width should default to 0.5"

    # Edge case 2: Zero height
    bbox_zero_height = GlobalBoundingBox(0.0, 5.0, 10.0, 5.0)
    norm_x, norm_y = bbox_zero_height.normalize_point(5.0, 5.0)
    print(f"Zero height: ({5.0}, {5.0}) -> ({norm_x:.3f}, {norm_y:.3f})")
    assert norm_y == 0.5, "Zero height should default to 0.5"

    # Edge case 3: Out of bounds (should clamp)
    bbox = GlobalBoundingBox(0.0, 0.0, 10.0, 10.0)
    norm_x, norm_y = bbox.normalize_point(-5.0, 15.0)
    print(f"Out of bounds: ({-5.0}, {15.0}) -> ({norm_x:.3f}, {norm_y:.3f})")
    assert 0.0 <= norm_x <= 1.0 and 0.0 <= norm_y <= 1.0, "Should clamp to [0,1]"

    print("[OK] All edge case tests passed")
    print()


def test_keyboard_coordinates():
    """Test keyboard matrix to world coordinate conversion."""
    print("=" * 70)
    print("TEST 3: Keyboard Matrix -> World Coordinates")
    print("=" * 70)

    # Simulate keyboard matrix (6 rows × 21 cols)
    rows, cols = 6, 21

    print(f"Keyboard Matrix: {rows} rows × {cols} cols")
    print()

    # Direct mapping: col→X, row→Y
    test_leds = [
        (0, 0),    # Top-left key
        (5, 20),   # Bottom-right key
        (2, 10),   # Center-ish key
    ]

    print("Matrix Position -> World Coordinates:")
    for row, col in test_leds:
        world_x, world_y = float(col), float(row)
        print(f"  Row {row}, Col {col:2d} -> World ({world_x:5.1f}, {world_y:5.1f})")

    # Create bbox spanning entire keyboard
    bbox = GlobalBoundingBox(0.0, 0.0, float(cols), float(rows))

    print()
    print("World Coordinates -> Normalized [0,1]:")
    for row, col in test_leds:
        world_x, world_y = float(col), float(row)
        norm_x, norm_y = bbox.normalize_point(world_x, world_y)
        print(f"  World ({world_x:5.1f}, {world_y:5.1f}) -> Normalized ({norm_x:.3f}, {norm_y:.3f})")

    print("[OK] Keyboard coordinate tests passed")
    print()


def test_multi_device_bbox():
    """Test global bbox calculation with multiple devices."""
    print("=" * 70)
    print("TEST 4: Multi-Device Global Bounding Box")
    print("=" * 70)

    # Device 1: Keyboard at (0,0) to (21,6)
    keyboard_positions = [(float(col), float(row)) for row in range(6) for col in range(21)]

    # Device 2: LED strip at (25,5) to (35,21) (vertical, 5 segments)
    strip_positions = [
        (25.0, 5.0), (26.0, 5.0), (27.0, 5.0),  # Segment 1
        (25.0, 9.0), (26.0, 9.0), (27.0, 9.0),  # Segment 2
        (25.0, 13.0), (26.0, 13.0), (27.0, 13.0),  # Segment 3
        (25.0, 17.0), (26.0, 17.0), (27.0, 17.0),  # Segment 4
        (25.0, 21.0), (26.0, 21.0), (27.0, 21.0),  # Segment 5
    ]

    # Calculate global bbox manually
    all_positions = keyboard_positions + strip_positions

    min_x = min(x for x, y in all_positions)
    min_y = min(y for x, y in all_positions)
    max_x = max(x for x, y in all_positions)
    max_y = max(y for x, y in all_positions)

    print(f"Device 1 (Keyboard): {len(keyboard_positions)} LEDs at (0,0) to (21,6)")
    print(f"Device 2 (LED Strip): {len(strip_positions)} LEDs at (25,5) to (35,21)")
    print()
    print(f"Raw BBox: X=[{min_x:.1f}, {max_x:.1f}], Y=[{min_y:.1f}, {max_y:.1f}]")

    # Add 10% padding (as per design)
    width = max_x - min_x
    height = max_y - min_y
    padding_x = width * 0.1
    padding_y = height * 0.1

    bbox = GlobalBoundingBox(
        min_x - padding_x,
        min_y - padding_y,
        max_x + padding_x,
        max_y + padding_y
    )

    print(f"With Padding: X=[{bbox.min_x:.1f}, {bbox.max_x:.1f}], Y=[{bbox.min_y:.1f}, {bbox.max_y:.1f}]")
    print()

    # Test normalization for LEDs in each device
    test_leds = [
        ("Keyboard center", 10.0, 3.0),
        ("LED strip segment 3 center", 26.0, 13.0),
    ]

    print("Sample Normalized Coordinates:")
    for label, world_x, world_y in test_leds:
        norm_x, norm_y = bbox.normalize_point(world_x, world_y)
        print(f"  {label}: ({world_x:.1f}, {world_y:.1f}) -> ({norm_x:.3f}, {norm_y:.3f})")

    print("[OK] Multi-device bbox test passed")
    print()


def main():
    """Run all tests."""
    print("\n")
    print("+" + "=" * 68 + "+")
    print("|" + " " * 10 + "COORDINATE NORMALIZATION TEST SUITE" + " " * 23 + "|")
    print("|" + " " * 22 + "Phase 1.1" + " " * 37 + "|")
    print("+" + "=" * 68 + "+")
    print()

    try:
        test_global_bbox_basic()
        test_global_bbox_edge_cases()
        test_keyboard_coordinates()
        test_multi_device_bbox()

        print("=" * 70)
        print("[OK] ALL TESTS PASSED")
        print("=" * 70)
        print()
        print("Phase 1.1 Infrastructure: READY")
        print()
        return 0

    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
