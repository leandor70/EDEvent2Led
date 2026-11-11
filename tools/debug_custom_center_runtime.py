"""
Runtime debug script for custom center implementation.

Tests if BloomEffect1D actually uses custom center at runtime.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from effects.linear_1d import Linear1D
from effects.spatial_effects_1d import BloomEffect1D
import json


def test_bloom_uses_custom_center():
    """Test that BloomEffect1D reads and uses custom center from topology."""

    print("=" * 70)
    print("  Runtime Debug: BloomEffect1D Custom Center Usage")
    print("=" * 70)
    print()

    # Load topology config
    topology_file = Path(__file__).parent.parent / 'config' / 'device_topologies.json'

    with open(topology_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    topologies = data.get('topologies', {})

    # Find device with custom center enabled
    target_device_id = None
    target_topology = None

    for device_id, topology in topologies.items():
        effect_center = topology.get('effect_center', {})
        if effect_center.get('enabled', False):
            target_device_id = device_id
            target_topology = topology
            break

    if not target_device_id:
        print("[FAIL] No device with custom center enabled found")
        return False

    print(f"Target Device: {target_device_id}")
    effect_center = target_topology.get('effect_center', {})
    print(f"Custom Center Config: X={effect_center.get('x')}%, Y={effect_center.get('y')}%")
    print()

    # Create mock device
    class MockDevice:
        def __init__(self):
            self.name = target_device_id
            self.leds_count = 38

    device = MockDevice()
    linear = Linear1D(device, 38)

    # Load topology into Linear1D
    linear._topology = target_topology
    linear._zones = target_topology.get('zones', [])
    linear._calculate_global_bbox()

    print("Linear1D Controller State:")
    print(f"  Topology loaded: {linear._topology is not None}")
    print(f"  Zones: {len(linear._zones)}")
    print(f"  Global BBox: {linear._global_bbox}")
    print()

    # Test get_effect_center()
    custom_center = linear.get_effect_center()

    print("get_effect_center() Result:")
    if custom_center:
        print(f"  [OK] Returned: ({custom_center[0]:.2f}, {custom_center[1]:.2f})")
    else:
        print(f"  [FAIL] Returned None (should return custom center)")
        return False

    print()

    # Create BloomEffect1D
    print("Creating BloomEffect1D...")

    colors = [
        (255, 255, 255),  # White
        (255, 255, 0),    # Yellow
        (255, 128, 0),    # Orange
        (255, 0, 0),      # Red
        (0, 0, 0),        # Black
    ]

    bloom = BloomEffect1D(
        linear=linear,
        duration_ms=2000,
        colors=colors,
        expansion_factor=2.0,
        use_normalized=False  # Use world coordinates to test custom center
    )

    print(f"BloomEffect1D Created")
    print(f"  Center used: ({bloom.center_x:.2f}, {bloom.center_y:.2f})")
    print()

    # Compare with expected
    bbox = linear._global_bbox
    geometric_cx = (bbox['min_x'] + bbox['max_x']) / 2.0
    geometric_cy = (bbox['min_y'] + bbox['max_y']) / 2.0

    print("Comparison:")
    print(f"  Geometric center: ({geometric_cx:.2f}, {geometric_cy:.2f})")
    print(f"  Custom center:    ({custom_center[0]:.2f}, {custom_center[1]:.2f})")
    print(f"  Bloom using:      ({bloom.center_x:.2f}, {bloom.center_y:.2f})")
    print()

    # Verify Bloom uses custom center
    tolerance = 0.01
    uses_custom = (
        abs(bloom.center_x - custom_center[0]) < tolerance and
        abs(bloom.center_y - custom_center[1]) < tolerance
    )

    uses_geometric = (
        abs(bloom.center_x - geometric_cx) < tolerance and
        abs(bloom.center_y - geometric_cy) < tolerance
    )

    print("Verification:")
    if uses_custom:
        print("  [OK] BloomEffect1D is using CUSTOM CENTER")
        print("       Implementation working correctly!")
        return True
    elif uses_geometric:
        print("  [FAIL] BloomEffect1D is using GEOMETRIC CENTER")
        print("         Custom center NOT being applied")
        print("         Check implementation in spatial_effects_1d.py")
        return False
    else:
        print("  [WARN] BloomEffect1D using unexpected center")
        print(f"        Expected custom: {custom_center}")
        print(f"        Expected geometric: ({geometric_cx:.2f}, {geometric_cy:.2f})")
        print(f"        Actual: ({bloom.center_x:.2f}, {bloom.center_y:.2f})")
        return False


if __name__ == "__main__":
    success = test_bloom_uses_custom_center()
    print()
    print("=" * 70)
    if success:
        print("  [SUCCESS] Custom center implementation verified")
    else:
        print("  [FAILURE] Custom center NOT working - needs debugging")
    print("=" * 70)
    print()
    sys.exit(0 if success else 1)
