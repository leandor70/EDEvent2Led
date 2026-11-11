"""
Debug script for DirectionalFlash topology awareness.
Tests if bbox is loaded correctly and LED classification works.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from effects.linear_1d import Linear1D

class MockDevice:
    """Mock OpenRGB device for testing."""
    def __init__(self, name, led_count):
        self.name = name
        self.leds = [None] * led_count
        self.colors = [(0, 0, 0)] * led_count

def test_directional_flash_topology():
    print("=" * 70)
    print("  DirectionalFlash Topology Debug")
    print("=" * 70)
    print()

    # Create Linear1D for LED strip
    device = MockDevice("LedStripScrivania::linear", 42)
    linear = Linear1D(device, 42)

    # Check if topology was loaded
    print("[1] Topology Loading Check:")
    print(f"    Zones loaded: {len(linear._zones)}")
    print(f"    Global bbox: {linear._global_bbox}")
    print()

    # Test get_global_bbox() method
    bbox = linear.get_global_bbox()
    print("[2] get_global_bbox() Result:")
    print(f"    {bbox}")
    print()

    if bbox and bbox.get('min_x') is not None:
        min_x = bbox['min_x']
        max_x = bbox['max_x']
        min_y = bbox['min_y']
        max_y = bbox['max_y']

        print("[3] BBox Analysis:")
        print(f"    X range: [{min_x}, {max_x}] (width: {max_x - min_x + 1})")
        print(f"    Y range: [{min_y}, {max_y}] (height: {max_y - min_y + 1})")
        print()

        # Test DirectionalFlash thresholds
        print("[4] DirectionalFlash Thresholds:")
        threshold_right = min_x + (max_x - min_x) * 0.75
        threshold_left = min_x + (max_x - min_x) * 0.25
        threshold_top = min_y + (max_y - min_y) * 0.75
        threshold_down = min_y + (max_y - min_y) * 0.25

        print(f"    RIGHT: world_x >= {threshold_right:.2f}")
        print(f"    LEFT:  world_x <  {threshold_left:.2f}")
        print(f"    TOP:   world_y >= {threshold_top:.2f}")
        print(f"    DOWN:  world_y <  {threshold_down:.2f}")
        print()

        # Test LED world positions for direction='right'
        print("[5] LED Classification for direction='right':")
        print(f"    Expected: world_x >= {threshold_right:.2f}")
        print()

        hit_leds = []
        for global_idx in range(linear.led_count):
            zone_idx, local_idx = linear.get_zone_and_local_index(global_idx)
            world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

            is_hit = world_x >= threshold_right
            if is_hit:
                hit_leds.append((global_idx, zone_idx, local_idx, world_x, world_y))

        print(f"    Total LEDs in hit zone: {len(hit_leds)}")
        print()
        print("    LED Details:")
        print("    Global | Zone | Local | World X | World Y")
        print("    " + "-" * 45)
        for global_idx, zone_idx, local_idx, world_x, world_y in hit_leds:
            zone_name = linear._zones[zone_idx].get('name', f'Zone {zone_idx}')
            print(f"    {global_idx:6d} | {zone_idx:4d} | {local_idx:5d} | {world_x:7.0f} | {world_y:7.0f}  ({zone_name})")
        print()

        # Test LED world positions for direction='left'
        print("[6] LED Classification for direction='left':")
        print(f"    Expected: world_x < {threshold_left:.2f}")
        print()

        hit_leds_left = []
        for global_idx in range(linear.led_count):
            zone_idx, local_idx = linear.get_zone_and_local_index(global_idx)
            world_x, world_y = linear.get_led_world_position(zone_idx, local_idx)

            is_hit = world_x < threshold_left
            if is_hit:
                hit_leds_left.append((global_idx, zone_idx, local_idx, world_x, world_y))

        print(f"    Total LEDs in hit zone: {len(hit_leds_left)}")
        print()
        if hit_leds_left:
            print("    LED Details:")
            print("    Global | Zone | Local | World X | World Y")
            print("    " + "-" * 45)
            for global_idx, zone_idx, local_idx, world_x, world_y in hit_leds_left[:10]:  # First 10
                zone_name = linear._zones[zone_idx].get('name', f'Zone {zone_idx}')
                print(f"    {global_idx:6d} | {zone_idx:4d} | {local_idx:5d} | {world_x:7.0f} | {world_y:7.0f}  ({zone_name})")
            if len(hit_leds_left) > 10:
                print(f"    ... and {len(hit_leds_left) - 10} more")
        print()

    else:
        print("[ERROR] BBox is None or invalid - topology NOT loaded!")
        print("        DirectionalFlash will fall back to sequential LEDs")
        print()

    print("=" * 70)

if __name__ == "__main__":
    test_directional_flash_topology()
