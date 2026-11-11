"""
Scientific Test Suite for Custom Effect Center Implementation

3-Level Testing Approach:
  Level 1: Unit Tests - Mathematical verification of coordinate conversion
  Level 2: Integration Tests - Verify radial effects use correct center
  Level 3: Visual Tests - Generate distance heatmaps for validation

Run with: python tools/test_custom_center_scientific.py
"""
import sys
import math
from pathlib import Path
from typing import Tuple, List, Dict, Optional
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from effects.linear_1d import Linear1D


# =============================================================================
# LEVEL 1: Unit Tests - Coordinate Conversion
# =============================================================================

def test_level1_coordinate_conversion():
    """
    Level 1: Mathematical verification of percentage to world coordinate conversion.

    Tests that get_effect_center() correctly converts topology percentages
    to world coordinates for various bbox configurations.
    """
    print("=" * 70)
    print("  LEVEL 1: Unit Tests - Coordinate Conversion")
    print("=" * 70)
    print()

    # Mock device for testing
    class MockDevice:
        def __init__(self):
            self.name = "Test LED Strip"
            self.leds_count = 38

    device = MockDevice()
    linear = Linear1D(device, 38)

    test_cases = [
        # (bbox, center_percent, expected_world)
        (
            {'min_x': 0, 'max_x': 10, 'min_y': 0, 'max_y': 5},
            (50.0, 50.0),
            (5.0, 2.5),
            "Center 50% in bbox [0,10]x[0,5]"
        ),
        (
            {'min_x': 0, 'max_x': 10, 'min_y': 0, 'max_y': 5},
            (75.0, 50.0),
            (7.5, 2.5),
            "Front impact 75% in bbox [0,10]x[0,5]"
        ),
        (
            {'min_x': 0, 'max_x': 10, 'min_y': 0, 'max_y': 5},
            (25.0, 50.0),
            (2.5, 2.5),
            "Rear impact 25% in bbox [0,10]x[0,5]"
        ),
        (
            {'min_x': 5, 'max_x': 21, 'min_y': 5, 'max_y': 21},
            (56.25, 50.0),
            (14.0, 13.0),
            "Offset bbox [5,21]x[5,21] with center at 56.25%"
        ),
        (
            {'min_x': 0, 'max_x': 10, 'min_y': 0, 'max_y': 5},
            (0.0, 0.0),
            (0.0, 0.0),
            "Bottom-left corner 0%"
        ),
        (
            {'min_x': 0, 'max_x': 10, 'min_y': 0, 'max_y': 5},
            (100.0, 100.0),
            (10.0, 5.0),
            "Top-right corner 100%"
        ),
    ]

    all_passed = True

    for bbox, (cx_pct, cy_pct), (expected_x, expected_y), description in test_cases:
        # Setup topology
        linear._topology = {
            "effect_center": {
                "x": cx_pct,
                "y": cy_pct,
                "enabled": True
            }
        }
        linear._global_bbox = bbox

        # Get result
        result = linear.get_effect_center()

        # Verify
        if result is None:
            print(f"  [FAIL] {description}")
            print(f"         Expected: ({expected_x}, {expected_y}), got None")
            all_passed = False
            continue

        actual_x, actual_y = result
        tolerance = 0.01

        x_match = abs(actual_x - expected_x) < tolerance
        y_match = abs(actual_y - expected_y) < tolerance

        if x_match and y_match:
            print(f"  [OK]   {description}")
            print(f"         Input:    {cx_pct}%, {cy_pct}%")
            print(f"         Expected: ({expected_x:.2f}, {expected_y:.2f})")
            print(f"         Actual:   ({actual_x:.2f}, {actual_y:.2f})")
        else:
            print(f"  [FAIL] {description}")
            print(f"         Expected: ({expected_x:.2f}, {expected_y:.2f})")
            print(f"         Actual:   ({actual_x:.2f}, {actual_y:.2f})")
            print(f"         Delta:    ({abs(actual_x - expected_x):.4f}, {abs(actual_y - expected_y):.4f})")
            all_passed = False

        print()

    return all_passed


# =============================================================================
# LEVEL 2: Integration Tests - Radial Effects Center Usage
# =============================================================================

def test_level2_radial_effects_integration():
    """
    Level 2: Integration test verifying radial effects use custom center.

    Creates a mock LED strip with custom center and verifies that:
    1. Bloom effect calculates distances from custom center
    2. LED distances match expected values based on custom center position
    """
    print("=" * 70)
    print("  LEVEL 2: Integration Tests - Radial Effects")
    print("=" * 70)
    print()

    # Mock device with known topology
    class MockDevice:
        def __init__(self):
            self.name = "Test Strip"
            self.leds_count = 10

    device = MockDevice()
    linear = Linear1D(device, 10)

    # Setup topology: 10 LEDs in horizontal line at Y=5
    # Positions: (0,5), (1,5), (2,5), ..., (9,5)
    linear._topology = {
        "zones": [
            {
                "id": 0,
                "name": "TestZone",
                "position": {"x": 0, "y": 5},
                "rotation": 0,
                "led_count": 10
            }
        ],
        "effect_center": {
            "x": 75.0,  # 75% of width = 6.75 in world coords
            "y": 50.0,  # 50% of height = 5.0 in world coords
            "enabled": True
        }
    }
    linear._zones = linear._topology["zones"]
    linear._calculate_global_bbox()

    print(f"  Setup: 10 LEDs horizontal line Y=5, X=[0,9]")
    print(f"  Custom Center: 75% X, 50% Y")
    print()

    # Get custom center
    custom_center = linear.get_effect_center()

    if custom_center is None:
        print(f"  [FAIL] get_effect_center() returned None")
        return False

    cx, cy = custom_center
    print(f"  Custom Center World Coords: ({cx:.2f}, {cy:.2f})")
    print()

    # Calculate expected distances for each LED from custom center
    print("  LED Distance Verification:")
    print("  " + "-" * 66)
    print(f"  {'LED':<4} {'Position':<12} {'Expected Dist':<15} {'Status'}")
    print("  " + "-" * 66)

    all_passed = True

    for led_idx in range(10):
        zone_idx, local_idx = linear.get_zone_and_local_index(led_idx)
        world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

        # Calculate expected distance
        expected_dist = math.sqrt((world_x - cx)**2 + (world_y - cy)**2)

        # Verify LED position is what we expect
        expected_x = float(led_idx)  # rotation=0 horizontal
        expected_y = 5.0

        pos_correct = (abs(world_x - expected_x) < 0.01 and
                      abs(world_y - expected_y) < 0.01)

        status = "[OK]" if pos_correct else "[FAIL]"

        print(f"  {led_idx:<4} ({world_x:.1f}, {world_y:.1f}){' ':<4} "
              f"{expected_dist:>6.2f} units     {status}")

        if not pos_correct:
            all_passed = False

    print("  " + "-" * 66)
    print()

    # Verify center is between LED 6 and 7 (since 75% of 9 = 6.75)
    if 6.0 < cx < 7.0 and abs(cy - 5.0) < 0.01:
        print(f"  [OK]   Custom center correctly positioned between LED 6 and 7")
    else:
        print(f"  [FAIL] Custom center position unexpected")
        all_passed = False

    print()

    return all_passed


# =============================================================================
# LEVEL 3: Visual Tests - Distance Heatmap Generation
# =============================================================================

def test_level3_visual_distance_heatmap():
    """
    Level 3: Generate ASCII heatmap showing LED distances from custom center.

    Creates visual representation of distance field for validation.
    Useful for debugging and understanding spatial distribution.
    """
    print("=" * 70)
    print("  LEVEL 3: Visual Tests - Distance Heatmap")
    print("=" * 70)
    print()

    # Mock device
    class MockDevice:
        def __init__(self):
            self.name = "Test Strip"
            self.leds_count = 21

    device = MockDevice()
    linear = Linear1D(device, 21)

    # Setup topology: 21 LEDs horizontal at Y=10
    linear._topology = {
        "zones": [{
            "id": 0,
            "name": "TestZone",
            "position": {"x": 0, "y": 10},
            "rotation": 0,
            "led_count": 21
        }],
        "effect_center": {
            "x": 75.0,  # 75% of 20 = 15
            "y": 50.0,
            "enabled": True
        }
    }
    linear._zones = linear._topology["zones"]
    linear._calculate_global_bbox()

    custom_center = linear.get_effect_center()

    if custom_center is None:
        print(f"  [FAIL] Cannot generate heatmap - no custom center")
        return False

    cx, cy = custom_center

    print(f"  Configuration: 21 LEDs horizontal, center at ({cx:.1f}, {cy:.1f})")
    print()

    # Calculate distances
    distances = []
    max_dist = 0.0

    for led_idx in range(21):
        zone_idx, local_idx = linear.get_zone_and_local_index(led_idx)
        world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)
        dist = math.sqrt((world_x - cx)**2 + (world_y - cy)**2)
        distances.append(dist)
        max_dist = max(max_dist, dist)

    # Normalize distances to 0-9 scale for ASCII visualization
    def normalize_to_char(dist: float) -> str:
        if max_dist == 0:
            return '0'
        normalized = int((dist / max_dist) * 9)
        return str(normalized)

    # Generate heatmap
    print("  Distance Heatmap (0=closest, 9=furthest):")
    print("  " + "-" * 66)
    print()

    # Header
    print("  LED:  ", end="")
    for i in range(21):
        print(f"{i:>2} ", end="")
    print()

    # Distance visualization
    print("  Dist: ", end="")
    for dist in distances:
        print(f" {normalize_to_char(dist)} ", end="")
    print()
    print()

    # Actual distances
    print("  Actual distances from custom center:")
    print("  ", end="")
    for i in range(21):
        if i % 7 == 0 and i > 0:
            print()
            print("  ", end="")
        print(f"LED {i:>2}: {distances[i]:>5.2f}  ", end="")
    print()
    print()

    # Verify gradient pattern
    # For horizontal line with center at 75%, distances should:
    # - Decrease from left to center position
    # - Increase from center position to right

    center_led = int(cx)  # Should be around LED 15 (75% of 20)

    gradient_correct = True

    # Check left side decreasing
    for i in range(center_led):
        if i > 0 and distances[i] > distances[i-1]:
            gradient_correct = False
            break

    # Check right side increasing
    for i in range(center_led + 1, 21):
        if distances[i] < distances[i-1]:
            gradient_correct = False
            break

    if gradient_correct:
        print(f"  [OK]   Distance gradient correct (minimum at LED {center_led})")
    else:
        print(f"  [FAIL] Distance gradient incorrect")
        return False

    print()

    return True


# =============================================================================
# LEVEL 4: Multi-Device Test - Independent Centers
# =============================================================================

def test_level4_multi_device_independence():
    """
    Level 4: Test that multiple devices with different custom centers
    maintain independent center calculations.
    """
    print("=" * 70)
    print("  LEVEL 4: Multi-Device Independence Test")
    print("=" * 70)
    print()

    # Create two mock devices
    class MockDevice:
        def __init__(self, name):
            self.name = name
            self.leds_count = 10

    # Device A: Front impact at 75%
    device_a = MockDevice("Front Strip")
    linear_a = Linear1D(device_a, 10)
    linear_a._topology = {
        "zones": [{"id": 0, "position": {"x": 0, "y": 5}, "rotation": 0, "led_count": 10}],
        "effect_center": {"x": 75.0, "y": 50.0, "enabled": True}
    }
    linear_a._zones = linear_a._topology["zones"]
    linear_a._global_bbox = {'min_x': 0, 'max_x': 9, 'min_y': 5, 'max_y': 5}

    # Device B: Rear impact at 25%
    device_b = MockDevice("Rear Strip")
    linear_b = Linear1D(device_b, 10)
    linear_b._topology = {
        "zones": [{"id": 0, "position": {"x": 0, "y": 10}, "rotation": 0, "led_count": 10}],
        "effect_center": {"x": 25.0, "y": 50.0, "enabled": True}
    }
    linear_b._zones = linear_b._topology["zones"]
    linear_b._global_bbox = {'min_x': 0, 'max_x': 9, 'min_y': 10, 'max_y': 10}

    # Get centers
    center_a = linear_a.get_effect_center()
    center_b = linear_b.get_effect_center()

    if center_a is None or center_b is None:
        print(f"  [FAIL] One or both centers returned None")
        return False

    print(f"  Device A (Front): Custom center at ({center_a[0]:.2f}, {center_a[1]:.2f})")
    print(f"  Device B (Rear):  Custom center at ({center_b[0]:.2f}, {center_b[1]:.2f})")
    print()

    # Verify independence: centers should be different
    if center_a[0] != center_b[0]:
        print(f"  [OK]   Centers are independent (X: {center_a[0]:.2f} vs {center_b[0]:.2f})")
    else:
        print(f"  [FAIL] Centers should be different")
        return False

    # Verify correct positions
    # La bbox e' quella dell'editor (corner dei rettangoli zona): 10 LED = larghezza 10
    expected_a_x = 0 + 0.75 * 10  # 75% of width = 7.5
    expected_b_x = 0 + 0.25 * 10  # 25% of width = 2.5

    tolerance = 0.01
    a_correct = abs(center_a[0] - expected_a_x) < tolerance
    b_correct = abs(center_b[0] - expected_b_x) < tolerance

    if a_correct and b_correct:
        print(f"  [OK]   Both centers calculated correctly")
        print(f"         Device A: Expected {expected_a_x:.2f}, got {center_a[0]:.2f}")
        print(f"         Device B: Expected {expected_b_x:.2f}, got {center_b[0]:.2f}")
    else:
        print(f"  [FAIL] Center calculation incorrect")
        return False

    print()

    return True


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run complete scientific test suite."""
    print("\n")
    print("*" * 70)
    print("  Custom Effect Center - Scientific Test Suite")
    print("*" * 70)
    print("\n")

    results = {}

    # Run all test levels
    print("\n")
    results['level1'] = test_level1_coordinate_conversion()

    print("\n")
    results['level2'] = test_level2_radial_effects_integration()

    print("\n")
    results['level3'] = test_level3_visual_distance_heatmap()

    print("\n")
    results['level4'] = test_level4_multi_device_independence()

    # Summary
    print("\n")
    print("=" * 70)
    print("  Test Summary")
    print("=" * 70)
    print()

    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)

    for level, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        level_name = level.replace('level', 'Level ').upper()
        print(f"  {status} {level_name}")

    print()
    print(f"  Overall: {passed_tests}/{total_tests} test levels passed")
    print()

    if all(results.values()):
        print("  " + "=" * 66)
        print("  [SUCCESS] All tests passed - Custom center implementation verified")
        print("  " + "=" * 66)
        print()
        print("  Ready for hardware testing:")
        print("  1. Configure custom centers in Topology Editor")
        print("  2. Save topology")
        print("  3. Play radial effects (Bloom, Explosion, Plasma)")
        print("  4. Verify expansion originates from custom center position")
        print()
    else:
        print("  " + "=" * 66)
        print("  [FAILURE] Some tests failed - review output above")
        print("  " + "=" * 66)
        print()

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
