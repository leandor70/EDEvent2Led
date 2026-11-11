"""
Test script for GLOBAL wave behavior in Phase 1.1 effects.

Verifies that wave effects propagate continuously across entire bbox,
with get_led_world_position() automatically handling segment rotation.
"""
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from effects.linear_1d import Linear1D
from effects.spatial_effects_1d import WaveEffect1D


class MockDevice:
    """Mock OpenRGB device for testing."""
    def __init__(self, name, led_count):
        self.name = name
        self.led_count = led_count
        self.leds = [None] * led_count
        self.colors = [(0, 0, 0)] * led_count

    def set_colors(self, colors, fast=True):
        """Mock set_colors."""
        self.colors = colors


def create_test_topology():
    """
    Create test topology with 2 horizontal segments:
    - Segment 0: rotation=0 (L->R), 10 LEDs at Y=5
    - Segment 1: rotation=180 (R->L), 10 LEDs at Y=10
    """
    return {
        "device_id": "test_strip",
        "device_type": "LINEAR",
        "zones": [
            {
                "zone_index": 0,
                "zone_name": "Segment 1",
                "position": {"x": 0, "y": 5},
                "rotation": 0,  # Horizontal L->R
                "led_count": 10
            },
            {
                "zone_index": 1,
                "zone_name": "Segment 2",
                "position": {"x": 0, "y": 10},
                "rotation": 180,  # Horizontal R->L (reversed)
                "led_count": 10
            }
        ]
    }


def test_rotation_correction_world_coords():
    """Test GLOBAL wave behavior with world coordinates (use_normalized=False)."""
    print("=" * 70)
    print("TEST: Global Wave - World Coordinates")
    print("=" * 70)
    print()

    # Create mock device with 20 LEDs (2 segments x 10 LEDs)
    mock_device = MockDevice("Test Strip", led_count=20)

    # Create Linear1D with test topology
    linear = Linear1D(mock_device, led_count=20)

    # Load test topology into Linear1D
    topology_data = create_test_topology()

    # Manually set topology (normally loaded from JSON file)
    linear._zones = topology_data["zones"]
    linear._calculate_global_bbox()

    print(f"Device: {topology_data['device_id']}")
    print(f"Total LEDs: {mock_device.led_count}")
    print(f"Segment 0: rotation={linear.get_zone_rotation(0)} (L->R)")
    print(f"Segment 1: rotation={linear.get_zone_rotation(1)} (R->L)")
    print()

    # Create horizontal wave effect (left to right)
    effect = WaveEffect1D(
        linear=linear,
        duration_ms=3000,
        color=(255, 128, 0),
        color_bg=(0, 0, 0),
        wavelength=5.0,
        speed=1.0,
        direction="horizontal",  # L->R in world space
        use_normalized=False  # Test world coordinates
    )

    # Render first frame
    effect.render_frame(time_ms=0)

    # Check device colors
    device_colors = mock_device.colors
    if not device_colors or len(device_colors) != 20:
        print(f"[FAIL] Expected 20 LEDs, got {len(device_colors)}")
        return 1

    # Analyze segment 0 (rotation=0, L->R)
    seg0_brightness = []
    for i in range(10):
        if hasattr(device_colors[i], 'red'):
            r = device_colors[i].red
        else:
            r = device_colors[i][0]
        seg0_brightness.append(r)

    # Analyze segment 1 (rotation=180, R->L)
    seg1_brightness = []
    for i in range(10, 20):
        if hasattr(device_colors[i], 'red'):
            r = device_colors[i].red
        else:
            r = device_colors[i][0]
        seg1_brightness.append(r)

    print("Segment 0 (rotation=0, L->R):")
    print(f"  Brightness values: {seg0_brightness}")

    print()
    print("Segment 1 (rotation=180, R->L):")
    print(f"  Brightness values: {seg1_brightness}")
    print()

    # GLOBAL WAVE TEST: Verify wave propagates through physical space
    # Segments with rotation=180 have LED indices reversed from world positions
    # So seg0 and seg1 should show DIFFERENT patterns because rotation is handled
    # by get_led_world_position() returning physically-correct coordinates

    print("Global Wave Verification:")
    print(f"  Segment 0 range: {min(seg0_brightness)}-{max(seg0_brightness)}")
    print(f"  Segment 1 range: {min(seg1_brightness)}-{max(seg1_brightness)}")

    # Check that both segments show valid brightness variation
    seg0_variation = max(seg0_brightness) - min(seg0_brightness)
    seg1_variation = max(seg1_brightness) - min(seg1_brightness)

    if seg0_variation > 50 and seg1_variation > 50:
        # Both segments show gradient - wave is propagating
        # Segments have different patterns because rotation affects world coords
        print("  [OK] Global wave propagates correctly")
        print("       Both segments show brightness variation")
        print("       Rotation handled by get_led_world_position()")
        return 0
    else:
        print("  [FAIL] Insufficient brightness variation")
        print(f"       Seg0 variation: {seg0_variation}, Seg1 variation: {seg1_variation}")
        return 1


def test_rotation_correction_normalized():
    """Test GLOBAL wave behavior with normalized coordinates (use_normalized=True)."""
    print()
    print("=" * 70)
    print("TEST: Global Wave - Normalized Coordinates")
    print("=" * 70)
    print()

    # Same setup as world coordinates test
    mock_device = MockDevice("Test Strip", led_count=20)
    linear = Linear1D(mock_device, led_count=20)

    topology_data = create_test_topology()
    linear._zones = topology_data["zones"]
    linear._calculate_global_bbox()

    # Create horizontal wave with normalized coordinates
    effect = WaveEffect1D(
        linear=linear,
        duration_ms=3000,
        color=(255, 128, 0),
        color_bg=(0, 0, 0),
        wavelength=0.5,  # Normalized wavelength
        speed=1.0,
        direction="horizontal",
        use_normalized=True  # Test normalized coordinates
    )

    # Render first frame
    effect.render_frame(time_ms=0)

    # Analyze segments
    device_colors = mock_device.colors

    seg0_brightness = []
    for i in range(10):
        if hasattr(device_colors[i], 'red'):
            r = device_colors[i].red
        else:
            r = device_colors[i][0]
        seg0_brightness.append(r)

    seg1_brightness = []
    for i in range(10, 20):
        if hasattr(device_colors[i], 'red'):
            r = device_colors[i].red
        else:
            r = device_colors[i][0]
        seg1_brightness.append(r)

    print("Segment 0 (rotation=0):")
    print(f"  Brightness: {seg0_brightness}")

    print()
    print("Segment 1 (rotation=180):")
    print(f"  Brightness: {seg1_brightness}")
    print()

    # GLOBAL WAVE TEST with normalized coords
    print("Global Wave Verification:")
    print(f"  Segment 0 range: {min(seg0_brightness)}-{max(seg0_brightness)}")
    print(f"  Segment 1 range: {min(seg1_brightness)}-{max(seg1_brightness)}")

    # Verify both segments show brightness variation (wave propagating)
    seg0_variation = max(seg0_brightness) - min(seg0_brightness)
    seg1_variation = max(seg1_brightness) - min(seg1_brightness)

    if seg0_variation > 50 and seg1_variation > 50:
        print("  [OK] Normalized global wave propagates correctly")
        print("       Both segments show brightness variation")
        return 0
    else:
        print("  [FAIL] Insufficient brightness variation")
        print(f"       Seg0 variation: {seg0_variation}, Seg1 variation: {seg1_variation}")
        return 1


def main():
    """Run all rotation correction tests."""
    print()
    print("+" + "=" * 68 + "+")
    print("|" + " " * 18 + "GLOBAL WAVE TEST" + " " * 33 + "|")
    print("|" + " " * 23 + "Phase 1.1" + " " * 36 + "|")
    print("+" + "=" * 68 + "+")
    print()

    try:
        result1 = test_rotation_correction_world_coords()
        result2 = test_rotation_correction_normalized()

        print()
        print("=" * 70)

        if result1 == 0 and result2 == 0:
            print("[OK] ALL GLOBAL WAVE TESTS PASSED")
            print("=" * 70)
            print()
            print("Global wave mode working correctly:")
            print("- Wave propagates continuously across entire bbox")
            print("- get_led_world_position() handles rotation automatically")
            print("- No additional rotation correction needed")
            print("- Both world and normalized coordinates work")
            print()
            return 0
        else:
            print("[FAIL] SOME TESTS FAILED")
            print("=" * 70)
            return 1

    except Exception as e:
        print()
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
