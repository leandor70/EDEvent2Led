"""
Visual validation script for corner custom center (100%, 100%).

Calculates expected LED activation order for Bloom effect starting from
top-right corner custom center.
"""
import sys
import math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import json


def analyze_corner_center():
    """Analyze corner custom center configuration and predict LED activation order."""

    # Load topology
    topology_file = Path(__file__).parent.parent / 'config' / 'device_topologies.json'

    with open(topology_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    topologies = data.get('topologies', {})

    # Find device with custom center enabled
    target_device = None

    for device_id, topology in topologies.items():
        effect_center = topology.get('effect_center', {})
        if effect_center.get('enabled', False):
            target_device = device_id
            target_topology = topology
            break

    if not target_device:
        print("No device with custom center enabled found.")
        return

    print("=" * 70)
    print("  Visual Validation: Corner Custom Center")
    print("=" * 70)
    print()
    print(f"Device: {target_device}")
    print()

    # Get center config
    effect_center = target_topology.get('effect_center', {})
    center_x_pct = effect_center.get('x', 50.0)
    center_y_pct = effect_center.get('y', 50.0)

    print(f"Custom Center: ({center_x_pct}%, {center_y_pct}%)")

    if center_x_pct == 100.0 and center_y_pct == 100.0:
        print("               ^^^^^^^^^^^^^^^^^^^^^^^^^")
        print("               EXTREME TOP-RIGHT CORNER!")

    print()

    # Get zones
    zones = target_topology.get('zones', [])

    if not zones:
        print("No zones found in topology.")
        return

    # Calculate global bbox
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')

    for zone in zones:
        pos = zone.get('position', {})
        pos_x = pos.get('x', 0)
        pos_y = pos.get('y', 0)
        rotation = zone.get('rotation', 0)
        led_count = zone.get('led_count', 0)

        # Calculate zone bounds based on rotation
        if rotation == 0:  # Horizontal
            min_x = min(min_x, pos_x)
            max_x = max(max_x, pos_x + led_count - 1)
            min_y = min(min_y, pos_y)
            max_y = max(max_y, pos_y)
        elif rotation == 90:  # Vertical up
            min_x = min(min_x, pos_x)
            max_x = max(max_x, pos_x)
            min_y = min(min_y, pos_y)
            max_y = max(max_y, pos_y + led_count - 1)
        elif rotation == 180:  # Horizontal reversed
            min_x = min(min_x, pos_x - led_count + 1)
            max_x = max(max_x, pos_x)
            min_y = min(min_y, pos_y)
            max_y = max(max_y, pos_y)
        elif rotation == 270:  # Vertical down
            min_x = min(min_x, pos_x)
            max_x = max(max_x, pos_x)
            min_y = min(min_y, pos_y - led_count + 1)
            max_y = max(max_y, pos_y)

    print(f"Global BBox: X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]")
    print()

    # Calculate custom center world coordinates
    width = max_x - min_x
    height = max_y - min_y

    cx = min_x + (center_x_pct / 100.0) * width
    cy = min_y + (center_y_pct / 100.0) * height

    print(f"Custom Center World Coords: ({cx:.2f}, {cy:.2f})")
    print()

    # Calculate LED distances from custom center
    print("LED Activation Order (Bloom effect):")
    print("-" * 70)

    led_distances = []

    for zone in zones:
        pos = zone.get('position', {})
        pos_x = pos.get('x', 0)
        pos_y = pos.get('y', 0)
        rotation = zone.get('rotation', 0)
        led_count = zone.get('led_count', 0)
        zone_id = zone.get('id', 0)
        zone_name = zone.get('name', f'Zone {zone_id}')

        for local_idx in range(led_count):
            # Calculate LED world position
            if rotation == 0:
                world_x = pos_x + local_idx
                world_y = pos_y
            elif rotation == 90:
                world_x = pos_x
                world_y = pos_y + local_idx
            elif rotation == 180:
                world_x = pos_x - local_idx
                world_y = pos_y
            elif rotation == 270:
                world_x = pos_x
                world_y = pos_y - local_idx
            else:
                world_x = pos_x
                world_y = pos_y

            # Calculate distance from custom center
            distance = math.sqrt((world_x - cx)**2 + (world_y - cy)**2)

            led_distances.append({
                'zone_name': zone_name,
                'local_idx': local_idx,
                'world_x': world_x,
                'world_y': world_y,
                'distance': distance
            })

    # Sort by distance (closest first)
    led_distances.sort(key=lambda x: x['distance'])

    # Print activation order
    print(f"{'Rank':<6} {'Zone':<20} {'LED':<5} {'Position':<15} {'Distance'}")
    print("-" * 70)

    for rank, led in enumerate(led_distances[:15], start=1):  # Show first 15
        print(f"{rank:<6} {led['zone_name']:<20} "
              f"{led['local_idx']:<5} "
              f"({led['world_x']:.1f}, {led['world_y']:.1f}){' ':<5} "
              f"{led['distance']:>6.2f}")

    if len(led_distances) > 15:
        print(f"... ({len(led_distances) - 15} more LEDs)")

    print("-" * 70)
    print()

    # Analysis
    print("Analysis:")
    print("-" * 70)

    closest_led = led_distances[0]
    print(f"  FIRST LED to activate: {closest_led['zone_name']} LED {closest_led['local_idx']}")
    print(f"  Position: ({closest_led['world_x']:.1f}, {closest_led['world_y']:.1f})")
    print(f"  Distance from custom center: {closest_led['distance']:.2f}")
    print()

    if closest_led['distance'] < 1.0:
        print("  [OK] Custom center is very close to LED physical position")
        print("       Effect will start from this LED as expected!")
    else:
        print(f"  [INFO] Custom center is {closest_led['distance']:.2f} units from nearest LED")
        print("        Effect will still expand from corner, but may look slightly offset")

    print()

    # Directional analysis
    if center_x_pct >= 75 and center_y_pct >= 75:
        print("  [CORNER] Top-Right Corner Configuration")
        print("           Expansion: from right→left, from top→bottom")
    elif center_x_pct <= 25 and center_y_pct >= 75:
        print("  [CORNER] Top-Left Corner Configuration")
        print("           Expansion: from left→right, from top→bottom")
    elif center_x_pct >= 75 and center_y_pct <= 25:
        print("  [CORNER] Bottom-Right Corner Configuration")
        print("           Expansion: from right→left, from bottom→top")
    elif center_x_pct <= 25 and center_y_pct <= 25:
        print("  [CORNER] Bottom-Left Corner Configuration")
        print("           Expansion: from left→right, from bottom→top")

    print()


if __name__ == "__main__":
    analyze_corner_center()
